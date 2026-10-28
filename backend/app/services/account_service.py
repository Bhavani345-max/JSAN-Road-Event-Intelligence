"""Registration, email verification, administrator approval and reset links (decision 0045).

A registration is a "pending_approval" account with the view-only User role,
which can do nothing until it has proved its email (a single-use link) and an
administrator has approved it. No registration can choose a role. Links are
256-bit random tokens of which only SHA-256 digests are stored; each expires and
works once. Every decision is recorded in security_events. The callers answer
alike whether or not an email has an account.
"""

import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import AuthSession, EmailToken, SecurityEvent, User
from app.services.auth_service import (
    ACTIVE,
    ADMIN_ROLE,
    ASSIGNABLE_ROLES,
    MIN_PASSWORD_LENGTH,
    PENDING_APPROVAL,
    REJECTED,
    SUSPENDED,
    USER_ROLE,
    hash_password,
    normalize_email,
    record_security_event,
    set_temporary_password,
)
from packages.common.time import utc_now

VERIFY_EMAIL = "verify_email"
RESET_PASSWORD = "reset_password"

# Passwords too common to allow, whatever their length (a short list of the most
# used ones; length is the main rule).
COMMON_PASSWORDS = frozenset({
    "password", "password1", "password123", "passw0rd", "12345678", "123456789", "1234567890",
    "qwerty123", "qwertyuiop", "11111111", "00000000", "iloveyou", "welcome1", "letmein1",
    "admin123", "administrator", "changeme", "abc12345", "jsan1234", "jsanconsulting",
})  # fmt: skip


def password_problem(password: str, email: str | None = None) -> str | None:
    """Why a password someone chooses is not accepted, or None (registration, reset links)."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Passwords must contain at least {MIN_PASSWORD_LENGTH} characters"
    if password.lower() in COMMON_PASSWORDS or len(set(password)) < 4:
        return "This password is too easy to guess: use a longer phrase or a random password."
    if email:
        name = normalize_email(email).partition("@")[0]
        if len(name) >= 3 and name in password.lower():
            return "The password must not contain your email's name."
    return None


def email_domain_problem(email: str, allowed: frozenset[str]) -> str | None:
    """Why the email cannot register: not one of the company domains, or None."""
    domain = normalize_email(email).rpartition("@")[2]
    if domain in allowed:
        return None
    listed = ", ".join(f"@{name}" for name in sorted(allowed))
    return f"Use your company email address ({listed})."


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8", errors="ignore")).hexdigest()


def _new_token(session: Session, user: User, purpose: str, minutes: int) -> str:
    """A new single-use link token; the account's earlier unused ones of the same kind stop working."""
    now = utc_now()
    session.execute(
        update(EmailToken)
        .where(EmailToken.user_id == user.user_id, EmailToken.purpose == purpose, EmailToken.used_at.is_(None))
        .values(used_at=now)
    )
    token = secrets.token_urlsafe(32)
    session.add(
        EmailToken(
            token_id=str(uuid.uuid4()),
            user_id=user.user_id,
            purpose=purpose,
            token_hash=_digest(token),
            created_at=now,
            expires_at=now + timedelta(minutes=minutes),
        )
    )
    session.flush()
    return token


def _use_token(session: Session, token: str, purpose: str) -> User | None:
    """The token's account, the token used up; None for an unknown, expired or used one."""
    if not token or len(token) > 200:
        return None
    now = utc_now()
    row = session.scalar(select(EmailToken).where(EmailToken.token_hash == _digest(token), EmailToken.purpose == purpose))
    if row is None or row.used_at is not None or row.expires_at <= now:
        return None
    # Used up in the statement that checks it: two requests cannot both use it.
    used = session.execute(
        update(EmailToken).where(EmailToken.token_id == row.token_id, EmailToken.used_at.is_(None)).values(used_at=now)
    ).rowcount
    if used != 1:
        return None
    return session.get(User, row.user_id)


# --- registration ------------------------------------------------------------------------


