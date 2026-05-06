import frappe
from frappe.model.document import Document

class Plan(Document):

    def before_save(self):
        # Auto monthly price
        if self.price and self.duration:
            self.monthly_price = self.price / self.duration

        # Auto slug
        if not self.slug:
            self.slug = frappe.scrub(self.plan_name)