"""Sending REI's emails (decision 0045): registration links, approval notices,
password reset links and password-change notices.

One provider for now, Resend (an HTTP API; Railway may block outgoing SMTP).
Another provider only needs a class with the same `send`. Without a complete
configuration there is no sender at all, and the callers say the feature is
unavailable: nothing pretends an email was sent. Message bodies hold links with
single-use tokens, so neither a message nor a token is ever logged.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"


class EmailDeliveryFailed(Exception):
    """The provider did not accept the message."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str
    # What the email is (for the log, which never holds its body).
    kind: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Hands the message to the provider. Raises EmailDeliveryFailed."""
        ...


class ResendSender:
    def __init__(self, api_key: str, sender: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._sender = sender
        self._client = client or httpx.Client(timeout=15)

    def send(self, message: EmailMessage) -> None:
        try:
            response = self._client.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"from": self._sender, "to": [message.to], "subject": message.subject, "text": message.text},
            )
        except httpx.HTTPError as error:
            raise EmailDeliveryFailed(f"The email service could not be reached ({type(error).__name__}).") from None
        if response.status_code >= 300:
            # The provider's own words, which never contain the message or the key.
            raise EmailDeliveryFailed(f"The email service refused the message (HTTP {response.status_code}).")


def email_sender(settings: Settings) -> EmailSender | None:
    """The configured sender, or None: no email can be sent."""
    if not settings.email_configured:
        return None
    return ResendSender(settings.email_api_key, settings.email_from)


def send_quietly(sender: EmailSender | None, message: EmailMessage) -> bool:
    """Sends after the answer has gone (a background task): a failure is logged by
    kind only, never with the address's link or token. Returns whether it was sent."""
    if sender is None:
        return False
    try:
        sender.send(message)
    except EmailDeliveryFailed as error:
        logger.warning("Email not sent (%s): %s", message.kind, error)
        return False
    logger.info("Email sent (%s).", message.kind)
    return True


# --- the messages -----------------------------------------------------------------------


def _link(settings: Settings, path: str, token: str) -> str:
    return f"{settings.app_base_url.rstrip('/')}{path}?token={token}"


def verification_message(settings: Settings, to: str, name: str, token: str) -> EmailMessage:
    minutes = settings.email_verification_minutes
    return EmailMessage(
        to=to,
        kind="email verification",
        subject="Confirm your email for JSAN Road Event Intelligence",
        text=(
            f"Hello {name},\n\n"
            "You asked for an account on JSAN Road Event Intelligence (REI). Confirm that this "
            "email address is yours:\n\n"
            f"{_link(settings, '/verify-email', token)}\n\n"
            f"The link works once, for {minutes // 60} hours. After you confirm, an administrator "
            "reviews your request; you will get an email when it is decided.\n\n"
            "If you did not ask for this, ignore this email: nothing happens without the link.\n"
        ),
    )


def approved_message(settings: Settings, to: str, name: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        kind="registration approved",
        subject="Your JSAN REI account is ready",
        text=(
            f"Hello {name},\n\n"
            "An administrator approved your JSAN Road Event Intelligence account. Sign in with "
            f"this email and the password you chose:\n\n{settings.app_base_url.rstrip('/')}/login\n"
        ),
    )


def rejected_message(settings: Settings, to: str, name: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        kind="registration rejected",
        subject="Your JSAN REI registration",
        text=(
            f"Hello {name},\n\n"
            "Your request for a JSAN Road Event Intelligence account was not approved. If you "
            "think this is a mistake, contact your REI administrator.\n"
        ),
    )


def reset_message(settings: Settings, to: str, name: str, token: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        kind="password reset link",
        subject="Reset your JSAN REI password",
        text=(
            f"Hello {name},\n\n"
            "Someone asked to reset the password of your JSAN Road Event Intelligence account. "
            "If it was you, choose a new password here:\n\n"
            f"{_link(settings, '/reset-password', token)}\n\n"
            f"The link works once, for {settings.password_reset_minutes} minutes.\n\n"
            "If it was not you, ignore this email: your password stays as it is.\n"
        ),
    )


def password_changed_message(settings: Settings, to: str, name: str) -> EmailMessage:
    return EmailMessage(
        to=to,
        kind="password changed notice",
        subject="Your JSAN REI password was changed",
        text=(
            f"Hello {name},\n\n"
            "The password of your JSAN Road Event Intelligence account was just changed with a "
            "reset link, and you were signed out everywhere.\n\n"
            "If you did not do this, contact your REI administrator at once.\n"
        ),
    )
