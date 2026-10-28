import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Enter a valid email address")
        return normalized


class ProfileIn(BaseModel):
    """The signed-in account's own details; a field left out stays as it is.
    A new email needs the current password."""

    display_name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    current_password: str | None = Field(default=None, max_length=1024)

    @field_validator("display_name")
    @classmethod
    def tidy_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        tidy = " ".join(value.split())
        if not tidy:
            raise ValueError("Enter a name")
        return tidy


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=1, max_length=1024)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    # A temporary password: the console asks for a new one before anything else.
    must_change_password: bool = False


# --- account recovery (decision 0044) -------------------------------------------------


class CurrentPasswordIn(BaseModel):
    """An administrator confirms a sensitive change with their own password."""

    current_password: str = Field(min_length=1, max_length=1024)


class TemporaryPasswordOut(BaseModel):
    account: UserOut
    # Shown once to the administrator, never stored or logged in clear.
    temporary_password: str


class RecoveryCodesStatusOut(BaseModel):
    remaining: int
    total: int
    created_at: datetime | None


class RecoveryCodesOut(BaseModel):
    # Shown once; only their digests are stored.
    codes: list[str]
    created_at: datetime


class RecoverIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    recovery_code: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=1, max_length=1024)


class RecoveredOut(BaseModel):
    ok: bool
    codes_left: int


# --- registration, approval and reset links (decision 0045) --------------------------------

_EMAIL_FORM = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _tidy_name(value: str) -> str:
    tidy = " ".join(value.split())
    if not tidy:
        raise ValueError("Enter your full name")
    return tidy


def _company_email(value: str) -> str:
    normalized = value.strip().lower()
    if not _EMAIL_FORM.fullmatch(normalized):
        raise ValueError("Enter a valid email address")
    return normalized


class RegisterIn(BaseModel):
    """A new employee's request. No role: every registration is a view-only User."""

    full_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("full_name")
    @classmethod
    def tidy_full_name(cls, value: str) -> str:
        return _tidy_name(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _company_email(value)


class EmailIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _company_email(value)


class TokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class LinkResetIn(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=1024)


class AuthOptionsOut(BaseModel):
    """What the sign-in page can offer, given the configuration."""

    registration_open: bool
    email_reset: bool
    allowed_domains: list[str]


class AccountOut(BaseModel):
    """An account as the administrator's User management shows it."""

    id: str
    email: str
    display_name: str
    role: str
    status: str
    email_verified: bool
    must_change_password: bool
    registered_at: datetime | None
    decided_at: datetime | None
    # The deciding administrator's name.
    decided_by: str | None
    created_at: datetime


class SecurityEventOut(BaseModel):
    kind: str
    occurred_at: datetime
    # Who acted: an account's name, or "the server".
    by: str
    detail: str | None


# --- accounts created by administrators (decision 0046) ----------------------------------


class CreateAccountIn(BaseModel):
    """A new account, made by an administrator, who confirms with their own password."""

    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    role: Literal["admin", "user"]
    current_password: str = Field(min_length=1, max_length=1024)

    @field_validator("display_name")
    @classmethod
    def tidy_display_name(cls, value: str) -> str:
        return _tidy_name(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _company_email(value)


class RoleChangeIn(BaseModel):
    role: Literal["admin", "user"]
    current_password: str = Field(min_length=1, max_length=1024)


class CreatedAccountOut(BaseModel):
    account: AccountOut
    # Shown once to the administrator, never stored or logged in clear.
    temporary_password: str
