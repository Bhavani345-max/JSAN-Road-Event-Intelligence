"""Local password authentication and opaque, revocable server sessions."""

import base64
import hashlib
import hmac
import logging
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import AuthSession, RecoveryCode, SecurityEvent, User
from packages.common.time import utc_now

logger = logging.getLogger(__name__)

PASSWORD_ROUNDS = 600_000
# Lowered from 12 at the user's request on 15 October 2026 (decision 0032).
MIN_PASSWORD_LENGTH = 8


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Passwords must contain at least {MIN_PASSWORD_LENGTH} characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ROUNDS,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(digest).decode("ascii").rstrip("="),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, rounds, salt_text, digest_text = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text + "=" * (-len(salt_text) % 4))
        expected = base64.urlsafe_b64decode(digest_text + "=" * (-len(digest_text) % 4))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


# The two kinds of account REI has (decision 0032): the admin manages REI and
# reviews; a user signs in to view the console and changes nothing.
ADMIN_ROLE = "admin"
USER_ROLE = "user"
# The roles an administrator gives (decision 0046): Admin (everything) or User (view-only).
ASSIGNABLE_ROLES = (ADMIN_ROLE, USER_ROLE)

# Account status (decision 0045): only an active account signs in and reaches REI.
ACTIVE = "active"
PENDING_APPROVAL = "pending_approval"
REJECTED = "rejected"
SUSPENDED = "suspended"


def status_problem(user: User) -> str | None:
    """Why an account with the right password still may not sign in, or None.
    Said only to someone who gave the account's password."""
    if user.status == ACTIVE:
        return None
    if user.status == PENDING_APPROVAL and user.email_verified_at is None:
        return "Confirm your email first: open the link we sent to it. An administrator then reviews your registration."
    if user.status == PENDING_APPROVAL:
        return "Your registration is waiting for an administrator's approval. You will get an email when it is decided."
    if user.status == REJECTED:
        return "This registration was not approved. Contact your REI administrator if you think this is a mistake."
    return "This account is deactivated. Contact your REI administrator."


def seed_admin_user(session: Session, email: str, password: str) -> tuple[User, bool]:
    """Create the bootstrap admin once; never reset an existing user's password."""
    return seed_account(session, email, password, role=ADMIN_ROLE)


def seed_account(session: Session, email: str, password: str, *, role: str) -> tuple[User, bool]:
    """Create the one account of `role` once, from configured values.

    Nothing is ever changed here: an account with this email is returned
    untouched, whatever the configuration says. REI has one account per role
    (decision 0032), so when another account already has the role, that one is
    returned and none is created: a changed email never adds a third account.
    """
    email = normalize_email(email)
    existing = session.scalar(select(User).where(User.email == email))
    if existing:
        return existing, False
    holder = session.scalar(select(User).where(User.role == role).order_by(User.created_at))
    if holder:
        return holder, False
    local_name = email.partition("@")[0].replace(".", " ").replace("_", " ").replace("-", " ")
    display_name = " ".join(part.capitalize() for part in local_name.split()) or "REI Admin"
    now = utc_now()
    user = User(
        user_id=str(uuid.uuid4()),
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()
    return user, True


_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True)
class EmailChange:
    user_id: str
    old_email: str
    new_email: str
    sessions_ended: int


def change_account_email(
    session: Session, old_email: str, new_email: str, *, role: str | None = None, end_sessions: bool = True
) -> EmailChange:
    """Give an existing account a new sign-in email; nothing else about it changes.

    The account keeps its id, password, role, status and creation time, and
    history that recorded the old email is left as it was. Its open sessions are
    ended unless `end_sessions` is False, so it signs in again with the new email.
    Raises ValueError, changing nothing, when no account has the old email, that
    account does not have `role` (when given), or the new email is taken or not
    an email. The caller commits.
    """
    old, new = normalize_email(old_email), normalize_email(new_email)
    if len(new) > 320 or not _EMAIL.fullmatch(new):
        raise ValueError(f"Not an email address: {new_email!r}")
    if new == old:
        raise ValueError("The new email is the account's current email.")
    user = session.scalar(select(User).where(User.email == old).with_for_update())
    if user is None:
        raise ValueError(f"No account has the email {old}.")
    if role is not None and user.role != role:
        raise ValueError(f"{old} is a {user.role!r} account, not {role!r}.")
    if session.scalar(select(User.user_id).where(func.lower(func.trim(User.email)) == new)):
        raise ValueError(f"{new} is already used by another account.")
    user.email = new
    user.updated_at = utc_now()
    ended = 0
    if end_sessions:
        ended = session.execute(delete(AuthSession).where(AuthSession.user_id == user.user_id)).rowcount
    session.flush()
    return EmailChange(user.user_id, old, new, ended)


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    # Spend comparable time for missing emails without revealing account existence.
    if user is None:
        verify_password(password, _DUMMY_PASSWORD_HASH)
        return None
    if not user.is_active or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(session: Session, user: User, lifetime_hours: int) -> str:
    now = utc_now()
    session.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = secrets.token_urlsafe(48)
    session.add(
        AuthSession(
            token_hash=hashlib.sha256(token.encode("ascii")).hexdigest(),
            user_id=user.user_id,
            created_at=now,
            expires_at=now + timedelta(hours=lifetime_hours),
        )
    )
    session.flush()
    return token