def register(
    session: Session, *, name: str, email: str, password: str, verification_minutes: int
) -> tuple[User, str] | None:
    """A new registration, waiting to prove its email: the account and the link token.

    For an email that already has an account: a registration that has not yet
    proved its email gets a new link (the earlier one stops working; its password
    is left as it was); any other account gets nothing. None then, changing
    nothing else; the caller answers the same either way. The password is hashed
    in every case, so every answer takes as long. The caller commits.
    """
    email = normalize_email(email)
    password_hash = hash_password(password)
    existing = session.scalar(select(User).where(func.lower(func.trim(User.email)) == email))
    if existing is not None:
        if existing.status == PENDING_APPROVAL and existing.email_verified_at is None:
            return existing, _new_token(session, existing, VERIFY_EMAIL, verification_minutes)
        return None
    now = utc_now()
    user = User(
        user_id=str(uuid.uuid4()),
        email=email,
        display_name=name,
        password_hash=password_hash,
        role=USER_ROLE,  # never chosen by the registrant
        is_active=True,
        status=PENDING_APPROVAL,
        registered_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()
    record_security_event(session, "registered", user, detail="registration received; email not yet confirmed")
    return user, _new_token(session, user, VERIFY_EMAIL, verification_minutes)


def verify_email(session: Session, token: str) -> User | None:
    """The registration whose link this is, its email now proved; None for a link that
    is not valid (unknown, expired, used, or not a waiting registration's). The caller commits."""
    user = _use_token(session, token, VERIFY_EMAIL)
    if user is None or user.status != PENDING_APPROVAL:
        return None
    user.email_verified_at = utc_now()
    user.updated_at = user.email_verified_at
    record_security_event(session, "email_verified", user, actor=user)
    session.flush()
    return user


# --- reset links -------------------------------------------------------------------------


def request_reset(session: Session, email: str, minutes: int) -> tuple[User, str] | None:
    """A reset link token for an active account with a proved email, or None (the caller
    answers alike). A pending registration never gets one. The caller commits."""
    user = session.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None or user.status != ACTIVE or not user.is_active or user.email_verified_at is None:
        return None
    token = _new_token(session, user, RESET_PASSWORD, minutes)
    record_security_event(session, "password_reset_requested", user)
    return user, token


def reset_with_token(session: Session, token: str, new_password: str) -> User | None:
    """Sets the new password of the link's account and ends all its sessions; None,
    changing nothing, for a link that is not valid. Raises ValueError for a password
    that is not accepted, before the link is used. The caller commits."""
    problem = password_problem(new_password)
    if problem:
        raise ValueError(problem)
    password_hash = hash_password(new_password)
    user = _use_token(session, token, RESET_PASSWORD)
    if user is None or user.status != ACTIVE or not user.is_active:
        return None
    user.password_hash = password_hash
    user.must_change_password = False
    user.updated_at = utc_now()
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.user_id))
    record_security_event(session, "password_reset_with_link", user, actor=user)
    session.flush()
    return user


# --- administrator decisions -------------------------------------------------------------


class DecisionRefused(ValueError):
    """The account is not in a state that allows this decision."""


def _account(session: Session, account_id: str) -> User:
    user = session.get(User, account_id)
    if user is None:
        raise LookupError("No such account.")
    return user


def _decided(session: Session, admin: User, user: User, status: str, kind: str, detail: str | None = None) -> User:
    now = utc_now()
    user.status = status
    user.decided_at = now
    user.decided_by = admin.user_id
    user.updated_at = now
    record_security_event(session, kind, user, actor=admin, detail=detail)
    session.flush()
    return user


def _end_sessions_and_links(session: Session, user: User) -> None:
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.user_id))
    session.execute(
        update(EmailToken).where(EmailToken.user_id == user.user_id, EmailToken.used_at.is_(None)).values(used_at=utc_now())
    )


def approve(session: Session, admin: User, account_id: str) -> User:
    """A registration that proved its email becomes an active, view-only account."""
    user = _account(session, account_id)
    if user.status != PENDING_APPROVAL:
        raise DecisionRefused("Only a registration waiting for approval can be approved.")
    if user.email_verified_at is None:
        raise DecisionRefused("This registration has not confirmed its email yet: it cannot be approved.")
    user.role = USER_ROLE  # least privilege, whatever was stored
    return _decided(session, admin, user, ACTIVE, "account_approved", detail=f"role {USER_ROLE}")


