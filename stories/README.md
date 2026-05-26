# RIPL Stories

Project stories and reference docs for future work. Each file captures decisions, integration guides, and context that should outlive a single chat or PR.

## Index

| Story | Description | Status |
|-------|-------------|--------|
| [login-authentication-kt.md](./login-authentication-kt.md) | **Client KT** — login/auth workflow, diagrams, tables, medium technical language | Active |
| [frontend-fix-get-quiz-prompt.md](./frontend-fix-get-quiz-prompt.md) | **Fix** — `get_quiz` must not send `module_id=undefined` | Active |
| [frontend-api-request-contract-prompt.md](./frontend-api-request-contract-prompt.md) | **API request contract** — one payload format; playbook purchase; no per-API decorators | Active |
| [frontend-implementation-prompt.md](./frontend-implementation-prompt.md) | Copy-paste implementation prompt for login + APIs | Active |
| [frontend-auth-integration.md](./frontend-auth-integration.md) | OTP login, JWT Bearer auth, public vs protected APIs, frontend integration | Active |

## Adding a story

1. Create `stories/<short-name>.md`
2. Add YAML frontmatter (`title`, `type`, `status`, `created`, `tags`, `related_code`)
3. Link it in this README
