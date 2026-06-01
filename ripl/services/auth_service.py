import random

import frappe

from ripl.utils.dev_auth import (
	dev_auth_metadata,
	get_dev_test_otp,
	is_dev_test_identifier,
	is_dev_test_login,
)
from ripl.utils.identifier import normalize_identifier, otp_cache_key
from ripl.utils.log import log_error_event, log_event, mask_identifier
from ripl.utils.otp_rate_limit import (
	OTP_EXPIRY_SECONDS,
	check_send_allowed,
	coerce_bool,
	record_send,
)
from ripl.utils.staging_auth import log_otp_to_error_log, staging_otp_response_fields
from ripl.utils.token import create_tokens


def send_otp(identifier: str, is_resend: bool | str | int | None = False) -> dict:
	identifier = normalize_identifier(identifier)
	client_is_resend = coerce_bool(is_resend)
	log_event(
		"send_otp.start",
		identifier=mask_identifier(identifier),
		is_resend=client_is_resend,
	)

	try:
		if not identifier:
			log_event("send_otp.validation_failed", level="warning", reason="missing_identifier")
			frappe.throw("Email or phone required")

		rate_meta = check_send_allowed(identifier)
		cache_key = otp_cache_key(identifier)
		had_existing_otp = bool(frappe.cache().get_value(cache_key, expires=True))

		if is_dev_test_identifier(identifier):
			otp = get_dev_test_otp()
			log_event(
				"send_otp.dev_bypass",
				identifier=mask_identifier(identifier),
				otp=otp,
			)
		else:
			otp = str(random.randint(100000, 999999))
			if frappe.conf.get("developer_mode"):
				log_event("send_otp.dev_otp", identifier=mask_identifier(identifier), otp=otp)
			else:
				log_event("send_otp.otp_cached", identifier=mask_identifier(identifier))

		frappe.cache().set_value(cache_key, otp, expires_in_sec=OTP_EXPIRY_SECONDS)
		log_otp_to_error_log(otp, identifier, OTP_EXPIRY_SECONDS)

		send_meta = record_send(
			identifier,
			client_is_resend=client_is_resend,
			had_existing_otp=had_existing_otp,
		)
		response = {
			"success": True,
			"message": "OTP sent",
			**rate_meta,
			**send_meta,
			**staging_otp_response_fields(otp, OTP_EXPIRY_SECONDS),
		}
		dev_meta = dev_auth_metadata()
		if dev_meta and is_dev_test_identifier(identifier):
			response.update(dev_meta)

		event = "send_otp.resend" if send_meta["is_resend"] else "send_otp.success"
		log_event(
			event,
			identifier=mask_identifier(identifier),
			is_resend=send_meta["is_resend"],
			resend_count=send_meta["resend_count"],
			hourly_attempts_used=send_meta["hourly_attempts_used"],
		)
		return response
	except Exception as exc:
		log_error_event("send_otp.failed", exc=exc, identifier=mask_identifier(identifier))
		raise


def verify_otp(identifier: str, otp: str) -> dict:
	identifier = normalize_identifier(identifier)
	otp = str(otp).strip() if otp is not None else ""
	log_event(
		"verify_otp.start",
		identifier=mask_identifier(identifier),
		otp_length=len(otp),
	)

	try:
		if not identifier or not otp:
			log_event("verify_otp.validation_failed", level="warning", reason="missing_fields")
			frappe.throw("Missing fields")

		if is_dev_test_login(identifier, otp):
			log_event("verify_otp.dev_bypass", identifier=mask_identifier(identifier))
		else:
			cache_key = otp_cache_key(identifier)
			stored_otp = frappe.cache().get_value(cache_key, expires=True)

			if not stored_otp:
				log_event(
					"verify_otp.failed",
					level="warning",
					reason="otp_expired",
					identifier=mask_identifier(identifier),
				)
				frappe.throw("OTP expired")

			if str(stored_otp) != otp:
				log_event(
					"verify_otp.failed",
					level="warning",
					reason="invalid_otp",
					identifier=mask_identifier(identifier),
					stored_otp_present=True,
				)
				frappe.throw("Invalid OTP")

			frappe.cache().delete_value(cache_key)

		log_event("verify_otp.otp_validated", identifier=mask_identifier(identifier))

		user_name = _get_or_create_user(identifier)
		log_event("verify_otp.user_ready", user=user_name)

		access_token, refresh_token = create_tokens(user_name)
		log_event("verify_otp.tokens_created", user=user_name)

		response = {
			"success": True,
			"access_token": access_token,
			"refresh_token": refresh_token,
			"user": user_name,
		}
		if is_dev_test_login(identifier, otp):
			dev_meta = dev_auth_metadata()
			if dev_meta:
				response["dev_mode"] = dev_meta["dev_mode"]

		log_event("verify_otp.success", user=user_name)
		return response
	except Exception as exc:
		log_error_event("verify_otp.failed", exc=exc, identifier=mask_identifier(identifier))
		raise


def _get_or_create_user(identifier: str) -> str:
	if frappe.db.exists("User", identifier):
		log_event("verify_otp.user_exists", user=identifier)
		return identifier

	log_event("verify_otp.creating_user", identifier=mask_identifier(identifier))
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": identifier,
			"first_name": identifier.split("@")[0] if "@" in identifier else identifier,
			"enabled": 1,
			"user_type": "Website User",
		}
	)
	user.insert(ignore_permissions=True)
	log_event("verify_otp.user_created", user=user.name)
	return user.name
