"""Check that REI can really send email (decision 0045):

    python backend/cli/send_test_email.py you@your-company-domain

Uses the same configuration as the API (EMAIL_PROVIDER, EMAIL_FROM, EMAIL_API_KEY,
APP_BASE_URL). Says what is missing, or sends one plain test message and says
whether the provider accepted it. Accepted is not delivered: check the inbox
(and spam) before relying on registration and reset links.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.services.email_service import EmailDeliveryFailed, EmailMessage, email_sender  # noqa: E402


def missing(settings) -> list[str]:
    names = []
    if settings.email_provider.strip().lower() != "resend":
        names.append("EMAIL_PROVIDER=resend")
    for name, value in (("EMAIL_FROM", settings.email_from), ("EMAIL_API_KEY", settings.email_api_key),
                        ("APP_BASE_URL", settings.app_base_url)):  # fmt: skip
        if not value:
            names.append(name)
    return names


def main() -> int:
    if len(sys.argv) != 2 or "@" not in sys.argv[1]:
        print(__doc__)
        return 2
    settings = get_settings()
    sender = email_sender(settings)
    if sender is None:
        print("Email is not configured. Missing: " + ", ".join(missing(settings)))
        return 1
    message = EmailMessage(
        to=sys.argv[1].strip(),
        kind="test message",
        subject="JSAN REI test email",
        text="This is a test from JSAN Road Event Intelligence. If you can read it, REI's email works.\n",
    )
    try:
        sender.send(message)
    except EmailDeliveryFailed as error:
        print(f"Not sent: {error}")
        return 1
    print(f"Accepted by the provider for {message.to}. Check that inbox (and spam) to confirm delivery.")
    if not settings.allowed_email_domain_set:
        print("Note: ALLOWED_EMAIL_DOMAINS is empty, so registration stays closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
