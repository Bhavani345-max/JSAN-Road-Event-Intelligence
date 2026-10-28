# Emergency account recovery (decision 0044)

For the one case the console cannot handle: **the only administrator has forgotten
the password and has no recovery code left.** Every other case is handled in REI:

| Who forgot | What to do |
| --- | --- |
| A view-only account | The administrator: **Users** (User management) → Reset password. The account gets a temporary password and chooses its own at the next sign-in. Once email is set up (decision 0045), "Email me a reset link" on the sign-in page also works for accounts with a confirmed email. |
| The administrator, with a recovery code | Sign-in page → Forgot password? → "use one of your recovery codes". |
| The administrator, no code left | Another administrator: **Users** → Reset password (decision 0046). If there is none: this procedure. |

## Who may run it

Only a person with access to the REI project on Railway (the project owner or a
developer they name). It changes a password directly in the production database,
so it is never run on someone's say-so alone: confirm with the account holder in
person or by phone first.

## Steps

1. Open a shell **inside the API service** on Railway (the database is reachable
   only on Railway's private network):

   ```sh
   railway login
   railway ssh --service JSAN-Road-Event-Intelligence --environment production
   ```

   (`railway ssh` needs an SSH key added to the Railway account first.)

2. In that shell, from `/srv`:

   ```sh
   python backend/cli/reset_password.py admin@your-domain
   ```

   It shows the database and the account, asks you to type `RESET`, then prints a
   **temporary password once**. It:

   - sets that temporary password (stored hashed, as every password),
   - signs the account out everywhere,
   - **cancels all its recovery codes** (lost codes must not work if found),
   - records `temporary_password_set_on_server` and `recovery_codes_revoked` in
     `security_events` (who, when; never the password).

3. Give the temporary password to the account holder **in person or by phone**,
   never by email or chat. Close the shell.

4. The account holder signs in with it, must choose a new password at once, and
   then creates new recovery codes (Profile and settings → Security).

If the account was locked after failed attempts, the lock ends 30 minutes after it
began, or at once when the API restarts.

## Never

- Never put a password in a Railway variable to reset an account: the variables
  are exactly what the 22 October 2026 Railway incident exposed.
- Never print, log, email or store the temporary password anywhere else.
- Never open the database to the internet (PostGIS public TCP proxy) for this.

## Checking what happened

The `security_events` table records every credential change (kind, account id,
acting account id or none for the server, time). Read it with a read-only
connection, for example inside the same shell:

```sh
python - <<'PY'
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import create_db_engine, create_session_factory
from app.models import SecurityEvent
with create_session_factory(create_db_engine(get_settings().database_url))() as s:
    for e in s.scalars(select(SecurityEvent).order_by(SecurityEvent.occurred_at.desc()).limit(20)):
        print(e.occurred_at, e.kind, e.account_id, e.actor_id or "server", e.detail or "")
PY
```
