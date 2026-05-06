import frappe
from frappe import _
from frappe.exceptions import DoesNotExistError, ValidationError
import requests
import tempfile
from frappe.utils.file_manager import save_file
import pdfplumber
from ripl.ripl.doctype.circular.circular import download_pdf, extract_pdf_text


def _handle_unexpected_error(context):
    frappe.log_error(frappe.get_traceback(), f"{context} API error")
    frappe.throw(_("Unable to process your request right now. Please try again later."))

@frappe.whitelist(allow_guest=True)
def get_circulars():
    try:
        circulars = frappe.get_all(
            "Circular",
            filters={"status": "Published"},
            fields=[
                "name",
                "title",
                "circular_number",
                "circular_date",
                "regulator",
                "category",
                "circular_url",
                "image_url"
            ],
            order_by="circular_date desc"
        )

        return {
            "status": "success",
            "data": circulars
        }
    except (ValidationError, DoesNotExistError):
        raise
    except Exception:
        _handle_unexpected_error("get_circulars")

@frappe.whitelist(allow_guest=True)
def get_circular_detail(name):
    try:
        if not name:
            frappe.throw(_("Circular name is required."), ValidationError)

        doc = frappe.get_doc("Circular", name)

        return {
            "status": "success",
            "data": {
                "id": doc.name,
                "title": doc.title,
                "circular_number": doc.circular_number,
                "circular_date": doc.circular_date,
                "regulator": doc.regulator,
                "category": doc.category,  
                "image_url": doc.image_url,
                "ai_summary": doc.ai_summary,
                "key_points": doc.key_points,
                "impacted_entities": doc.impacted_entities if doc.show_impacted_entities else None,
                "required_actions": doc.required_actions if doc.show_required_actions else None
            }
        }
    except (ValidationError, DoesNotExistError):
        raise
    except Exception:
        _handle_unexpected_error("get_circular_detail")

@frappe.whitelist(allow_guest=True)
def get_filtered_circulars(category=None, regulator=None, search=None):
    try:
        filters = {"status": "Published"}

        if category:
            filters["category"] = category

        if regulator:
            filters["regulator"] = regulator

        circulars = frappe.get_all(
            "Circular",
            filters=filters,
            fields=[
                "name",
                "title",
                "circular_number",
                "circular_date",
                "regulator",
                "category",
                "circular_url"
            ],
            order_by="circular_date desc"
        )

        # 🔍 Search filter (title)
        if search:
            search_value = search.strip().lower()
            circulars = [c for c in circulars if search_value in c["title"].lower()]

        return {
            "status": "success",
            "data": circulars
        }
    except (ValidationError, DoesNotExistError):
        raise
    except Exception:
        _handle_unexpected_error("get_filtered_circulars")

@frappe.whitelist(allow_guest=True)
def get_latest_circulars(limit=5):
    try:
        limit = int(limit)
        if limit <= 0:
            frappe.throw(_("Limit must be a positive integer."), ValidationError)

        circulars = frappe.get_all(
            "Circular",
            filters={"status": "Published"},
            fields=[
                "name",
                "title",
                "circular_date",
                "circular_url"
            ],
            order_by="circular_date desc",
            limit_page_length=limit
        )

        return {
            "status": "success",
            "data": circulars
        }
    except ValueError:
        frappe.throw(_("Limit must be a valid integer."), ValidationError)
    except (ValidationError, DoesNotExistError):
        raise
    except Exception:
        _handle_unexpected_error("get_latest_circulars")

@frappe.whitelist()
def enqueue_ai_generation(name):
    """
    frappe.enqueue(
        "ripl.api.circular.generate_ai_data",
        name=name,
        queue="long"
    )
    return {"status": "queued"}
    """
    return {"status": "disabled"}

@frappe.whitelist()
def generate_ai_data(name):
    doc = frappe.get_doc("Circular", name)

    if not doc.circular_file:

        frappe.throw("Please upload Circular PDF")

    # 🔹 Get file from Frappe

    file_doc = frappe.get_doc("File", {"file_url": doc.circular_file})
    file_path = file_doc.get_full_path()

    # 🔹 Call Claude with file

    ai_data = call_claude(file_path)

    # 🔹 Map response

    doc.ai_summary = ai_data.get("summary")
    doc.key_points = "\n".join(ai_data.get("key_points", []))
    doc.regulator = ai_data.get("regulator")
    doc.category = ai_data.get("category")
    doc.impacted_entities = "\n".join(ai_data.get("impacted_entities", []))
    doc.required_actions = "\n".join(ai_data.get("required_actions", []))
    doc.save(ignore_permissions=True)

    return {"status": "success"}