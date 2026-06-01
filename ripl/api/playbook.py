import json

import frappe
from frappe import _
from ripl.api.auth import auth_required, subscription_required
from ripl.utils.html_content import prepare_richtext_html_for_api

# ----------------------------------------
# Helpers
# ----------------------------------------

# `order` is a reserved SQL keyword — must quote the column in order_by clauses.
_MODULE_ORDER_BY = "`tabModule`.`order` asc"
_CHAPTER_ORDER_BY = "`tabChapter`.`order` asc"
_QUESTION_ORDER_BY = "`tabQuestion`.`order` asc"
_OPTION_ORDER_BY = "`tabOption`.`idx` asc"


def check_purchase(user, playbook):
    return frappe.db.exists("Playbook Purchase", {
        "user": user,
        "playbook": playbook,
        "status": "Active"
    })


# ----------------------------------------
# Sandbox purchase (until payment gateway)
# ----------------------------------------

@frappe.whitelist()
@auth_required
@subscription_required
def playbook_purchase(playbook_id, user=None):
    """
    Mark the playbook as purchased for the current user by creating or reactivating
    a Playbook Purchase row. Real payments will replace this flow later.
    """
    if user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    if not frappe.db.exists("Playbook", {"name": playbook_id, "is_active": 1}):
        frappe.throw(_("Playbook not found or inactive"), frappe.DoesNotExistError)

    existing = frappe.db.exists("Playbook Purchase", {
        "user": user,
        "playbook": playbook_id,
    })

    if existing:
        doc = frappe.get_doc("Playbook Purchase", existing)
        doc.status = "Active"
        doc.purchase_date = frappe.utils.now_datetime()
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Playbook Purchase",
            "user": user,
            "playbook": playbook_id,
            "status": "Active",
            "purchase_date": frappe.utils.now_datetime(),
        }).insert(ignore_permissions=True)

    return {
        "playbook_id": playbook_id,
        "is_purchased": True,
    }


# ----------------------------------------
# 1. Get Playbooks (Catalog)
# ----------------------------------------

@frappe.whitelist()
@auth_required
@subscription_required
def get_playbooks(user=None):
    playbooks = frappe.get_all("Playbook",
        filters={"is_active": 1},
        fields=["name", "title", "price", "duration_hours", "thumbnail", "total_modules", "total_questions"]
    )

    result = []

    for pb in playbooks:
        purchased = check_purchase(user, pb.name)

        progress = frappe.db.get_value("Playbook Progress", {
            "user": user,
            "playbook": pb.name
        }, "completion_percentage") or 0

        result.append({
            "id": pb.name,
            "title": pb.title,
            "price": pb.price,
            "duration": f"{pb.duration_hours} hrs" if pb.duration_hours else None,
            "image": pb.thumbnail,
            "is_purchased": bool(purchased),
            "progress": progress,
            "total_modules": pb.total_modules,
            "total_questions": pb.total_questions
        })

    return result

# ----------------------------------------
# 3. Get Playbook Detail (Playbook outline + purchase data)
# ----------------------------------------
#

@frappe.whitelist()
@auth_required
@subscription_required
def get_playbook_detail(playbook_id, user=None):
    pb = frappe.get_doc("Playbook", playbook_id)

    result = {
        "id": pb.name,
        "title": pb.title,
        "image": pb.thumbnail,

        # ✅ Rich text field (no parsing)
        "learning_points": pb.learning_points,
        "designed_for": pb.designed_for,

        # ✅ counts
        "total_modules": pb.total_modules,
        "total_quizzes": pb.total_quizzes,
        "total_questions": pb.total_questions,

        # meta data
        "duration": pb.duration_hours,
        "price": pb.price,
        "is_purchased": bool(check_purchase(user, pb.name)),

        # ✅ module previews
        "description": pb.description,
        "references": pb.references
    }

    return result

# ----------------------------------------
# 3. Get Playbook Content (Modules + Chapters)
# ----------------------------------------

@frappe.whitelist()
@auth_required
@subscription_required
def get_playbook_content(playbook_id, user=None):
    if not check_purchase(user, playbook_id):
        frappe.throw("Access denied. Purchase required.")

    modules = frappe.get_all(
        "Module",
        filters={"playbook": playbook_id},
        fields=["name", "title", "order"],
        order_by=_MODULE_ORDER_BY,
    )

    response = []

    for m in modules:
        chapters = frappe.get_all(
            "Chapter",
            filters={"module": m.name},
            fields=["name", "title", "order"],
            order_by=_CHAPTER_ORDER_BY,
        )

        chapter_list = []
        previous_completed = True

        for ch in chapters:
            progress = frappe.db.get_value("Chapter Progress", {
                "user": user,
                "chapter": ch.name
            }, "status")

            status = progress or "Not Started"

            if not previous_completed:
                final_status = "locked"
            else:
                if status == "Completed":
                    final_status = "completed"
                elif status == "In Progress":
                    final_status = "in_progress"
                else:
                    final_status = "not_started"

            previous_completed = (status == "Completed")

            chapter_list.append({
                "name": ch.name,
                "title": ch.title,
                "content": prepare_richtext_html_for_api(
                    frappe.db.get_value("Chapter", ch.name, "content")
                ),
                "order": ch.order,
                "is_completed": status == "Completed"
            })

        # Quiz info
        quiz_count = frappe.db.count("Quiz", {"module": m.name})
        quiz = frappe.db.get_value("Quiz", {"module": m.name}, ["name"], as_dict=1)

        quiz_data = None
        if quiz:
            attempt = frappe.db.get_value("Quiz Attempt", {
                "user": user,
                "quiz": quiz.name
            }, ["passed"], as_dict=1)

            quiz_data = {
                "quiz_id": quiz.name,
                "passed": attempt.passed if attempt else False
            }

        response.append({
            "module_id": m.name,
            "title": m.title,
            "chapter_count": len(chapter_list),
            "quiz_count": quiz_count,
            "chapters": chapter_list,
            "quiz": quiz_data
        })

    return {
        "name": playbook_id,
        "title": frappe.db.get_value("Playbook", playbook_id, "title"),
        "description": frappe.db.get_value("Playbook", playbook_id, "description"),
        "modules": response,
    }


