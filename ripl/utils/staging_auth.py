import frappe

from ripl.utils.log import mask_identifier
from ripl.utils.otp_rate_limit import coerce_bool


def is_production_site() -> bool:
	return coerce_bool(frappe.conf.get("ripl_production"))


def is_staging_auth_context() -> bool:
	"""Allow staging QA auth helpers. Never enabled when ripl_production is set."""
	if is_production_site():
		return False
	return bool(frappe.conf.get("developer_mode")) or coerce_bool(frappe.conf.get("ripl_staging_auth"))


def should_expose_otp_in_response() -> bool:
	if not is_staging_auth_context():
		return False
	return coerce_bool(frappe.conf.get("ripl_expose_otp_in_response"))


def should_log_otp_to_error_log() -> bool:
	if is_production_site():
		return False
	if frappe.conf.get("developer_mode"):
		return True
	if not is_staging_auth_context():
		return False
	return coerce_bool(frappe.conf.get("ripl_log_otp_to_error_log"))


def staging_otp_response_fields(otp: str, ttl: int) -> dict:
	if not should_expose_otp_in_response():
		return {}
	return {
		"dev_mode": True,
		"dev_test_otp": otp,
		"expires_in_seconds": ttl,
	}


def log_otp_to_error_log(otp: str, identifier: str, ttl: int) -> None:
	if not should_log_otp_to_error_log():
		return

	masked = mask_identifier(identifier)
	frappe.log_error(
		title=f"RIPL OTP for {masked}",
		message=(
			f"OTP: {otp}\n"
			f"Expires in: {ttl}s\n"
			f"Identifier: {identifier}\n"
			f"Search: send_otp RIPL OTP"
		),
	)
