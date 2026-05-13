# Copyright (c) 2026, dewansh and contributors
# For license information, please see license.txt

# import frappe
import frappe
from frappe.model.document import Document
from frappe import _

class Post(Document):
    def validate(self):
        # Impacted Entities validation
        if self.show_impacted_entities and not self.impacted_entities:
            frappe.throw(_("Impacted Entities is required when checkbox is checked"))

        # Action Steps validation
        if self.show_action_steps and not self.action_steps:
            frappe.throw(_("Action Steps is required when checkbox is checked"))
