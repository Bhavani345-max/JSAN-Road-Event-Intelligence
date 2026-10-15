"""Local password authentication and opaque, revocable server sessions."""

import base64
import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import AuthSession, User
from packages.common.time import utc_now

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
    return user if user and user.is_active else None


def revoke_session(session: Session, token: str | None) -> None:
    if token and len(token) <= 200:
        digest = hashlib.sha256(token.encode("ascii", errors="ignore")).hexdigest()
        session.execute(delete(AuthSession).where(AuthSession.token_hash == digest))


def user_public(user: User) -> dict[str, str]:
    return {
        "id": user.user_id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


_DUMMY_SALT = b"REI login timing salt"
_DUMMY_DIGEST = hashlib.pbkdf2_hmac("sha256", b"unused", _DUMMY_SALT, PASSWORD_ROUNDS)
_DUMMY_PASSWORD_HASH = "pbkdf2_sha256${}${}${}".format(
    PASSWORD_ROUNDS,
    base64.urlsafe_b64encode(_DUMMY_SALT).decode("ascii").rstrip("="),
    base64.urlsafe_b64encode(_DUMMY_DIGEST).decode("ascii").rstrip("="),
)
