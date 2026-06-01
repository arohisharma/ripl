def normalize_identifier(identifier: str | None) -> str:
	"""Normalize login identifier so send_otp and verify_otp use the same cache key."""
	if not identifier:
		return ""

	value = identifier.strip()
	if "@" in value:
		return value.lower()

	digits = "".join(char for char in value if char.isdigit())
	return digits or value.lower()


def otp_cache_key(identifier: str) -> str:
	return f"otp_{normalize_identifier(identifier)}"
