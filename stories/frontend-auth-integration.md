---
title: Frontend Login & Authentication Integration
type: story
status: active
created: 2026-05-21
tags: [auth, otp, jwt, frontend, api]
related_code:
  - ripl/api/auth.py
  - ripl/api/login.py
  - ripl/services/auth_service.py
  - ripl/utils/token.py
  - ripl/auth.py
---

# RIPL Frontend — Login & Authentication Integration Guide

> **Story** — Reference doc for frontend OTP login, JWT tokens, and API integration.  
> Canonical path: `apps/ripl/stories/frontend-auth-integration.md`

This document describes how to integrate the RIPL mobile/web frontend with the Frappe backend OTP login and JWT authentication.

---

## Table of contents

1. [Overview](#overview)
2. [Base URL & API format](#base-url--api-format)
3. [Authentication flow](#authentication-flow)
4. [Token handling](#token-handling)
5. [Dev mode test credentials](#dev-mode-test-credentials)
6. [Public APIs (no token)](#public-apis-no-token)
7. [Protected APIs (Bearer token required)](#protected-apis-bearer-token-required)
8. [Error handling](#error-handling)
9. [Frontend implementation checklist](#frontend-implementation-checklist)
10. [Code examples](#code-examples)

---

## Overview

| Item | Detail |
|------|--------|
| Auth type | OTP login → JWT Bearer tokens |
| Session/cookies | **Not used** — do not rely on Frappe session cookies |
| Header | `Authorization: Bearer <access_token>` |
| Token issuer | Backend (`ripl.api.auth.verify_otp`) |
| Access token lifetime | 1 day |
| Refresh token lifetime | 7 days (stored for future use; **no refresh API yet**) |

The backend registers a Frappe `auth_hook` so JWT is validated **before** API handlers run. Protected endpoints will return **401** if the Bearer token is missing, invalid, or expired.

---

## Base URL & API format

| Environment | Example base URL |
|-------------|------------------|
| Local bench | `http://site1.local:8000` or your machine IP, e.g. `http://192.168.0.x:8000` |

All endpoints use Frappe’s RPC style:

```
{BASE_URL}/api/method/{dotted.python.path}
```

### Request methods

- **POST** — login APIs (`send_otp`, `verify_otp`); body as JSON or form-urlencoded
- **GET / POST** — most data APIs (query params or JSON body)

### Response wrapper (important)

Frappe wraps successful return values in a **`message`** field:

```json
{
  "message": { ... actual payload ... }
}
```

Always read **`response.message`** (or `data.message` in axios), not the root object.

### Example

```ts
const res = await fetch(`${BASE_URL}/api/method/ripl.api.auth.verify_otp`, { ... });
const json = await res.json();
const payload = json.message; // ← tokens live here
```

---

## Authentication flow

```
┌─────────────┐     send_otp      ┌─────────────┐
│  Screen 1   │ ────────────────► │   Backend   │
│  identifier │                   │  (cache OTP)│
└─────────────┘                   └─────────────┘
       │
       ▼
┌─────────────┐     verify_otp    ┌─────────────┐
│  Screen 2   │ ────────────────► │   Backend   │
│  6-digit OTP│ ◄──────────────── │ JWT tokens  │
└─────────────┘   access_token    └─────────────┘
                  refresh_token
                  user
       │
       ▼
 Store access_token → use on all protected API calls
```

### Step 1 — Send OTP

**Endpoint:** `POST /api/method/ripl.api.auth.send_otp`

**Alternate:** `POST /api/method/ripl.api.login.send_otp` (same behavior)

**Body:**

```json
{
  "identifier": "user@example.com",
  "is_resend": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `identifier` | Yes | Email or phone |
| `is_resend` | No | Pass `true` when user taps **Resend OTP** (analytics). Backend also auto-detects resends. |

**Resend:** Call the **same** `send_otp` endpoint again with the same `identifier` and `is_resend: true`. No separate resend API.

**Rate limits (backend enforced):**

| Rule | Value |
|------|--------|
| Cooldown between sends | **30 seconds** |
| Max sends per hour | **3** per `identifier` |

**Success (`message`):**

```json
{
  "success": true,
  "message": "OTP sent",
  "is_resend": false,
  "resend_count": 0,
  "retry_after_seconds": 30,
  "cooldown_seconds": 30,
  "expires_in_seconds": 300,
  "max_hourly_attempts": 3,
  "hourly_attempts_used": 1,
  "hourly_attempts_remaining": 2
}
```

| Response field | Use on frontend |
|----------------|-----------------|
| `retry_after_seconds` | Disable resend button for this many seconds |
| `cooldown_seconds` | Same as above (constant 30) |
| `expires_in_seconds` | OTP validity countdown (300) |
| `is_resend` | Analytics / UI copy |
| `resend_count` | Analytics (0 = first send, 1+ = resends in current hour) |
| `hourly_attempts_remaining` | Show “X attempts left” if useful |

**Rate limit errors:** `ValidationError` with message e.g. “Please wait N seconds…” or “Maximum OTP requests reached…”

**Dev / staging extra fields** (when staging auth is enabled — see [STAGING_OTP_RUNBOOK.md](../docs/STAGING_OTP_RUNBOOK.md)):

With `ripl_staging_auth` + `ripl_expose_otp_in_response` on the site (staging only):

```json
{
  "success": true,
  "message": "OTP sent",
  "dev_mode": true,
  "dev_test_otp": "482917",
  "expires_in_seconds": 300
}
```

With `developer_mode` and the dev test email (`test@ripl.dev` by default):

```json
{
  "success": true,
  "message": "OTP sent",
  "dev_mode": true,
  "dev_test_email": "test@ripl.dev",
  "dev_test_otp": "123456"
}
```

**Where to read OTP on staging**

| Method | Location |
|--------|----------|
| API | `message.dev_test_otp` when `ripl_expose_otp_in_response` is on |
| Desk | **Error Log** → search `RIPL OTP` (when `ripl_log_otp_to_error_log` or `developer_mode`) |
| Test account | `test@ripl.dev` / `123456` when staging auth is enabled |

**Production:** set `ripl_production: 1`. No OTP in response or Error Log.

Identifiers are normalized (email lowercased; phone digits only) — use the same identifier for send and verify.

SMS/email delivery is **not** live yet — use staging flags above until delivery ships.

---

### Step 2 — Verify OTP (login)

**Endpoint:** `POST /api/method/ripl.api.auth.verify_otp`

**Alternate:** `POST /api/method/ripl.api.login.verify_otp`

**Body:**

```json
{
  "identifier": "user@example.com",
  "otp": "123456"
}
```

**Success (`message`):**

```json
{
  "success": true,
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "user": "user@example.com"
}
```

Optional in dev test login:

```json
{
  "dev_mode": true
}
```

**Frontend action on success:**

1. Save `access_token` (required).
2. Optionally save `refresh_token` and `user`.
3. Navigate to the main app.
4. Attach `Authorization: Bearer <access_token>` on every protected request.

**Common errors:**

| Error message | Meaning | UI action |
|---------------|---------|-----------|
| `OTP expired` | No OTP in cache or expired | Resend OTP |
| `Invalid OTP` | Wrong code | Retry |
| `Missing fields` | Empty identifier/otp | Validate form |
| `Email or phone required` | Empty identifier on send | Validate form |

---

## Token handling

### Storage

Recommended keys (example):

| Key | Value |
|-----|--------|
| `access_token` | JWT from `verify_otp` |
| `refresh_token` | JWT (future refresh flow) |
| `user` | Logged-in user id/email |

Use `localStorage`, `sessionStorage`, or secure native storage — team choice.

### Authenticated requests

Every **protected** API call must include:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Logout

1. Clear stored tokens and user.
2. Redirect to login screen.

### Token expiry

- Access token expires in **1 day**.
- There is **no** `refresh_token` API yet — user must log in again with OTP when access token expires.
- On **401** / authentication errors → clear tokens and redirect to login.

### What not to use

- Do not use Frappe session cookies (`sid`).
- Do not use `frappe.session.user` on the client.
- Do not send refresh token for data APIs (only access token).

---

## Dev mode test credentials

Active only when backend `developer_mode: 1` (current dev site).

| Field | Value |
|-------|--------|
| Email | `test@ripl.dev` |
| OTP | `123456` |

Override via site config (optional):

```json
"ripl_dev_test_email": "test@ripl.dev",
"ripl_dev_test_otp": "123456"
```

**Behavior:**

- `verify_otp` with test email + OTP works **without** calling `send_otp` first.
- `send_otp` for test email always uses OTP `123456` and may return `dev_test_otp` in the response.

**Production builds:** do not pre-fill or hardcode these credentials.

---

## Public APIs (no token)

These use `@frappe.whitelist(allow_guest=True)`. **No** `Authorization` header required.

### Auth (login only)

| Method | Endpoint | Params |
|--------|----------|--------|
| POST | `ripl.api.auth.send_otp` | `identifier` |
| POST | `ripl.api.auth.verify_otp` | `identifier`, `otp` |
| POST | `ripl.api.login.send_otp` | `identifier` (alias) |
| POST | `ripl.api.login.verify_otp` | `identifier`, `otp` (alias) |

### Circulars

| Method | Endpoint | Params | Notes |
|--------|----------|--------|-------|
| GET/POST | `ripl.api.circular.get_circulars` | — | Returns `{ status, data: [...] }` |
| GET/POST | `ripl.api.circular.get_circular_detail` | `name` | Circular id |
| GET/POST | `ripl.api.circular.get_filtered_circulars` | `category?`, `regulator?`, `search?` | Filters |
| GET/POST | `ripl.api.circular.get_latest_circulars` | `limit?` (default 5) | Latest list |

### Plans

| Method | Endpoint | Params | Notes |
|--------|----------|--------|-------|
| GET/POST | `ripl.api.plan.get_plans` | — | Subscription plans list |

---

## Protected APIs (Bearer token required)

These require:

```http
Authorization: Bearer <access_token>
```

Without a valid token, Frappe returns **401 Unauthorized** before the handler runs.

---

### Auth / test

| Method | Endpoint | Params | Returns |
|--------|----------|--------|---------|
| GET/POST | `ripl.api.test.get_profile` | — | `{ message, user }` — use to verify token works |

---

### Posts

| Method | Endpoint | Params | Returns |
|--------|----------|--------|---------|
| GET/POST | `ripl.api.post.get_posts` | `limit?` (default 10), `offset?` (default 0) | Array of posts |
| GET/POST | `ripl.api.post.get_post_detail` | `name` | Post object |
| POST | `ripl.api.post.create_post` | `data` (JSON object or string) | `{ message, name }` |
| POST | `ripl.api.post.delete_post` | `name` | `{ message }` |

**`create_post` `data` shape (example):**

```json
{
  "title": "...",
  "circular_number": "...",
  "date": "2026-05-21",
  "regulator": "...",
  "category": "...",
  "summary": "...",
  "key_points": "...",
  "show_impacted_entities": 1,
  "show_action_steps": 1,
  "impacted_entities": "...",
  "action_steps": "...",
  "circular_pdf": "...",
  "image_url": "..."
}
```

---

### Circulars (admin / AI — protected)

| Method | Endpoint | Params | Notes |
|--------|----------|--------|-------|
| POST | `ripl.api.circular.enqueue_ai_generation` | `name` | Currently returns `{ status: "disabled" }` |
| POST | `ripl.api.circular.generate_ai_data` | `name` | Admin AI pipeline |

---

### Playbooks

All listed below use `@auth_required`. Several also use `@subscription_required` (currently enforces logged-in user only; full subscription check TBD).

| Method | Endpoint | Params | Notes |
|--------|----------|--------|-------|
| POST | `ripl.api.playbook.playbook_purchase` | `playbook_id` | Mark playbook purchased (sandbox) |
| GET/POST | `ripl.api.playbook.get_playbooks` | — | Catalog + purchase/progress flags |
| GET/POST | `ripl.api.playbook.get_playbook_detail` | `playbook_id` | Outline / metadata |
| GET/POST | `ripl.api.playbook.get_playbook_content` | `playbook_id` | Modules + chapters (**requires purchase**) |
| GET/POST | `ripl.api.playbook.get_chapter` | `chapter_id` | Chapter content |
| POST | `ripl.api.playbook.mark_chapter_progress` | `chapter_id`, `status` | Progress update |
| GET/POST | `ripl.api.playbook.get_quiz` | `module_id` | Quiz + questions |
| POST | `ripl.api.playbook.submit_answer` | `question_id`, `selected_option_id` | Instant feedback |
| POST | `ripl.api.playbook.submit_quiz` | `quiz_id`, `answers` | `answers` = JSON string of array |

**`submit_quiz` `answers` format:**

```json
[
  { "question_id": "Q-001", "option_id": "OPT-001" },
  { "question_id": "Q-002", "option_id": "OPT-003" }
]
```

Pass as a **stringified JSON** in the request body (Frappe form field).

**`get_playbook_content`:** throws if playbook not purchased — call `playbook_purchase` first in sandbox.

---

## Error handling

### HTTP status codes

| Code | Meaning |
|------|---------|
| 200 | Success (check `message` payload) |
| 401 | Missing/invalid/expired Bearer token |
| 403 | Permission denied (logged in but no access) |
| 500 | Server error |

### Frappe error body (example)

```json
{
  "exc_type": "AuthenticationError",
  "exception": "...",
  "_server_messages": "[\"...\"]"
}
```

Parse `_server_messages` or `exception` for user-facing text; do not show raw tracebacks.

### Recommended client behavior

```ts
if (res.status === 401) {
  clearAuthStorage();
  redirectToLogin();
}
```

---

## Frontend implementation checklist

- [ ] **Screen 1:** identifier input → `send_otp`
- [ ] **Screen 2:** 6-digit OTP → `verify_otp`
- [ ] Store `access_token` from `response.message`
- [ ] API client adds `Authorization: Bearer ...` on protected routes
- [ ] Dev build: optional pre-fill `test@ripl.dev` / `123456`
- [ ] Production: no hardcoded credentials
- [ ] Logout clears tokens
- [ ] 401 → login redirect
- [ ] Parse all success payloads from `message`
- [ ] CORS: configure if frontend origin ≠ API origin

---

## Code examples

### API client (fetch)

```ts
const BASE_URL = "http://192.168.0.x:8000"; // your bench URL

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

export async function apiCall<T>(
  method: string,
  params: Record<string, string | number> = {}
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const url = new URL(`${BASE_URL}/api/method/${method}`);
  if (method.startsWith("get_") || method.includes(".get_")) {
    Object.entries(params).forEach(([k, v]) =>
      url.searchParams.set(k, String(v))
    );
    const res = await fetch(url.toString(), { headers });
    const json = await res.json();
    if (!res.ok) throw json;
    return json.message as T;
  }

  const res = await fetch(url.toString(), {
    method: "POST",
    headers,
    body: JSON.stringify(params),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json.message as T;
}
```

### Login

```ts
export async function sendOtp(identifier: string) {
  const res = await fetch(`${BASE_URL}/api/method/ripl.api.auth.send_otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier }),
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json.message;
}

export async function verifyOtp(identifier: string, otp: string) {
  const res = await fetch(`${BASE_URL}/api/method/ripl.api.auth.verify_otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ identifier, otp }),
  });
  const json = await res.json();
  if (!res.ok) throw json;

  const { access_token, refresh_token, user } = json.message;
  localStorage.setItem("access_token", access_token);
  localStorage.setItem("refresh_token", refresh_token);
  localStorage.setItem("user", user);
  return json.message;
}
```

### Fetch posts (authenticated)

```ts
export async function getPosts(limit = 20, offset = 0) {
  const token = getAccessToken();
  const url = `${BASE_URL}/api/method/ripl.api.post.get_posts?limit=${limit}&offset=${offset}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const json = await res.json();
  if (!res.ok) throw json;
  return json.message; // array of posts
}
```

### Dev quick login

```ts
await verifyOtp("test@ripl.dev", "123456");
```

---

## Quick reference — token required?

| Module | Guest OK | Token required |
|--------|----------|----------------|
| `ripl.api.auth` (send/verify OTP) | ✅ login only | ❌ |
| `ripl.api.login` | ✅ login only | ❌ |
| `ripl.api.circular` (read/list) | ✅ | ❌ |
| `ripl.api.circular` (AI admin) | ❌ | ✅ |
| `ripl.api.plan` | ✅ | ❌ |
| `ripl.api.post` | ❌ | ✅ |
| `ripl.api.playbook` | ❌ | ✅ |
| `ripl.api.test` | ❌ | ✅ |

---

## Support & debugging

| Issue | Check |
|-------|--------|
| 401 on protected API | Token sent? `Bearer ` prefix? Token expired? |
| Login OK but 401 after | Reading `json.message`? Storing `access_token`? |
| OTP never arrives | SMS/email not integrated; use dev credentials or backend logs |
| CORS error | Frappe/site CORS for your frontend origin |

**Verify token works:**

```bash
curl "${BASE_URL}/api/method/ripl.api.test.get_profile" \
  -H "Authorization: Bearer <access_token>"
```

---

*Last updated: May 2026 — backend app `ripl`, Frappe bench.*
