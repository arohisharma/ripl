import frappe

from ripl.services import auth_service
from ripl.utils.log import log_error_event, log_event, mask_identifier


@frappe.whitelist(allow_guest=True)
def send_otp(identifier, is_resend=False):
	log_event(
		"api.send_otp",
		endpoint="ripl.api.login.send_otp",
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
		endpoint="ripl.api.login.verify_otp",
		identifier=mask_identifier(identifier),
		otp_length=len(str(otp)) if otp else 0,
	)
	try:
		return auth_service.verify_otp(identifier, otp)
	except Exception as exc:
		log_error_event("api.verify_otp.error", exc=exc, identifier=mask_identifier(identifier))
		raise
