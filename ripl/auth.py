import frappe

from ripl.utils.log import log_error_event, log_event
from ripl.utils.token import extract_bearer_token, get_user_from_access_token


def validate_jwt_auth():
	"""Frappe auth_hook: authenticate Bearer JWT before validate_auth() rejects Guest."""
	token = extract_bearer_token()
	if not token:
		return

	try:
		user = get_user_from_access_token(token)
		frappe.set_user(user)
		log_event("auth_hook.jwt_success", user=user)
	except Exception as exc:
		log_error_event("auth_hook.jwt_failed", exc=exc)
