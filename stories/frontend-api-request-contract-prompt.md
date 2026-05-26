---
title: Frontend API Request Contract (All Protected APIs)
type: story
status: active
created: 2026-05-22
audience: frontend
tags: [api, contract, playbook, auth]
---

# Frontend Prompt — API Request Contract (Including Playbook Purchase)

**Purpose:** One request format for all RIPL APIs so the backend uses a **single auth decorator** — no per-API decorator changes.

---

## Senior backend note (for your team)

**You are correct.**

| Approach | Verdict |
|----------|---------|
| Customize decorator per API | ❌ Avoid — hard to maintain, easy to break |
| One decorator + standard frontend payload | ✅ **Recommended** |
| Different payload shape per screen | ❌ Avoid — causes 500s like `missing playbook_id` |

A senior engineer would:

1. Keep **one** `auth_required` decorator (authentication only).
2. Publish a **fixed request contract** (this document).
3. Let the **frontend** follow that contract consistently.
4. Use **auth_hook** (JWT) at the framework layer — already in place.

The backend should not need to know whether the call is “purchase” vs “post detail” inside the decorator. It should only validate the token and pass request parameters through.

---

## The contract (frontend must follow)

### Rule 1 — Authentication header (protected APIs)

```http
Authorization: Bearer <access_token>
```

### Rule 2 — Parameter names match backend exactly

Use the Python argument name from the API table — **not** aliases.

| API | Required param | Name to send |
|-----|----------------|--------------|
| Post detail | Post id | `name` |
| Playbook detail | Playbook id | `playbook_id` |
| Playbook purchase | Playbook id | `playbook_id` |

❌ Do not send `{ "id": "..." }` for playbooks.  
✅ Send `{ "playbook_id": "..." }`.

### Rule 3 — Where to put parameters

| HTTP method | Put parameters here | Content-Type |
|-------------|---------------------|--------------|
| **GET** | Query string | — |
| **POST** | **Top-level JSON body** | `application/json` |

**Do not** wrap purchase/post params inside:

```json
{ "data": { "playbook_id": "..." } }
```

unless you also send top-level fields (not recommended).

### Rule 4 — Read responses from `message`

```ts
const json = await res.json();
const data = json.message;
```

---

## Playbook purchase — exact implementation

### Endpoint

```
POST {BASE_URL}/api/method/ripl.api.playbook.playbook_purchase
```

### Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Body (required shape)

```json
{
  "playbook_id": "m2eq01lh6n"
}
```

### Success (`message`)

```json
{
  "playbook_id": "m2eq01lh6n",
  "is_purchased": true
}
```

### Example (fetch)

```ts
async function purchasePlaybook(playbookId: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(
    `${BASE_URL}/api/method/ripl.api.playbook.playbook_purchase`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ playbook_id: playbookId }),
    }
  );
  const json = await res.json();
  if (!res.ok) throw json;
  return json.message;
}
```

### Example (axios)

```ts
const { data } = await axios.post(
  "/api/method/ripl.api.playbook.playbook_purchase",
  { playbook_id: playbookId },
  { headers: { Authorization: `Bearer ${token}` } }
);
return data.message;
```

### Common mistakes (causes 500 / missing argument)

| Mistake | Result |
|---------|--------|
| Body `{}` or missing `playbook_id` | `missing playbook_id` |
| `{ "id": "..." }` instead of `playbook_id` | `missing playbook_id` |
| `playbook_id` only in query on POST, empty body | `missing playbook_id` |
| No `Authorization` header | 401 |
| Token expired | 401 → login |

---

## Same pattern — other playbook APIs

```ts
// GET detail — query string
GET .../ripl.api.playbook.get_playbook_detail?playbook_id=m2eq01lh6n

// GET content
GET .../ripl.api.playbook.get_playbook_content?playbook_id=m2eq01lh6n

// POST purchase — JSON body
POST .../ripl.api.playbook.playbook_purchase
Body: { "playbook_id": "m2eq01lh6n" }
```

---

## Shared helper (recommended)

Use **one** client for all APIs — only `method` and `params` change:

```ts
type Params = Record<string, string | number | undefined>;

export async function riplApi<T>(
  method: string,
  params: Params = {},
  httpMethod?: "GET" | "POST"
): Promise<T> {
  const token = localStorage.getItem("access_token");
  if (!token) throw new Error("Not authenticated");

  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };

  const verb =
    httpMethod ?? (method.includes(".get_") ? "GET" : "POST");
  let url = `${BASE_URL}/api/method/${method}`;

  if (verb === "GET") {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v != null) qs.set(k, String(v));
    });
    if (qs.toString()) url += `?${qs.toString()}`;
    const res = await fetch(url, { headers });
    const json = await res.json();
    if (res.status === 401) throw new AuthError();
    if (!res.ok) throw json;
    return json.message;
  }

  headers["Content-Type"] = "application/json";
  const res = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(params),
  });
  const json = await res.json();
  if (res.status === 401) throw new AuthError();
  if (!res.ok) throw json;
  return json.message;
}

// Usage
await riplApi("ripl.api.playbook.playbook_purchase", {
  playbook_id: id,
}, "POST");
```

---

## Checklist before calling purchase

- [ ] User logged in; `access_token` present
- [ ] POST (not GET) for `playbook_purchase`
- [ ] Body is `{ "playbook_id": "<id>" }` at root
- [ ] Header `Content-Type: application/json`
- [ ] Header `Authorization: Bearer ...`
- [ ] Read `response.message` for result

---

## Backend commitment

We will **not** add purchase-specific decorator logic.  
If the frontend follows this contract, the same `@auth_required` decorator works for posts, playbooks, and all other protected APIs.

---

**Related:** [frontend-implementation-prompt.md](./frontend-implementation-prompt.md)
