# 0045 — Registration, administrator approval and email reset links

**Status:** 28 October 2026. Code local, tested, for the user to push. Migration
0010 (additive). **Self-registration switched off by decision 0046**
(`REGISTRATION_ENABLED`, false by default): administrators create accounts.
Reset links stay available only once an email service is set up.

## Context

The user's brief (28 October 2026, pasted): employees register with a company
email; the email is proved by a single-use link; an administrator approves or
rejects; administrators suspend and reactivate accounts and see their history;
"Forgot password?" emails a reset link; everything enforced on the server,
rate-limited, audited, without revealing which emails have accounts; nothing
pretends an email was sent when none can be.

What REI had: two seeded accounts (decision 0032, no registration), cookie
sessions, roles admin/user, the sign-in limit and recovery codes of decision
0044, no email service at all. The accounts' emails are not real mailboxes.

## Decision

### Account status (migration 0010)

`users.status`: `active` (every existing and seeded account, by the column
default: nobody downgraded or signed out), `pending_approval`, `rejected`,
`suspended`; `email_verified_at`, `registered_at`, `decided_at`, `decided_by`.
On PostgreSQL a CHECK constraint holds the four values. **Only `active` reaches
anything**: `user_for_token` refuses every other status, so a session of an
account that is suspended (or changed in the database) gets 401 on every
protected route. Sign-in with the right password but another status gets 403
with the reason (confirm your email / waiting / not approved / suspended), said
only to someone who knew the password; no session is created.

The migration adds columns in place. A first version rebuilt the users table on
SQLite, which with foreign keys on deletes every session, recovery code and link
of every account: `tests/integration/test_migrations.py` caught it, and now
checks that accounts and sessions survive the upgrade and the downgrade.

### Registration

- `POST /api/auth/register` (full name, company email, password). **No role in
  the request**: every registration is a `user` (view-only); any extra field
  (`role`, `status`) is ignored.
- Open only when email is configured **and** `ALLOWED_EMAIL_DOMAINS` lists the
  company domains (never guessed); otherwise 503 with the reason, and the page
  says registration is not open yet. `GET /api/auth/options` tells the page.
- Checked on both sides: name, email form, exact company domain (no
  subdomains), password at least 8 characters, not one of the most common
  passwords, at least 4 different characters, not containing the email's name;
  the confirmation in the form.
- The same answer whether or not the email has an account. A registration that
  has not proved its email and registers again gets a new link (the old one stops
  working; its password stays the first one); any other existing account gets
  nothing. The password is hashed in every case, so every answer costs the same;
  emails are sent after the answer.
- Limits: 3 registrations per email per hour, 30 in all per hour.

### Email verification

A 256-bit random token in a link to `/verify-email?token=…`, valid 24 hours
(`EMAIL_VERIFICATION_MINUTES`). Only its SHA-256 digest is stored
(`email_tokens`), used up in the statement that checks it (cannot be used twice),
and a new one ends the earlier. The page confirms with a **button**, not on
opening, so mail scanners that open links cannot use it up. Wrong or expired
links: 60 in all per 10 minutes, then 429.

### Approval (User management)

`/users` in the console (header **Users** button for administrators, with the
number of confirmed registrations waiting). API `/api/admin/users`: list,
`approve`, `reject`, `suspend`, `reactivate`, `history`. Every route requires an
active administrator (`require_account_admin`) and an allowed origin.

- Approve: only a registration that **proved its email**; it becomes `active`
  with the `user` role; who and when are kept; an email tells the person.
- Reject: a waiting registration; never signs in; its links end; an email tells
  the person only if the address was proved.
- Suspend: another active account (never your own, never the last active
  administrator); all its sessions and links end at once.
- Reactivate: a suspended account.
- History: the account's `security_events`, with who acted.
- The temporary password of decision 0044 moved here (Reset password).

### Reset links (forgot password)

`POST /api/auth/forgot` (email): the same answer for every address; a link only
for an **active account with a proved email** (so not for a waiting
registration, and not for the seeded accounts until they prove one); valid 30
minutes (`PASSWORD_RESET_MINUTES`); a new one ends the earlier. `POST
/api/auth/reset-password` (token, new password): the password checked **before**
the link is used; all sessions end; the sign-in lock is lifted; an email notice
says the password changed. Limits: 3 requests per email per 30 minutes, 60 in
all per hour; wrong links as above. **Without email**, both answer 503 and the
sign-in page offers recovery codes and the administrator's reset instead
(decision 0044, the documented admin-assisted procedure).

### Email service

`app/services/email_service.py`: a provider abstraction with one provider,
**Resend** (an HTTP API; Railway may block outgoing SMTP). Settings:

| Variable | Example | |
| --- | --- | --- |
| `EMAIL_PROVIDER` | `resend` | anything else: no email |
| `EMAIL_FROM` | `JSAN REI <rei@mail.your-domain>` | a domain verified at the provider |
| `EMAIL_API_KEY` | `re_…` | secret: Railway variables only |
| `APP_BASE_URL` | `https://jsan-rei.up.railway.app` | for the links |
| `ALLOWED_EMAIL_DOMAINS` | `your-company-domain` | empty: registration closed |

Without all of the first four there is **no sender**; nothing is ever reported
as sent. Messages and failures are logged by kind only, never with an address's
link, token or the key. `backend/cli/send_test_email.py you@domain` says what is
missing or sends one test message: **delivery is not claimed until a test
message has actually arrived.**

### Audit

New `security_events` kinds: registered, email_verified, account_approved,
account_rejected, account_suspended, account_reactivated,
password_reset_requested, password_reset_with_link (decision 0044's remain).

## Tests

`backend/tests/api/test_registration.py` (36; six safeguards removed one at a
time were caught, a seventh has a second layer, both removed caught),
`tests/api/test_accounts.py` (closed without email, no other route creates an
account), `tests/integration/test_migrations.py` (accounts and sessions survive
up and down); frontend `accountApi.test.ts` (the common-password list matches
the API's), `users.test.ts`. Headless Chrome against a throwaway API whose emails
went to a file: register, refused domain, confirm by link, waiting messages,
header badge, approve with confirmation, history, the member signs in
view-only, email reset link, password-changed notice, suspend, phones 360/390.

## To switch it on (each step needs the user's approval)

1. Create a Resend account, verify a sending domain the company owns (DNS
   records), create an API key.
2. Locally: put the five variables in `.env`, run
   `python backend/cli/send_test_email.py you@company-domain`, and check the
   message **arrives**.
3. Railway, API service: set the same variables (`APP_BASE_URL` = the console's
   address). Redeploy; the sign-in page then shows Register and "Email me a reset
   link".
4. Existing accounts keep signing in as before. To use reset links they need a
   real, proved address; until then: recovery codes and the administrator's reset.
