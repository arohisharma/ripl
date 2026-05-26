import frappe

LOGGER_NAME = "ripl.auth"


def get_logger():
	return frappe.logger(LOGGER_NAME)


def log_event(event: str, level: str = "info", **context):
	logger = get_logger()
	message = _format_message(event, context)
	getattr(logger, level, logger.info)(message)


def log_error_event(event: str, exc: BaseException | None = None, **context):
	context = {**context, "error": str(exc) if exc else None, "error_type": type(exc).__name__ if exc else None}
	log_event(event, level="error", **context)
	if exc:
		frappe.log_error(
			title=f"ripl.auth: {event}",
			message=_format_message(event, context) + f"\n\n{frappe.get_traceback()}",
		)


def _format_message(event: str, context: dict) -> str:
	parts = [f"[{event}]"]
	for key, value in context.items():
		if value is not None:
			parts.append(f"{key}={value}")
	return " | ".join(parts)


def mask_identifier(identifier: str | None) -> str | None:
	if not identifier:
		return identifier
	if "@" in identifier:
		local, domain = identifier.split("@", 1)
		masked_local = (local[:2] + "***") if len(local) > 2 else "***"
		return f"{masked_local}@{domain}"
	if len(identifier) > 4:
		return identifier[:2] + "***" + identifier[-2:]
	return "***"
