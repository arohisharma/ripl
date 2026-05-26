import inspect
from functools import wraps

import frappe
from frappe import _

from ripl.services import auth_service
from ripl.utils.log import log_error_event, log_event, mask_identifier
from ripl.utils.token import create_tokens, extract_bearer_token, get_user_from_access_token

# Backward-compatible import for modules that import create_tokens from here.
__all__ = ["auth_required", "subscription_required", "create_tokens", "send_otp", "verify_otp"]


def _set_authenticated_user(user: str) -> None:
	frappe.local.user = user
	frappe.set_user(user)


def authenticate_request() -> str:
	token = extract_bearer_token()
	if not token:
		log_event("auth.missing_token", level="warning")
		frappe.throw(_("Authentication required"), frappe.AuthenticationError)

	try:
		user = get_user_from_access_token(token)
		log_event("auth.token_valid", user=user)
		return user
	except Exception as exc:
		log_error_event("auth.token_invalid", exc=exc)
		raise


def _resolve_wrapped_function(func):
	"""Return the innermost function (skip auth/subscription/whitelist wrappers)."""
	target = func
	while hasattr(target, "__wrapped__"):
		target = target.__wrapped__
	return target


def _get_combined_request_params(incoming_kwargs: dict | None = None) -> frappe._dict:
	"""Merge form_dict, query string, JSON body, and kwargs from Frappe's caller."""
	params = frappe._dict(frappe.form_dict)
	if incoming_kwargs:
		params.update(incoming_kwargs)

	request = getattr(frappe.local, "request", None)
	if request:
		params.update(request.args or {})
		params.update(request.form or {})

		if request.is_json:
			json_body = request.get_json(silent=True)
			if isinstance(json_body, dict):
				params.update(json_body)

	if params.get("data"):
		try:
			parsed = frappe.parse_json(params.get("data"))
			if isinstance(parsed, dict):
				params.update(parsed)
		except Exception:
			pass

	return params


def _build_fn_kwargs(func, extra_kwargs: dict | None = None, incoming_kwargs: dict | None = None) -> dict:
	"""Map request params to the wrapped function (fixes decorator chain + GET/POST args)."""
	target = _resolve_wrapped_function(func)
	combined = _get_combined_request_params(incoming_kwargs)
	fn_kwargs = frappe.get_newargs(target, combined)

	# Fallback: ensure declared parameters are filled (e.g. name, playbook_id)
	for param_name in inspect.signature(target).parameters:
		if param_name not in fn_kwargs and combined.get(param_name) is not None:
			fn_kwargs[param_name] = combined.get(param_name)

	if extra_kwargs:
		for key, value in extra_kwargs.items():
			if key in inspect.signature(target).parameters:
				fn_kwargs[key] = value

	return fn_kwargs


def _call_wrapped(func, args, incoming_kwargs: dict, extra_kwargs: dict | None = None):
	fn_kwargs = _build_fn_kwargs(func, extra_kwargs, incoming_kwargs)
	target = _resolve_wrapped_function(func)

	sig = inspect.signature(target)
	param_names = [
		name
		for name, param in sig.parameters.items()
		if param.kind
		in (
			inspect.Parameter.POSITIONAL_ONLY,
			inspect.Parameter.POSITIONAL_OR_KEYWORD,
		)
	]
	for index, value in enumerate(args):
		if index < len(param_names) and param_names[index] not in fn_kwargs:
			fn_kwargs[param_names[index]] = value

	# Pass resolved kwargs into the next decorator or handler in the chain
	return func(**fn_kwargs)


def auth_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		log_event("auth_required.start", method=func.__name__)
		try:
			user = authenticate_request()
			_set_authenticated_user(user)

			extra = {"user": user} if "user" in inspect.signature(func).parameters else None
			result = _call_wrapped(func, args, kwargs, extra)
			log_event("auth_required.success", method=func.__name__, user=user)
			return result
		except Exception as exc:
			log_error_event("auth_required.failed", exc=exc, method=func.__name__)
			raise

	return wrapper


def subscription_required(func):
	"""Placeholder until subscription/plan enforcement is implemented."""

	@wraps(func)
	def wrapper(*args, **kwargs):
		user = kwargs.get("user") or getattr(frappe.local, "user", None)
		if not user or user == "Guest":
			log_event("subscription_required.failed", level="warning", method=func.__name__)
			frappe.throw(_("Authentication required"), frappe.AuthenticationError)

		extra = {"user": user} if "user" in inspect.signature(func).parameters else None
		return _call_wrapped(func, args, kwargs, extra)

	return wrapper


@frappe.whitelist(allow_guest=True)
def send_otp(identifier, is_resend=False):
	log_event(
		"api.send_otp",
		endpoint="ripl.api.auth.send_otp",
		identifier=mask_identifier(identifier),
		is_resend=is_resend,
	)
	try:
		return auth_service.send_otp(identifier, is_resend=is_resend)
	except Exception as exc:
		log_error_event("api.send_otp.error", exc=exc, identifier=mask_identifier(identifier))
		raise


@frappe.whitelist(allow_guest=True)
def verify_otp(identifier, otp):
	log_event(
		"api.verify_otp",
		endpoint="ripl.api.auth.verify_otp",
		identifier=mask_identifier(identifier),
		otp_length=len(str(otp)) if otp else 0,
	)
	try:
		return auth_service.verify_otp(identifier, otp)
	except Exception as exc:
		log_error_event("api.verify_otp.error", exc=exc, identifier=mask_identifier(identifier))
		raise
