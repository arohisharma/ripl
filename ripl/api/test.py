import frappe
from ripl.api.auth import auth_required

@frappe.whitelist(allow_guest=True)
@auth_required
def get_profile(user=None):
    return {
        "message": "You are authenticated",
        "user": user
    }