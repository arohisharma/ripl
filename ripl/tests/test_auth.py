import time
from unittest.mock import patch

import frappe
import jwt
from frappe.tests.utils import FrappeTestCase

from ripl.api.auth import authenticate_request
from ripl.api.test import get_profile
from ripl.services import auth_service
from ripl.utils.otp_rate_limit import COOLDOWN_SECONDS, clear_rate_limit
from ripl.utils.token import create_tokens, decode_token, get_secret_key


class TestAuth(FrappeTestCase):
	def setUp(self):
		self.test_user = "auth-test@example.com"
		if not frappe.db.exists("User", self.test_user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": self.test_user,
					"first_name": "Auth",
					"enabled": 1,
					"user_type": "Website User",
				}
			).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clear_otp_keys(self.test_user)
		if frappe.db.exists("User", self.test_user):
			frappe.delete_doc("User", self.test_user, force=1)

	def _clear_otp_keys(self, identifier: str):
		frappe.cache().delete_value(f"otp_{identifier}")
		clear_rate_limit(identifier)

	def _auth_header(self, token: str) -> dict:
		return {"Authorization": f"Bearer {token}"}

	def test_create_and_decode_access_token(self):
		access_token, refresh_token = create_tokens(self.test_user)
		payload = decode_token(access_token, expected_type="access")
		self.assertEqual(payload["user"], self.test_user)
		refresh_payload = decode_token(refresh_token, expected_type="refresh")
		self.assertEqual(refresh_payload["user"], self.test_user)

	def test_verify_otp_issues_tokens(self):
		identifier = self.test_user
		otp = "123456"
		frappe.cache().set_value(f"otp_{identifier}", otp, expires_in_sec=300)

		result = auth_service.verify_otp(identifier, otp)
		self.assertTrue(result["success"])
		self.assertEqual(result["user"], identifier)
		self.assertTrue(result["access_token"])
		self.assertTrue(result["refresh_token"])

	def test_verify_otp_rejects_invalid_otp(self):
		frappe.cache().set_value(f"otp_{self.test_user}", "111111", expires_in_sec=300)
		with self.assertRaises(frappe.ValidationError):
			auth_service.verify_otp(self.test_user, "999999")

	def test_authenticate_request_missing_token(self):
		with patch("frappe.get_request_header", return_value=None):
			with self.assertRaises(frappe.AuthenticationError):
				authenticate_request()

	def test_authenticate_request_invalid_token(self):
		with patch("frappe.get_request_header", return_value="Bearer invalid-token"):
			with self.assertRaises(frappe.AuthenticationError):
				authenticate_request()

	def test_authenticate_request_expired_token(self):
		secret = get_secret_key()
		expired = jwt.encode(
			{"user": self.test_user, "type": "access", "exp": 0},
			secret,
			algorithm="HS256",
		)
		with patch("frappe.get_request_header", return_value=f"Bearer {expired}"):
			with self.assertRaises(frappe.AuthenticationError):
				authenticate_request()

	def test_auth_required_forwards_query_params(self):
		from ripl.api.post import get_post_detail

		access_token, _ = create_tokens(self.test_user)
		post_name = "test-post-param-forward"

		def mock_header(key, default=None):
			if key == "Authorization":
				return f"Bearer {access_token}"
			return default

		frappe.form_dict = frappe._dict({"name": post_name})

		with patch("frappe.get_request_header", side_effect=mock_header):
			with patch("frappe.get_doc") as mock_get_doc:
				mock_get_doc.return_value = frappe._dict(name=post_name, title="Test")
				result = get_post_detail()
		mock_get_doc.assert_called_once_with("Post", post_name)
		self.assertEqual(result["name"], post_name)

	def test_playbook_purchase_post_body(self):
		from ripl.api.playbook import playbook_purchase

		access_token, _ = create_tokens(self.test_user)
		playbook_id = "test-playbook-purchase"

		def mock_header(key, default=None):
			if key == "Authorization":
				return f"Bearer {access_token}"
			return default

		frappe.form_dict = frappe._dict({"cmd": "ripl.api.playbook.playbook_purchase"})
		with patch("frappe.get_request_header", side_effect=mock_header):
			with patch("frappe.db.exists", return_value=True):
				with patch("frappe.get_doc") as mock_get_doc:
					mock_doc = mock_get_doc.return_value
					mock_doc.status = "Active"
					mock_doc.save = lambda *a, **k: None
					with patch("frappe.get_doc", side_effect=lambda *a, **k: mock_doc if a else mock_doc):
						result = playbook_purchase(playbook_id=playbook_id)
		self.assertEqual(result["playbook_id"], playbook_id)
		self.assertTrue(result["is_purchased"])

	def test_auth_required_forwards_kwargs_from_frappe_call(self):
		"""Simulates GET ?name= when Frappe passes name via kwargs, not form_dict."""
		from ripl.api.auth import auth_required

		@auth_required
		def sample_detail(name, user=None):
			return {"name": name, "user": user}

		access_token, _ = create_tokens(self.test_user)

		def mock_header(key, default=None):
			if key == "Authorization":
				return f"Bearer {access_token}"
			return default

		frappe.form_dict = frappe._dict({"cmd": "sample"})
		with patch("frappe.get_request_header", side_effect=mock_header):
			result = sample_detail(name="post-from-kwargs")
		self.assertEqual(result["name"], "post-from-kwargs")

	def test_auth_required_protects_api(self):
		access_token, _ = create_tokens(self.test_user)

		def mock_header(key, default=None):
			if key == "Authorization":
				return f"Bearer {access_token}"
			return default

		with patch("frappe.get_request_header", side_effect=mock_header):
			response = get_profile()
		self.assertEqual(response["user"], self.test_user)

	def test_refresh_token_rejected_for_api_auth(self):
		_, refresh_token = create_tokens(self.test_user)
		with patch("frappe.get_request_header", return_value=f"Bearer {refresh_token}"):
			with self.assertRaises(frappe.AuthenticationError):
				authenticate_request()

	def test_dev_test_login_bypass(self):
		from ripl.utils.dev_auth import get_dev_test_email, get_dev_test_otp

		with patch("ripl.utils.dev_auth.is_dev_auth_enabled", return_value=True):
			result = auth_service.verify_otp(get_dev_test_email(), get_dev_test_otp())
		self.assertTrue(result["success"])
		self.assertTrue(result.get("dev_mode"))
		self.assertEqual(result["user"], get_dev_test_email())

	def test_jwt_auth_hook_sets_user(self):
		access_token, _ = create_tokens(self.test_user)

		def mock_header(key, default=None):
			if key == "Authorization":
				return f"Bearer {access_token}"
			return default

		from ripl.auth import validate_jwt_auth

		with patch("frappe.get_request_header", side_effect=mock_header):
			validate_jwt_auth()
		self.assertEqual(frappe.session.user, self.test_user)

	def test_send_otp_resend_metadata(self):
		identifier = f"rate-meta-{frappe.generate_hash(length=6)}@example.com"
		self._clear_otp_keys(identifier)
		base = 1_700_000_000.0

		with patch("ripl.utils.otp_rate_limit.time.time", return_value=base):
			first = auth_service.send_otp(identifier, is_resend=False)
		self.assertFalse(first["is_resend"])
		self.assertEqual(first["resend_count"], 0)
		self.assertEqual(first["retry_after_seconds"], COOLDOWN_SECONDS)

		with patch("ripl.utils.otp_rate_limit.time.time", return_value=base + COOLDOWN_SECONDS + 1):
			second = auth_service.send_otp(identifier, is_resend=True)
		self.assertTrue(second["is_resend"])
		self.assertEqual(second["resend_count"], 1)
		self._clear_otp_keys(identifier)

	def test_send_otp_cooldown_enforced(self):
		identifier = f"rate-cooldown-{frappe.generate_hash(length=6)}@example.com"
		self._clear_otp_keys(identifier)
		base = 1_700_000_100.0

		with patch("ripl.utils.otp_rate_limit.time.time", return_value=base):
			auth_service.send_otp(identifier)

		with patch("ripl.utils.otp_rate_limit.time.time", return_value=base + 5):
			with self.assertRaises(frappe.ValidationError):
				auth_service.send_otp(identifier, is_resend=True)
		self._clear_otp_keys(identifier)

	def test_send_otp_hourly_cap_enforced(self):
		identifier = f"rate-hourly-{frappe.generate_hash(length=6)}@example.com"
		self._clear_otp_keys(identifier)
		base = 1_700_000_200.0

		for i in range(3):
			with patch(
				"ripl.utils.otp_rate_limit.time.time",
				return_value=base + i * (COOLDOWN_SECONDS + 1),
			):
				auth_service.send_otp(identifier, is_resend=bool(i))

		with patch(
			"ripl.utils.otp_rate_limit.time.time",
			return_value=base + 3 * (COOLDOWN_SECONDS + 1),
		):
			with self.assertRaises(frappe.ValidationError):
				auth_service.send_otp(identifier, is_resend=True)
		self._clear_otp_keys(identifier)

	def test_dev_test_login_rejected_when_not_dev_mode(self):
		from ripl.utils.dev_auth import get_dev_test_email, get_dev_test_otp

		with patch("ripl.utils.dev_auth.is_dev_auth_enabled", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				auth_service.verify_otp(get_dev_test_email(), get_dev_test_otp())
