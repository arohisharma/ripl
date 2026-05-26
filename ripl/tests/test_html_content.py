import frappe
from frappe.tests.utils import FrappeTestCase

from ripl.utils.html_content import prepare_richtext_html_for_api


class TestHtmlContent(FrappeTestCase):
	def test_prepare_richtext_html_for_api_absolute_urls(self):
		html = '<div class="ql-editor"><img src="/files/chapter.png"></div>'
		result = prepare_richtext_html_for_api(html)
		self.assertIn(frappe.utils.get_url("/files/chapter.png"), result)
		self.assertNotIn('src="/files/chapter.png"', result)

	def test_prepare_richtext_html_for_api_private_files(self):
		html = '<img src="/private/files/chapter.png?fid=FILE-001">'
		result = prepare_richtext_html_for_api(html)
		self.assertTrue(result.startswith("<img src=\""))
		self.assertIn("/private/files/chapter.png", result)
