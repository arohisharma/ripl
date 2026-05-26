import datetime

import frappe
import jwt

from ripl.utils.log import log_error_event, log_event

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY_DAYS = 1
REFRESH_TOKEN_EXPIRY_DAYS = 7


def get_secret_key():
	secret = frappe.conf.get("jwt_secret")
	if not secret:
		log_event("token.missing_jwt_secret", level="error")
		frappe.throw(
			"JWT secret not configured. Set jwt_secret in site_config.json.",
			frappe.AuthenticationError,
		)
	return secret


def create_tokens(user: str) -> tuple[str, str]:
	now = datetime.datetime.utcnow()
	access_payload = {
		"user": user,
		"type": "access",
		"iat": now,
		"exp": now + datetime.timedelta(days=ACCESS_TOKEN_EXPIRY_DAYS),
	}
	refresh_payload = {
		"user": user,
		"type": "refresh",
		"iat": now,
		"exp": now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS),
	}
	secret = get_secret_key()
	access_token = jwt.encode(access_payload, secret, algorithm=ALGORITHM)
	refresh_token = jwt.encode(refresh_payload, secret, algorithm=ALGORITHM)
	return access_token, refresh_token


def extract_bearer_token() -> str | None:
	auth_header = frappe.get_request_header("Authorization")
	if not auth_header:
		return None
	parts = auth_header.split(" ", 1)
	if len(parts) != 2 or parts[0].lower() != "bearer":
		return None
	token = parts[1].strip()
	return token or None


def decode_token(token: str, expected_type: str | None = None) -> dict:
	try:
		payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
	except jwt.ExpiredSignatureError:
		log_event("token.expired", level="warning", expected_type=expected_type)
		frappe.throw("Token expired", frappe.AuthenticationError)
	except jwt.InvalidTokenError as exc:
		log_error_event("token.invalid", exc=exc, expected_type=expected_type)
		frappe.throw("Invalid token", frappe.AuthenticationError)

	token_type = payload.get("type")
	if expected_type and token_type != expected_type:
		log_event(
			"token.wrong_type",
			level="warning",
			expected_type=expected_type,
			actual_type=token_type,
		)
		frappe.throw("Invalid token type", frappe.AuthenticationError)

	return payload


def get_user_from_access_token(token: str) -> str:
	payload = decode_token(token, expected_type="access")
	user = payload.get("user")
	if not user:
		log_event("token.missing_user_claim", level="warning")
		frappe.throw("Invalid token", frappe.AuthenticationError)

	if not frappe.db.exists("User", {"name": user, "enabled": 1}):
		log_event("token.user_not_found", level="warning", user=user)
		frappe.throw("User not found or disabled", frappe.AuthenticationError)

	return user
