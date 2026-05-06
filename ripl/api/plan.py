import frappe
from frappe import _
from frappe.exceptions import ValidationError

@frappe.whitelist(allow_guest=True)
def get_plans():
    try:
        plans = frappe.get_all(
            "Plan",
            filters={"is_active": 1},
            fields=[
                "name",
                "plan_name",
                "price",
                "duration",
                "tag",
                "is_highlighted",
                "sort_order"
            ],
            order_by="sort_order asc"
        )

        result = []

    for plan in plans:
        # 🔹 Calculate monthly price safely
        monthly_price = 0
        if plan.get("price") and plan.get("duration"):
            monthly_price = plan["price"] / plan["duration"]

        # 🔹 Get features
        features = frappe.get_all(
            "Plan Feature",
            filters={"parent": plan["name"]},
            fields=["feature"]
        )

            result.append({
                "id": plan["name"],
                "title": plan["plan_name"],
                "price": plan["price"],
                "monthly_price": round(monthly_price),
                "duration": plan["duration"],
                "tag": plan.get("tag"),
                "is_highlighted": plan.get("is_highlighted"),
                "features": [f["feature"] for f in features]
            })

        return result
    except ValidationError:
        raise
    except Exception:
        frappe.log_error(frappe.get_traceback(), "get_plans API error")
        frappe.throw(_("Unable to fetch plans right now. Please try again later."))