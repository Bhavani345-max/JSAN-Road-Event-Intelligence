# 0046 — Accounts created by administrators; no self-registration

**Status:** 28 October 2026. Code local, tested, for the user to push. No
migration (decisions 0044 and 0045 already added every column). No Railway
setting needed.

## Context

The user's brief (28 October 2026, pasted): the company's DNS records for an
email service are not set up, so turn off self-registration and its email
verification; administrators create accounts by hand (name, official email, Admin
or User), activate and deactivate them, change roles and reset passwords; keep
Forgot password, recovery codes and every existing security control; nothing may
depend on Resend; no production data touched.

## Decision

### Registration: off, not deleted

- New setting `REGISTRATION_ENABLED`, **false by default**. While false:
  `POST /api/auth/register` and `POST /api/auth/verify-email` answer **404**
  ("Registration is closed: accounts are created by your REI administrator."),
  whatever else is configured; `GET /api/auth/options` says
  `registration_open: false`; the sign-in page has **no Register link** and says
  "Accounts are created by your REI administrator."
- The registration code of decision 0045 stays, switched off, so it can be opened
  again once email works (`REGISTRATION_ENABLED=true` plus the email settings).
  Its tests run with the setting on.
- No account, record or table is removed.

### Administrators create accounts (User management, `/users`)

- **Add a user**: full name, official email, role **User** (view-only) or
  **Admin** (full access), then the administrator's own password to confirm.
  `POST /api/admin/users` (administrators only, allowed origin). The account is
  active at once with a **random temporary password, shown once** (`no-store`),
  stored only as a hash; at the first sign-in the person must choose their own
  (decision 0044's forced change). Recorded: `account_created`,
  `temporary_password_set`.
- **No duplicates**: an email already used, in any case or with spaces, is
  refused (409 "An account with this email already exists."); the database's
  unique index refuses one created at the same moment too.
- **Change role**: `POST /api/admin/users/{id}/role` (Admin ⇄ User, own password
  to confirm); never one's own role, never the last active administrator's;
  applies to the account's next request. Recorded: `role_changed`.
- **Deactivate / Activate** (the existing suspend/reactivate): signed out at
  once, refused everything until activated; never oneself, never the last active
  administrator. The page and messages say "deactivated".
- **Reset password**: another active account's, **another administrator's too**
  (there can be several now; an administrator already has every right, so this
  grants nothing new). Never one's own (Password tab or a recovery code).
- History, as before.
- Only the Admin and User roles can be given (`reviewer` stays in code, unused).

### Forgot password (kept)

The "Forgot password?" link and panel stay. Without email (today): "Contact your
REI administrator (reset links by email are not set up): they set a temporary
password, and you choose your own when you sign in." Administrators can also use
a recovery code; with none left, another administrator or a developer
(docs/operations/emergency-account-recovery.md). "Email me a reset link" appears
only when email is configured, and is never shown as working otherwise
(`POST /api/auth/forgot` answers 503 then).

### Unchanged

Sign-in, sessions and cookies, sign-out, the lock at 5 failed attempts, password
hashing, roles and every authorization check, recovery codes, the emergency
procedure, the ended-session handling.

## Tests

`backend/tests/api/test_user_management.py` (19, three safeguards removed one at
a time were caught), the registration tests with `REGISTRATION_ENABLED` on,
`test_accounts.py` (no public registration); frontend `users.test.ts`. Headless
Chrome against a throwaway API with **no email settings**: no Register link,
Forgot password panel, a User and an Admin created, a duplicate refused, role
changed both ways, the new User's forced password change, a User refused by the
admin API and page, a reset password replacing the old one, deactivation, an
existing account signing in and out, a phone width. It found a form nested in a
form in "Add a user", which made it fail: fixed.
