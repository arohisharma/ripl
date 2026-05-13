import frappe
from frappe import _

# ----------------------------------------
# Helpers
# ----------------------------------------

def check_purchase(user, playbook):
    return frappe.db.exists("Playbook Purchase", {
        "user": user,
        "playbook": playbook,
        "status": "Active"
    })


# ----------------------------------------
# 1. Get Playbooks (Catalog)
# ----------------------------------------

@frappe.whitelist()
def get_playbooks():
    user = frappe.session.user

    playbooks = frappe.get_all("Playbook",
        filters={"is_active": 1},
        fields=["name", "title", "price", "duration_hours", "thumbnail"]
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
            "progress": progress
        })

    return result

# ----------------------------------------
# 3. Get Playbook Detail (Playbook outline + purchase data)
# ----------------------------------------
# 

@frappe.whitelist()
def get_playbook_detail(playbook_id):
    pb = frappe.get_doc("Playbook", playbook_id)

    # ✅ Fetch modules
    modules = frappe.get_all(
        "Module",
        filters={"playbook": pb.name},
        fields=["name", "title"],
        order_by="idx asc"
    )

    module_names = [m.name for m in modules]

    # ✅ QUIZ COUNTS (optimized - single query)
    quiz_map = {}
    total_quizzes = 0

    if module_names:
        quiz_counts = frappe.get_all(
            "Quiz",
            filters={"module": ["in", module_names]},
            fields=["module", "count(name) as count"],
            group_by="module"
        )

        quiz_map = {q.module: q.count for q in quiz_counts}
        total_quizzes = sum(quiz_map.values())

    # ✅ CHAPTER COUNTS (also optimized - single query)
    chapter_map = {}

    if module_names:
        chapter_counts = frappe.get_all(
            "Chapter",
            filters={"module": ["in", module_names]},
            fields=["module", "count(name) as count"],
            group_by="module"
        )

        chapter_map = {c.module: c.count for c in chapter_counts}

    # ✅ Build module preview
    module_data = []
    for m in modules:
        module_data.append({
            "id": m.name,
            "title": m.title,
            "chapter_count": chapter_map.get(m.name, 0),
            "quiz_count": quiz_map.get(m.name, 0)
        })

    return {
        "id": pb.name,
        "title": pb.title,
        "description": pb.description,
        "image": pb.thumbnail,
        "duration": pb.duration_hours,

        # ✅ Rich text field (no parsing)
        "learning_points": pb.learning_points,
        "designed_for": pb.designed_for,

        # ✅ counts
        "total_modules": len(modules),
        "total_quizzes": total_quizzes,

        "price": pb.price,

        # ✅ module preview
        "modules_preview": module_data
    }

# ----------------------------------------
# 3. Get Playbook Content (Modules + Chapters)
# ----------------------------------------

@frappe.whitelist()
def get_playbook_content(playbook_id):
    user = frappe.session.user

    if not check_purchase(user, playbook_id):
        frappe.throw("Access denied. Purchase required.")

    modules = frappe.get_all("Module",
        filters={"playbook": playbook_id},
        fields=["name", "title", "order"],
        order_by="order asc"
    )

    response = []

    for m in modules:
        chapters = frappe.get_all("Chapter",
            filters={"module": m.name},
            fields=["name", "title", "order"],
            order_by="order asc"
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
                "content": frappe.db.get_value("Chapter", ch.name, "content"),
                "order": ch.order,
                "is_completed": status == "Completed"
            })

        # Quiz info
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
            "chapters": chapter_list,
            "quiz": quiz_data
        })

        return {
            "name": playbook_id,
            "title": frappe.db.get_value("Playbook", playbook_id, "title"),
            "description": frappe.db.get_value("Playbook", playbook_id, "description"),
            "modules": response
        }


# ----------------------------------------
# 4. Get Chapter Content
# ----------------------------------------

@frappe.whitelist()
def get_chapter(chapter_id):
    chapter = frappe.get_doc("Chapter", chapter_id)

    return {
        "id": chapter.name,
        "title": chapter.title,
        "content": chapter.content,
        "read_time": chapter.read_time_mins
    }


# ----------------------------------------
# 5. Mark Chapter Progress
# ----------------------------------------

@frappe.whitelist()
def mark_chapter_progress(chapter_id, status):
    user = frappe.session.user

    existing = frappe.db.exists("Chapter Progress", {
        "user": user,
        "chapter": chapter_id
    })

    if existing:
        doc = frappe.get_doc("Chapter Progress", existing)
        doc.status = status
        doc.save()
    else:
        frappe.get_doc({
            "doctype": "Chapter Progress",
            "user": user,
            "chapter": chapter_id,
            "status": status
        }).insert()

    return "Success"


# ----------------------------------------
# 6. Get Quiz
# ----------------------------------------

@frappe.whitelist()
def get_quiz(module_id):
    quiz = frappe.get_doc("Quiz", {"module": module_id})

    questions = frappe.get_all("Question",
        filters={"quiz": quiz.name},
        fields=["name", "question_text", "explanation", "order"],
        order_by="order asc"
    )

    question_list = []

    for q in questions:
        options = frappe.get_all("Option",
            filters={"question": q.name},
            fields=["name", "option_text", "is_correct"]
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
            "explanation": q.explanation
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
def submit_answer(question_id, selected_option_id):
    correct = frappe.db.get_value("Option", {
        "question": question_id,
        "is_correct": 1
    }, "name")

    explanation = frappe.db.get_value("Question", question_id, "explanation")

    return {
        "is_correct": selected_option_id == correct,
        "correct_option_id": correct,
        "explanation": explanation
    }


# ----------------------------------------
# 8. Submit Quiz (Final)
# ----------------------------------------

@frappe.whitelist()
def submit_quiz(quiz_id, answers):
    import json

    user = frappe.session.user
    answers = json.loads(answers)

    total = len(answers)
    correct_count = 0

    for ans in answers:
        correct = frappe.db.get_value("Option", {
            "question": ans["question_id"],
            "is_correct": 1
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
        doc.score = score
        doc.passed = passed
        doc.attempts += 1
        doc.save()
    else:
        frappe.get_doc({
            "doctype": "Quiz Attempt",
            "user": user,
            "quiz": quiz_id,
            "score": score,
            "passed": passed,
            "attempts": 1
        }).insert()

    return {
        "score": score,
        "passed": passed
    }