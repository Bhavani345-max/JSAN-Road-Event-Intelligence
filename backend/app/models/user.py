from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UtcDateTime


class User(Base):
    """A reviewer account. Accounts are provisioned by an administrator."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # A temporary password set by an administrator (or on the server): the
    # account must choose its own before it can use REI (decision 0044).
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    # Registration and approval (decision 0045). Only "active" signs in; existing
    # and seeded accounts are active. A registration is "pending_approval" until an
    # administrator approves ("active") or rejects ("rejected"); "suspended" is an
    # active account an administrator stopped.
    status: Mapped[str] = mapped_column(String(24), default="active", server_default="active")
    # When the account proved it owns its email (a registration's link). None for
    # an unproved one: the seeded accounts, a registration not yet confirmed.
    email_verified_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    # A registration's request time; None for an account created otherwise.
    registered_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    # The administrator's last decision on the account (approve, reject, suspend,
    # reactivate): when, and who (a plain id, kept if that account goes).
    decided_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime)


class AuthSession(Base):
    """Server-side session record; only a SHA-256 digest of its cookie is stored."""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)


class RecoveryCode(Base):
    """One single-use recovery code of an account (decision 0044). Only a SHA-256
    digest is stored, as for session cookies: each code is 16 random characters
    (about 79 bits), shown once when created."""

    __tablename__ = "recovery_codes"

    code_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    # Set when the code is used; a used code never works again.
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)


class SecurityEvent(Base):
    """What happened to an account's credentials, and who did it (decision 0044).
    Never holds a password, a temporary password or a recovery code."""

    __tablename__ = "security_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime, index=True)
    # One of auth_service.SECURITY_EVENT_KINDS.
    kind: Mapped[str] = mapped_column(String(40))
    # The account concerned and the account that acted (None: on the server).
    # Kept as plain ids so the record outlives the account.
    account_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(300), nullable=True)


class EmailToken(Base):
    """A single-use link sent by email (decision 0045): to confirm a registration's
    email, or to reset a forgotten password. Only a SHA-256 digest of the 256-bit
    random token is stored; it expires, and a used one never works again."""

    __tablename__ = "email_tokens"

    token_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    # "verify_email" or "reset_password".
    purpose: Mapped[str] = mapped_column(String(24))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime)
    used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, nullable=True)
