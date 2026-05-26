import re

import frappe
from frappe.utils import get_url


_FILE_SRC_RE = re.compile(
	r"""src=["']((?:/private)?/files/[^"']+)["']""",
	re.IGNORECASE,
)
_PRIVATE_FILE_PATH_RE = re.compile(r"/private/files/[^\"'?\s>]+")


def extract_text_editor_images(doc, fieldname: str = "content") -> None:
	"""Persist pasted data-URI images as File records linked to the document."""
	from frappe.core.doctype.file.utils import extract_images_from_doc

	extract_images_from_doc(doc, fieldname)


def publish_private_images_in_html(doc, fieldname: str = "content") -> None:
	"""Move embedded private images to public files and update HTML src paths."""
	content = doc.get(fieldname) or ""
	if "/private/files/" not in content:
		return

	updated = content
	for file_url in set(_PRIVATE_FILE_PATH_RE.findall(content)):
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": file_url,
				"attached_to_doctype": doc.doctype,
				"attached_to_name": doc.name,
			},
			"name",
		)
		if not file_name:
			continue

		file_doc = frappe.get_doc("File", file_name)
		if file_doc.is_private:
			file_doc.is_private = 0
			file_doc.save(ignore_permissions=True)

		public_url = file_doc.file_url
		updated = re.sub(
			re.escape(file_url) + r"(?:\?[^\"'>\s]*)?",
			public_url,
			updated,
		)

	if updated != content:
		doc.set(fieldname, updated)


def prepare_richtext_html_for_api(html: str | None) -> str | None:
	"""Return richtext HTML with embed file paths as absolute URLs for clients."""
	if not html:
		return html

	def replace_src(match: re.Match) -> str:
		path = match.group(1)
		if path.startswith(("http://", "https://", "data:")):
			return match.group(0)
		return f'src="{get_url(path)}"'

	return _FILE_SRC_RE.sub(replace_src, html)
