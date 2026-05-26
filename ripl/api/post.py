import frappe
from frappe import _
from ripl.api.auth import auth_required

# -------------------------
# CREATE POST
# -------------------------
@frappe.whitelist()
@auth_required
def create_post(data, user=None):
    """
    Create a new Post
    """
    if isinstance(data, str):
        data = frappe.parse_json(data)

    doc = frappe.new_doc("Post")

    doc.title = data.get("title")
    doc.circular_number = data.get("circular_number")
    doc.date = data.get("date")
    doc.regulator = data.get("regulator")
    doc.category = data.get("category")
    doc.summary = data.get("summary")
    doc.key_points = data.get("key_points")

    doc.show_impacted_entities = data.get("show_impacted_entities", 1)
    doc.show_action_steps = data.get("show_action_steps", 1)

    doc.impacted_entities = data.get("impacted_entities")
    doc.action_steps = data.get("action_steps")

    doc.circular_pdf = data.get("circular_pdf")
    doc.image_url = data.get("image_url")

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "message": "Post created successfully",
        "name": doc.name
    }


# -------------------------
# GET LIST (FEED)
# -------------------------
@frappe.whitelist()
@auth_required
def get_posts(limit=10, offset=0, user=None):
    posts = frappe.get_all(
        "Post",
        fields=[
            "name",
            "title",
            "date",
            "regulator",
            "category",
            "image_url"
        ],
        order_by="date desc",
        limit=limit,
        start=offset
    )

    return posts


# -------------------------
# GET SINGLE POST DETAIL
# -------------------------
@frappe.whitelist()
@auth_required
def get_post_detail(name, user=None):
    doc = frappe.get_doc("Post", name)

    return {
        "name": doc.name,
        "title": doc.title,
        "circular_number": doc.circular_number,
        "date": doc.date,
        "regulator": doc.regulator,
        "category": doc.category,
        "summary": doc.summary,
        "key_points": doc.key_points,
        "show_impacted_entities": doc.show_impacted_entities,
        "show_action_steps": doc.show_action_steps,
        "impacted_entities": doc.impacted_entities,
        "action_steps": doc.action_steps,
        "circular_pdf": doc.circular_pdf,
        "image_url": doc.image_url
    }


# -------------------------
# DELETE POST (OPTIONAL)
# -------------------------
@frappe.whitelist()
@auth_required
def delete_post(name, user=None):
    frappe.delete_doc("Post", name, ignore_permissions=True)
    frappe.db.commit()

    return {"message": "Deleted successfully"}
