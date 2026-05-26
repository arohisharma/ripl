# Copyright (c) 2026, dewansh and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from ripl.utils.html_content import extract_text_editor_images, publish_private_images_in_html


class Chapter(Document):
	def before_save(self):
		extract_text_editor_images(self, "content")
		publish_private_images_in_html(self, "content")
