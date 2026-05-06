import frappe
import requests
import tempfile
import pdfplumber
from frappe.model.document import Document
from frappe.utils import now


# =========================================================
# 📦 DOCTYPE CONTROLLER (runs on document events)
# =========================================================

class Circular(Document):

    def validate(self):

        # ✅ File is mandatory
        if not self.circular_file:
            frappe.throw("Please upload Circular PDF")

        # ✅ Title is mandatory
        if not self.title:
            frappe.throw("Title is required")


    def before_save(self):
        """
        This runs every time the document is saved.
        Used for auto-filling fields.
        """

        # ✅ Auto timestamp when status becomes Published
        if self.status == "Published" and not self.published_date:
            self.published_date = now()

        # ✅ Auto set publisher (current logged-in user)
        if self.status == "Published" and not self.published_by:
            self.published_by = frappe.session.user


# =========================================================
# 🔹 API: Trigger AI Processing (called from frontend button)
# =========================================================

@frappe.whitelist()
def enqueue_ai_generation(name):
    """
    This API is triggered when user clicks
    'Generate AI Summary' button.

    It does NOT process immediately.
    Instead, it sends job to background queue.
    """

    frappe.enqueue(
        "ripl.api.circular.generate_ai_data",  # path to function
        name=name,
        queue="long"  # long queue for heavy tasks (PDF + AI)
    )

    return {"status": "queued"}


# =========================================================
# 🤖 MAIN WORKER FUNCTION (runs in background)
# =========================================================

def generate_ai_data(name):
    """
    This runs asynchronously in worker.

    Steps (to be implemented next):
    1. Fetch Circular doc
    2. Download PDF
    3. Extract text
    4. Call Claude API
    5. Save AI-generated fields
    """

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


# =========================================================
# 🧩 HELPER FUNCTIONS (to be implemented)
# =========================================================

def download_pdf(url):

    try:

        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

        print("Status:", response.status_code)

        print("Content-Type:", response.headers.get("Content-Type"))

        if response.status_code != 200:

            frappe.throw(f"Download failed: {response.status_code}")

        # 🚨 Validate it's actually a PDF

        if "pdf" not in response.headers.get("Content-Type", "").lower():

            frappe.throw("URL did not return a PDF. It may be blocked or redirected.")

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

        temp.write(response.content)

        temp.close()

        return temp.name

    except Exception as e:

        frappe.log_error(frappe.get_traceback(), "PDF Download Failed")

        frappe.throw(f"Download failed: {str(e)}")


def extract_pdf_text(path):
    text = ""

    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                print(f"Page {i} text: {page_text}")
                text += page_text

        if not text.strip():
            frappe.throw("No text found → likely scanned PDF")

        return text[:200000]

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "PDF Text Extraction Failed")
        frappe.throw(f"Extraction failed: {str(e)}")  # ✅ KEEP ORIGINAL ERROR


def call_claude(text):
    """
    Sends text to Claude API
    and returns structured response.
    """
    pass


def get_prompt(text):
    """
    Builds prompt for Claude.
    """
    pass


def parse_response(response):
    """
    Converts Claude response into JSON/dict.
    """
    pass