def reject(session: Session, admin: User, account_id: str) -> User:
    user = _account(session, account_id)
    if user.status != PENDING_APPROVAL:
        raise DecisionRefused("Only a registration waiting for approval can be rejected.")
    _end_sessions_and_links(session, user)
    return _decided(session, admin, user, REJECTED, "account_rejected")


def suspend(session: Session, admin: User, account_id: str) -> User:
    """An active account stops at once: its sessions and links end."""
    user = _account(session, account_id)
    if user.user_id == admin.user_id:
        raise DecisionRefused("You cannot deactivate your own account.")
    if user.status != ACTIVE:
        raise DecisionRefused("Only an active account can be deactivated.")
    if user.role == ADMIN_ROLE and _active_admins(session) <= 1:
        raise DecisionRefused("The last active administrator cannot be deactivated.")
    _end_sessions_and_links(session, user)
    return _decided(session, admin, user, SUSPENDED, "account_suspended")


def reactivate(session: Session, admin: User, account_id: str) -> User:
    user = _account(session, account_id)
    if user.status != SUSPENDED:
        raise DecisionRefused("Only a deactivated account can be activated.")
    return _decided(session, admin, user, ACTIVE, "account_reactivated")


class DuplicateAccount(ValueError):
    """Another account already uses the email."""


def _active_admins(session: Session) -> int:
    return session.scalar(
        select(func.count()).select_from(User).where(User.role == ADMIN_ROLE, User.status == ACTIVE, User.is_active)
    )


def create_account(session: Session, admin: User, *, name: str, email: str, role: str) -> tuple[User, str]:
    """An account an administrator creates (decision 0046): active at once, with the
    role given and a random temporary password, returned once to be handed over and
    replaced at the first sign-in. Raises DuplicateAccount for an email already used
    (in any case), DecisionRefused for a role REI does not give. The caller commits."""
    if role not in ASSIGNABLE_ROLES:
        raise DecisionRefused("Choose Admin or User.")
    email = normalize_email(email)
    if session.scalar(select(User.user_id).where(func.lower(func.trim(User.email)) == email)):
        raise DuplicateAccount("An account with this email already exists.")
    now = utc_now()
    user = User(
        user_id=str(uuid.uuid4()),
        email=email,
        display_name=name,
        # No usable password until the temporary one below.
        password_hash="!",
        role=role,
        is_active=True,
        status=ACTIVE,
        decided_at=now,
        decided_by=admin.user_id,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    session.flush()
    record_security_event(session, "account_created", user, actor=admin, detail=f"role {role}")
    return user, set_temporary_password(session, user, actor=admin)


def change_role(session: Session, admin: User, account_id: str, role: str) -> User:
    """Gives another active account the Admin or User role; it applies to its next
    request. Never an administrator's own role, never the last active administrator's."""
    user = _account(session, account_id)
    if role not in ASSIGNABLE_ROLES:
        raise DecisionRefused("Choose Admin or User.")
    if user.user_id == admin.user_id:
        raise DecisionRefused("You cannot change your own role.")
    if user.status != ACTIVE:
        raise DecisionRefused("Only an active account's role can be changed.")
    if user.role == role:
        raise DecisionRefused("The account already has this role.")
    if user.role == ADMIN_ROLE and _active_admins(session) <= 1:
        raise DecisionRefused("The last active administrator must keep the role.")
    old = user.role
    user.role = role
    now = utc_now()
    user.updated_at = now
    user.decided_at = now
    user.decided_by = admin.user_id
    record_security_event(session, "role_changed", user, actor=admin, detail=f"{old} -> {role}")
    session.flush()
    return user


def history(session: Session, account_id: str, limit: int = 50) -> list[SecurityEvent]:
    """The account's recorded security events, newest first."""
    _account(session, account_id)
    return list(
        session.scalars(
            select(SecurityEvent)
            .where(SecurityEvent.account_id == account_id)
            .order_by(SecurityEvent.occurred_at.desc())
            .limit(limit)
        )
    )