def user_for_token(session: Session, token: str | None) -> User | None:
    if not token or len(token) > 200:
        return None
    digest = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
    row = session.scalar(
        select(AuthSession).where(AuthSession.token_hash == digest, AuthSession.expires_at > utc_now())
    )
    if row is None:
        return None
    user = session.get(User, row.user_id)
    # Pending, rejected and suspended accounts reach nothing, whatever cookie they hold.
    return user if user and user.is_active and user.status == ACTIVE else None


def revoke_session(session: Session, token: str | None) -> None:
    if token and len(token) <= 200:
        digest = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
        session.execute(delete(AuthSession).where(AuthSession.token_hash == digest))


def end_other_sessions(session: Session, user: User, token: str | None) -> int:
    """End the account's sessions except the one `token` belongs to (the browser
    making the change stays signed in). Returns how many were ended."""
    keep = hashlib.sha256((token or "").encode("ascii", errors="ignore")).hexdigest()
    return session.execute(
        delete(AuthSession).where(AuthSession.user_id == user.user_id, AuthSession.token_hash != keep)
    ).rowcount


def change_own_profile(
    session: Session, user: User, *, display_name: str | None, email: str | None, token: str | None
) -> None:
    """The account's own new name and/or sign-in email; the caller has checked the
    password for a new email, and commits. A new email ends the account's other
    sessions. Raises ValueError, changing nothing, for an email that is not one
    or is another account's."""
    new_email = normalize_email(email) if email is not None else user.email
    if new_email != user.email:
        old_email = user.email
        change_account_email(session, user.email, new_email, end_sessions=False)
        end_other_sessions(session, user, token)
        record_security_event(session, "email_changed", user, actor=user, detail=f"{old_email} -> {new_email}")
    if display_name is not None and display_name != user.display_name:
        user.display_name = display_name
        user.updated_at = utc_now()
    session.flush()


def change_own_password(session: Session, user: User, new_password: str, token: str | None) -> None:
    """The account's own new password (the caller has checked the current one);
    every other session of the account ends. Raises ValueError for one that is
    too short. The caller commits."""
    user.password_hash = hash_password(new_password)
    # A temporary password, once replaced, has done its job.
    user.must_change_password = False
    user.updated_at = utc_now()
    end_other_sessions(session, user, token)
    record_security_event(session, "password_changed", user, actor=user)
    session.flush()


def user_public(user: User) -> dict[str, str | bool]:
    return {
        "id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "must_change_password": user.must_change_password,
    }


# --- account recovery (decision 0044) -------------------------------------------------

# What security_events.kind may hold (at most 40 characters).
SECURITY_EVENT_KINDS = frozenset({
    "password_changed",
    "email_changed",
    "temporary_password_set",
    "temporary_password_set_on_server",
    "recovery_codes_created",
    "recovery_codes_revoked",
    "recovered_with_code",
    "sign_in_locked",
    # Registration and approval (decision 0045).
    "registered",
    "email_verified",
    "account_approved",
    "account_rejected",
    "account_suspended",
    "account_reactivated",
    "password_reset_requested",
    "password_reset_with_link",
    # Accounts made by administrators (decision 0046).
    "account_created",
    "role_changed",
})  # fmt: skip

# Temporary passwords and recovery codes: 16 characters from 31 that cannot be
# mistaken for one another (no i, l, o, 0, 1), about 79 bits, read in groups of four.
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
CODE_LENGTH = 16
RECOVERY_CODE_COUNT = 10


def record_security_event(
    session: Session, kind: str, account: User | str | None, *, actor: User | None = None, detail: str | None = None
) -> None:
    """Records what happened to an account's credentials. Never pass a password or a code."""
    if kind not in SECURITY_EVENT_KINDS:
        raise ValueError(f"Unknown security event: {kind}")
    account_id = account.user_id if isinstance(account, User) else account
    session.add(
        SecurityEvent(
            event_id=str(uuid.uuid4()),
            occurred_at=utc_now(),
            kind=kind,
            account_id=account_id,
            actor_id=actor.user_id if actor else None,
            detail=detail[:300] if detail else None,
        )
    )
    logger.info("Security event %s: account %s, by %s", kind, account_id, actor.user_id if actor else "the server")


def _random_code() -> str:
    """A new temporary password or recovery code, as xxxx-xxxx-xxxx-xxxx."""
    raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
    return "-".join(raw[i : i + 4] for i in range(0, CODE_LENGTH, 4))


def normalize_recovery_code(code: str) -> str | None:
    """The code as stored (lower case, without spaces or dashes); None if it cannot be one."""
    compact = "".join(code.split()).replace("-", "").lower()
    if len(compact) != CODE_LENGTH or any(character not in CODE_ALPHABET for character in compact):
        return None
    return compact


