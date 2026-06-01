# Staging OTP runbook (QA)

Use this on **staging only**. Never set these flags on production.

## 1. Enable staging site config

On the staging server:

```bash
cd /home/frappe/frappe-bench

bench --site ripl.local set-config ripl_staging_auth 1
bench --site ripl.local set-config ripl_expose_otp_in_response 1
bench --site ripl.local set-config ripl_log_otp_to_error_log 1

# Optional fixed test account (defaults: test@ripl.dev / 123456)
bench --site ripl.local set-config ripl_dev_test_email "test@ripl.dev"
bench --site ripl.local set-config ripl_dev_test_otp "123456"

bench --site ripl.local clear-cache
bench restart
```

Production safety (required on prod):

```bash
bench --site <prod-site> set-config ripl_production 1
```

When `ripl_production` is `1`, OTP is never returned in API responses and never written to Error Log.

## 2. Send OTP

```bash
curl -sS -X POST "http://168.144.157.100/api/method/ripl.api.auth.send_otp" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"qa@example.com"}'
```

Read `message.dev_test_otp` from the JSON response when `ripl_expose_otp_in_response` is enabled.

## 3. Read OTP (pick one)

| Method | Where |
|--------|--------|
| API response | `response.message.dev_test_otp` |
| Frappe Desk | **Error Log** → search title `RIPL OTP` |
| Fixed test user | `test@ripl.dev` + OTP `123456` (when staging auth is on) |

## 4. Verify OTP

```bash
curl -sS -X POST "http://168.144.157.100/api/method/ripl.api.auth.verify_otp" \
  -H "Content-Type: application/json" \
  -d '{"identifier":"qa@example.com","otp":"XXXXXX"}'
```

Use the same identifier casing/format as send (emails are normalized to lowercase).

## 5. Rate limits (QA)

- **30 seconds** cooldown between sends per identifier
- **3 sends per hour** per identifier

Wait between retries or use a fresh email for each test run.

## 6. Redis / cache check

If verify always returns **Invalid OTP** after a successful send:

- Confirm staging workers share one Redis/cache backend
- Run `bench doctor` on the server
- Retry after `bench restart`