# ----------------------------------------
# 4. Get Chapter Content
# ----------------------------------------

@frappe.whitelist()
@auth_required
def get_chapter(chapter_id, user=None):
    chapter = frappe.get_doc("Chapter", chapter_id)

    return {
        "id": chapter.name,
        "title": chapter.title,
        "content": prepare_richtext_html_for_api(chapter.content),
        "read_time": chapter.read_time_mins
    }


# ----------------------------------------
# 5. Mark Chapter Progress
# ----------------------------------------

@frappe.whitelist()
@auth_required
def mark_chapter_progress(chapter_id, status, user=None):
    if not user or user == "Guest":
        frappe.throw(_("Login required"), frappe.AuthenticationError)

    existing = frappe.db.exists("Chapter Progress", {
        "user": user,
        "chapter": chapter_id,
    })

    if existing:
        doc = frappe.get_doc("Chapter Progress", existing)
        if doc.user != user:
            frappe.throw(_("Not permitted"), frappe.PermissionError)
        doc.status = status
        doc.last_read_at = frappe.utils.now_datetime()
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Chapter Progress",
            "user": user,
            "chapter": chapter_id,
            "status": status,
            "last_read_at": frappe.utils.now_datetime(),
        }).insert(ignore_permissions=True)

    return "Success"


# ----------------------------------------
# 6. Get Quiz
# ----------------------------------------

@frappe.whitelist()
@auth_required
def get_quiz(module_id, user=None):
    quiz = frappe.get_doc("Quiz", {"module": module_id})

    questions = frappe.get_all(
        "Question",
        filters={"quiz": quiz.name},
        fields=["name", "question_text", "explanation", "order"],
        order_by=_QUESTION_ORDER_BY,
    )

    question_list = []

    for q in questions:
        options = frappe.get_all(
            "Option",
            filters={"parent": q.name, "parenttype": "Question", "parentfield": "options"},
            fields=["name", "option_text", "is_correct"],
            order_by=_OPTION_ORDER_BY,
        )

        formatted_options = []
        correct_option_id = None

        for opt in options:
            formatted_options.append({
                "id": opt.name,
                "text": opt.option_text
            })

            if opt.is_correct:
                correct_option_id = opt.name

        question_list.append({
            "id": q.name,
            "question": q.question_text,
            "options": formatted_options,
            "explanation": q.explanation,
            "correct_option_id": correct_option_id
        })

    return {
        "name": quiz.name,
        "pass_percentage": quiz.pass_percentage,
        "questions": question_list
    }


# ----------------------------------------
# 7. Submit Answer (Instant Feedback)
# ----------------------------------------

@frappe.whitelist()
@auth_required
def submit_answer(question_id, selected_option_id, user=None):
    correct = frappe.db.get_value("Option", {
        "parent": question_id,
        "parenttype": "Question",
        "parentfield": "options",
        "is_correct": 1,
    }, "name")

    question = frappe.db.get_value(
        "Question",
        question_id,
        ["explanation", "practitioner_insight"],
        as_dict=True,
    ) or {}

    return {
        "is_correct": selected_option_id == correct,
        "correct_option_id": correct,
        "explanation": question.get("explanation"),
        "practitioner_insight": question.get("practitioner_insight"),
    }


# ----------------------------------------
# 8. Submit Quiz (Final)
# ----------------------------------------

@frappe.whitelist()
@auth_required
def submit_quiz(quiz_id, answers, user=None):
    answers = json.loads(answers)

    total = len(answers)
    correct_count = 0

    for ans in answers:
        correct = frappe.db.get_value("Option", {
            "parent": ans["question_id"],
            "parenttype": "Question",
            "parentfield": "options",
            "is_correct": 1,
        }, "name")

        if ans["option_id"] == correct:
            correct_count += 1

    score = (correct_count / total) * 100 if total else 0

    pass_percentage = frappe.db.get_value("Quiz", quiz_id, "pass_percentage")
    passed = score >= pass_percentage

    existing = frappe.db.exists("Quiz Attempt", {
        "user": user,
        "quiz": quiz_id
    })

    if existing:
        doc = frappe.get_doc("Quiz Attempt", existing)
        if doc.user != user:
            frappe.throw(_("Not permitted"), frappe.PermissionError)
        doc.score = score
        doc.passed = passed
        doc.attempts += 1
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({
            "doctype": "Quiz Attempt",
            "user": user,
            "quiz": quiz_id,
            "score": score,
            "passed": passed,
            "attempts": 1,
        }).insert(ignore_permissions=True)

    return {
        "score": score,
        "passed": passed
    }
