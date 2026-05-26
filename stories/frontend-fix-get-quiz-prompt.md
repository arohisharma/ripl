---
title: Frontend Fix — get_quiz module_id undefined
type: story
status: active
created: 2026-05-23
audience: frontend
tags: [playbook, quiz, bugfix]
---

# Frontend Prompt — Fix `get_quiz` (`module_id=undefined`)

**Copy and share with the frontend team.**

---

## Problem

This request is failing:

```http
GET /api/method/ripl.api.playbook.get_quiz?module_id=undefined
```

Backend error:

```text
Quiz {'module': 'undefined'} not found
```

**Root cause:** The app is sending the JavaScript value `undefined`, which becomes the **string** `"undefined"` in the URL. That is not a valid Module id.

This is a **frontend bug**, not an auth or backend API design issue.

---

## What you must send

| Param | Required | Must be |
|-------|----------|---------|
| `module_id` | Yes | Real **Module** document name from backend (e.g. `"abc123xyz"`) |
| NOT | — | `"undefined"`, `null`, empty string, or `quiz_id` |

`get_quiz` loads the quiz **by module**, not by quiz id.

---

## Where to get `module_id`

Call **`get_playbook_content`** first:

```http
GET /api/method/ripl.api.playbook.get_playbook_content?playbook_id=m2eq01lh6n
Authorization: Bearer <access_token>
```

Response shape (`message`):

```json
{
  "name": "m2eq01lh6n",
  "title": "...",
  "modules": [
    {
      "module_id": "REAL_MODULE_NAME_HERE",
      "title": "Module 1",
      "chapters": [...],
      "quiz": {
        "quiz_id": "QUIZ_DOC_NAME",
        "passed": false
      }
    }
  ]
}
```

Use **`modules[i].module_id`** for `get_quiz`.

Do **not** use `modules[i].quiz.quiz_id` for this API.

---

## Correct API call

```http
GET /api/method/ripl.api.playbook.get_quiz?module_id=<REAL_MODULE_ID>
Authorization: Bearer <access_token>
```

Example:

```http
GET /api/method/ripl.api.playbook.get_quiz?module_id=mod-abc-123
```

---

## Code fix (TypeScript)

### ❌ Wrong (causes your bug)

```ts
// moduleId is undefined when user taps quiz too early
const moduleId = selectedModule?.id; // wrong field — should be module_id

fetch(`${BASE}/api/method/ripl.api.playbook.get_quiz?module_id=${moduleId}`);
// → module_id=undefined in URL
```

### ✅ Correct

```ts
async function loadQuiz(moduleId: string) {
  if (!moduleId || moduleId === "undefined") {
    console.error("Invalid module_id", moduleId);
    return;
  }

  const token = localStorage.getItem("access_token");
  const res = await fetch(
    `${BASE_URL}/api/method/ripl.api.playbook.get_quiz?module_id=${encodeURIComponent(moduleId)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const json = await res.json();
  if (!res.ok) throw json;
  return json.message;
}

// After get_playbook_content:
const content = await loadPlaybookContent(playbookId);
const module = content.modules[0];
const quiz = await loadQuiz(module.module_id); // ← use module_id
```

### Guard before every API call

```ts
function assertId(value: unknown, label: string): string {
  if (
    value === undefined ||
    value === null ||
    value === "" ||
    value === "undefined"
  ) {
    throw new Error(`Missing or invalid ${label}`);
  }
  return String(value);
}

// Usage
const moduleId = assertId(module.module_id, "module_id");
await loadQuiz(moduleId);
```

---

## Common frontend mistakes

| Mistake | Result |
|---------|--------|
| Using `module.id` instead of `module.module_id` | `undefined` in URL |
| Calling `get_quiz` before `get_playbook_content` loads | `undefined` |
| Passing `quiz.quiz_id` to `get_quiz` | Wrong lookup / not found |
| Template string with unset state variable | `module_id=undefined` |
| Optional chaining skipped, no validation | Silent `"undefined"` string |

---

## Field name reference

| API | Param name | Source in UI |
|-----|------------|--------------|
| `get_playbook_content` | `playbook_id` | Playbook list item `.id` |
| `get_quiz` | `module_id` | Content response `modules[].module_id` |
| `get_chapter` | `chapter_id` | Content `modules[].chapters[].name` |
| `mark_chapter_progress` | `chapter_id` | Same chapter `name` |
| `submit_quiz` | `quiz_id` | From `get_quiz` response `.name` |

---

## Success response (`get_quiz`)

```json
{
  "name": "quiz-doc-name",
  "pass_percentage": 70,
  "questions": [
    {
      "id": "question-id",
      "question": "...",
      "options": [{ "id": "...", "text": "..." }]
    }
  ]
}
```

Read from `response.message`.

---

## Checklist

- [ ] Stop calling API when `module_id` is missing
- [ ] Use `module.module_id` from `get_playbook_content` (not `.id`, not `quiz_id`)
- [ ] Add `assertId()` / validation before fetch
- [ ] Use `encodeURIComponent(moduleId)` in URL
- [ ] Send `Authorization: Bearer <token>`
- [ ] Verify in Network tab: URL shows real id, not `undefined`

---

## How to verify in browser

1. Open DevTools → Network  
2. Trigger quiz screen  
3. Confirm URL looks like:  
   `...get_quiz?module_id=someRealDocName`  
4. Must **not** contain `module_id=undefined`

---

**Related:** [frontend-api-request-contract-prompt.md](./frontend-api-request-contract-prompt.md)
