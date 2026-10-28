# 0044 — Sign-in limit, admin password reset and recovery codes

**Status:** 28 October 2026. Code local, tested, for the user to push. Migration
0009 (additive). No Railway setting.

## Context

The user asked (28 October 2026) what happens on "Forgot password?" and for a
stricter sign-in limit. The answer: the button only said "ask your
administrator", but there was no way to reset a password in REI; only a server
script could, and a forgotten administrator password had no way back. The account
emails are not real mailboxes, so a reset link by email cannot work (and would be
unsafe on a domain REI does not control). The user chose (asked directly):

- **Sign-in limit:** warn from the 3rd failed attempt, lock the account for
  **30 minutes at the 5th**.
- **Forgot password:** the administrator resets the User's password; the
  administrator keeps single-use recovery codes; with twelve written requirements
  (temporary password changed at next sign-in, codes hashed and single-use, rate
  limits, generic errors, sessions ended, audit without secrets, an emergency
  procedure, tests, nothing weakened).

## Decision

### Sign-in limit (replaces decision 0032's 8 in 15 minutes)

- Failures per account (the email typed, existing or not) within **30 minutes**.
  Attempts 1–2: "The email or password is incorrect."; 3–4: the same with
  "2 attempts left / 1 attempt left before this account is locked for 30
  minutes."; the **5th** answers 429 and locks the account for **30 minutes from
  that moment**, even for the right password ("try again in N minutes").
- Wrong current passwords (profile, password, admin actions) and wrong recovery
  codes count towards the same limit. A success clears it; an administrator's
  reset clears the User's.
- Still per account only, in the API's memory (one replica): a restart forgets it.
  A made-up email gets exactly the answers of a real one. A lock of an existing
  account is recorded (`sign_in_locked`).

### Admin resets the User's password

- `POST /api/auth/accounts/{id}/temporary-password` (administrator only, own
  password to confirm). The list of accounts and the button moved to User
  management in decision 0045 (`GET /api/admin/users`). Never the administrator's own or
  another administrator's account.
- The server makes a **random temporary password** (16 characters from 31 that
  cannot be confused, about 79 bits), returns it **once** (`Cache-Control:
  no-store`), stores only its hash (PBKDF2, as every password). The current
  password is never shown or retrievable.
- The account's sessions all end; `users.must_change_password` is set. Until it
  chooses its own password, the API refuses that account everything (403) except
  `/auth/me`, `/auth/password` and `/auth/logout`, and the console shows only
  "Choose your own password".

### Administrator recovery codes

- `GET/POST /api/auth/recovery-codes` (administrator only; creating needs the own
  password): **10 single-use codes**, same form as temporary passwords, shown once
  with Copy and Download; creating new ones cancels the old. Only **SHA-256
  digests** are stored, as for session cookies; each code is high-entropy random,
  so a fast digest is safe, and lookups need no per-code key.
- `POST /api/auth/recover` (open, like sign-in): email + code + new password. The
  code is used up in the same statement that checks it (`UPDATE … WHERE used_at
  IS NULL`), so it cannot be used twice, even by two requests at once. A new
  password the policy refuses is refused **before** the code is checked (no code
  wasted). Every wrong email, wrong, used, malformed or other account's code gets
  "The email or recovery code is not valid." All sessions end; the account signs
  in again.
- The view-only User has no codes: the administrator resets theirs.

### Emergency procedure

`backend/cli/reset_password.py`, run inside the API service on Railway by someone
with project access (docs/operations/emergency-account-recovery.md): temporary
password printed once, sessions ended, **all recovery codes cancelled**,
recorded. Never through a Railway variable.

### Audit

`security_events` (kind, account id, acting account id or none for the server,
time, short detail): password and email changes, temporary passwords, codes
created, revoked and used, locks. Never a password, temporary password or code;
log lines carry ids only (tested).

### Console

- Sign-in page: the attempt warnings and lock time from the API; "Forgot
  password?" explains both cases and opens the recovery-code form (below desktop
  width only the card shows, so it fits phones down to 360 × 640).
- Profile and settings → **Security** (administrators): recovery codes (status,
  create, shown once); other accounts' temporary passwords in User management
  (decision 0045).

### Database (migration 0009)

`users.must_change_password` (NOT NULL, default false: every existing account
unchanged), tables `recovery_codes` (unique digest, FK to the account, cascade)
and `security_events`. Nothing removed or rewritten.

## Tests

`backend/tests/api/test_account_recovery.py` (26; six safeguards removed one at a
time were each caught), the updated limit tests in `test_auth.py`,
`test_accounts.py`, `test_security.py`, `test_own_profile.py`,
`tests/integration/test_migrations.py`; frontend `profile.test.ts`,
`permissions.test.ts`. Headless Chrome against a throwaway API: warnings and
lock, forgot note, codes created and shown once, the User's reset and forced new
password, recovery with a code, a used code refused, six screen sizes.

## Not done

Email reset links and registration (the user's next brief) need a real email
service; they come with decision 0045.
