import frappe


def execute():
	"""Remove deprecated Circular DocType (replaced by Post for regulatory content)."""
	frappe.delete_doc_if_exists("DocType", "Circular", force=True)
