import time

import frappe
from frappe import _

OTP_EXPIRY_SECONDS = 300
COOLDOWN_SECONDS = 30
MAX_SENDS_PER_HOUR = 3
HOURLY_WINDOW_SECONDS = 3600


def coerce_bool(value) -> bool:
	if isinstance(value, bool):
		return value
	if isinstance(value, (int, float)):
		return bool(value)
	if isinstance(value, str):
		return value.strip().lower() in ("1", "true", "yes", "on")
	return False


def _meta_key(identifier: str) -> str:
	return f"otp_send_meta_{identifier}"


def _get_meta(identifier: str) -> dict:
	meta = frappe.cache().get_value(_meta_key(identifier)) or {}
	now = time.time()
	window_end = meta.get("window_end") or 0
	if window_end and now >= float(window_end):
		return {}
	return meta


def _set_meta(identifier: str, meta: dict) -> None:
	frappe.cache().set_value(_meta_key(identifier), meta)


def check_send_allowed(identifier: str) -> dict:
	"""Validate cooldown and hourly cap. Returns static limits for success responses."""
	meta = _get_meta(identifier)
	now = time.time()

	last_sent = meta.get("last_sent")
	if last_sent is not None:
		elapsed = now - float(last_sent)
		if elapsed < COOLDOWN_SECONDS:
			retry_after = max(1, int(COOLDOWN_SECONDS - elapsed))
			frappe.throw(
				_("Please wait {0} seconds before requesting another OTP.").format(retry_after),
				frappe.ValidationError,
			)

	hourly_count = int(meta.get("hourly_count") or 0)
	if hourly_count >= MAX_SENDS_PER_HOUR:
		window_end = meta.get("window_end")
		retry_after = max(1, int(float(window_end) - now)) if window_end else HOURLY_WINDOW_SECONDS
		frappe.throw(
			_("Maximum OTP requests reached. Try again in {0} seconds.").format(retry_after),
			frappe.ValidationError,
		)

	return {
		"cooldown_seconds": COOLDOWN_SECONDS,
		"expires_in_seconds": OTP_EXPIRY_SECONDS,
		"max_hourly_attempts": MAX_SENDS_PER_HOUR,
		"hourly_attempts_used": hourly_count,
		"hourly_attempts_remaining": max(0, MAX_SENDS_PER_HOUR - hourly_count),
	}


def record_send(identifier: str, client_is_resend: bool = False, had_existing_otp: bool = False) -> dict:
	"""Increment counters after a successful OTP send."""
	now = time.time()
	meta = _get_meta(identifier)
	hourly_count = int(meta.get("hourly_count") or 0)

	if hourly_count == 0:
		meta["window_end"] = now + HOURLY_WINDOW_SECONDS

	meta["hourly_count"] = hourly_count + 1
	meta["last_sent"] = now
	_set_meta(identifier, meta)

	new_hourly_count = meta["hourly_count"]
	resend_count = max(0, new_hourly_count - 1)
	is_resend = client_is_resend or had_existing_otp or resend_count > 0

	return {
		"is_resend": is_resend,
		"resend_count": resend_count,
		"hourly_attempts_used": new_hourly_count,
		"hourly_attempts_remaining": max(0, MAX_SENDS_PER_HOUR - new_hourly_count),
		"retry_after_seconds": COOLDOWN_SECONDS,
		"cooldown_seconds": COOLDOWN_SECONDS,
		"expires_in_seconds": OTP_EXPIRY_SECONDS,
		"max_hourly_attempts": MAX_SENDS_PER_HOUR,
	}


def clear_rate_limit(identifier: str) -> None:
	frappe.cache().delete_value(_meta_key(identifier))
