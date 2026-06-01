import frappe

from ripl.utils.identifier import normalize_identifier
from ripl.utils.staging_auth import is_staging_auth_context

DEFAULT_DEV_TEST_EMAIL = "test@ripl.dev"
DEFAULT_DEV_TEST_OTP = "123456"


def is_dev_auth_enabled() -> bool:
	return is_staging_auth_context()


def get_dev_test_email() -> str:
	return (frappe.conf.get("ripl_dev_test_email") or DEFAULT_DEV_TEST_EMAIL).strip().lower()


def get_dev_test_otp() -> str:
	return str(frappe.conf.get("ripl_dev_test_otp") or DEFAULT_DEV_TEST_OTP)


def is_dev_test_identifier(identifier: str | None) -> bool:
	if not identifier or not is_dev_auth_enabled():
		return False
	return normalize_identifier(identifier) == get_dev_test_email()


def is_dev_test_login(identifier: str | None, otp: str | None) -> bool:
	if not is_dev_test_identifier(identifier):
		return False
	return str(otp).strip() == get_dev_test_otp()


def dev_auth_metadata() -> dict | None:
	if not is_dev_auth_enabled():
		return None
	return {
		"dev_mode": True,
		"dev_test_email": get_dev_test_email(),
		"dev_test_otp": get_dev_test_otp(),
	}