def _code_digest(normalized_code: str) -> str:
    return hashlib.sha256(normalized_code.encode("ascii")).hexdigest()


def set_temporary_password(session: Session, account: User, *, actor: User | None) -> str:
    """Gives the account a new random temporary password, returned once to be handed
    over; the account must choose its own at its next sign-in. All its sessions end.
    `actor` None: set on the server (the emergency procedure). The caller commits."""
    temporary = _random_code()
    account.password_hash = hash_password(temporary)
    account.must_change_password = True
    account.updated_at = utc_now()
    session.execute(delete(AuthSession).where(AuthSession.user_id == account.user_id))
    kind = "temporary_password_set" if actor else "temporary_password_set_on_server"
    record_security_event(session, kind, account, actor=actor)
    session.flush()
    return temporary


def reset_password_by_admin(session: Session, admin: User, account_id: str) -> tuple[User, str]:
    """An administrator's reset of another active account, another administrator's too
    since there can be several (decision 0046): an administrator already has every
    right, so it grants nothing new. Never their own: they change it under Password,
    or use a recovery code. Raises LookupError for no such account, ValueError for
    one that cannot be reset here."""
    account = session.get(User, account_id)
    if account is None:
        raise LookupError("No such account.")
    if account.status != ACTIVE:
        raise ValueError("Only an active account's password can be reset.")
    if account.user_id == admin.user_id:
        raise ValueError("Your own password is not reset here: change it under Password, or use a recovery code.")
    return account, set_temporary_password(session, account, actor=admin)


@dataclass(frozen=True)
class RecoveryCodeStatus:
    remaining: int
    total: int
    created_at: datetime | None


def recovery_code_status(session: Session, user: User) -> RecoveryCodeStatus:
    codes = session.scalars(select(RecoveryCode).where(RecoveryCode.user_id == user.user_id)).all()
    return RecoveryCodeStatus(
        remaining=sum(code.used_at is None for code in codes),
        total=len(codes),
        created_at=max((code.created_at for code in codes), default=None),
    )


def create_recovery_codes(session: Session, user: User) -> list[str]:
    """A new set of single-use recovery codes, returned once; the account's earlier
    codes stop working. Only their digests are stored. The caller commits."""
    session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.user_id))
    now = utc_now()
    codes = [_random_code() for _ in range(RECOVERY_CODE_COUNT)]
    for code in codes:
        session.add(
            RecoveryCode(
                code_id=str(uuid.uuid4()),
                user_id=user.user_id,
                code_hash=_code_digest(normalize_recovery_code(code)),
                created_at=now,
            )
        )
    record_security_event(
        session, "recovery_codes_created", user, actor=user,
        detail=f"{RECOVERY_CODE_COUNT} codes; earlier codes no longer work",
    )  # fmt: skip
    session.flush()
    return codes


def revoke_recovery_codes(session: Session, user: User) -> int:
    """Ends every recovery code of the account (the emergency procedure). The caller commits."""
    ended = session.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.user_id)).rowcount
    if ended:
        record_security_event(session, "recovery_codes_revoked", user, detail=f"{ended} codes")
    session.flush()
    return ended


def recover_with_code(session: Session, email: str, code: str, new_password: str) -> int | None:
    """Sets a new password with one of the account's recovery codes, which is used up.

    Returns the codes left, or None, changing nothing, when the email, the code or
    the account is not valid (the caller answers alike for all of them). Raises
    ValueError for a new password the policy refuses, before the code is checked,
    so a refused password never uses a code up. Every session of the account ends.
    The caller commits.
    """
    # Hashing first also gives every answer, valid or not, the same cost.
    password_hash = hash_password(new_password)
    normalized = normalize_recovery_code(code)
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or not user.is_active or user.status != ACTIVE or normalized is None:
        return None
    now = utc_now()
    # Used up in the same statement that checks it: two requests with one code
    # cannot both succeed.
    used = session.execute(
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user.user_id,
            RecoveryCode.code_hash == _code_digest(normalized),
            RecoveryCode.used_at.is_(None),
        )
        .values(used_at=now)
    ).rowcount
    if used != 1:
        return None
    user.password_hash = password_hash
    user.must_change_password = False
    user.updated_at = now
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.user_id))
    left = recovery_code_status(session, user).remaining
    record_security_event(session, "recovered_with_code", user, actor=user, detail=f"{left} codes left")
    session.flush()
    return left


_DUMMY_SALT = b"REI login timing salt"
_DUMMY_DIGEST = hashlib.pbkdf2_hmac("sha256", b"unused", _DUMMY_SALT, PASSWORD_ROUNDS)
_DUMMY_PASSWORD_HASH = "pbkdf2_sha256${}${}${}".format(
    PASSWORD_ROUNDS,
    base64.urlsafe_b64encode(_DUMMY_SALT).decode("ascii").rstrip("="),
    base64.urlsafe_b64encode(_DUMMY_DIGEST).decode("ascii").rstrip("="),
)
