from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models import User
from app.services.auth_service import user_for_token


# Who may change things: a reviewer records review decisions, an admin also
# runs sources. Any other role (a viewer) reads only.
REVIEW_ROLES = frozenset({"admin", "reviewer"})
ADMIN_ROLES = frozenset({"admin"})

# An account with a temporary password reaches nothing but choosing its own (decision 0044).
NEW_PASSWORD_FIRST = "Choose a new password first: this account has a temporary password."


def _signed_in(request: Request, session: Session, *, temporary_ok: bool = False) -> User:
    """The account whose session cookie came with the request; a change only from an
    allowed origin. An account with a temporary password is refused unless
    `temporary_ok` (the one route that replaces it)."""
    settings = request.app.state.settings
    user = user_for_token(session, request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in {value.rstrip("/") for value in settings.cors_origin_list}:
            raise HTTPException(status_code=403, detail="This origin is not allowed to make changes.")
    if user.must_change_password and not temporary_ok:
        raise HTTPException(status_code=403, detail=NEW_PASSWORD_FIRST)
    return user


def require_user(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    user = _signed_in(request, session)
    if request.method not in {"GET", "HEAD", "OPTIONS"} and user.role not in REVIEW_ROLES:
        raise HTTPException(status_code=403, detail="Your account can view events but not change them.")
    return user


def require_account(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    """The signed-in account, changing only itself (its name, email, password): any role,
    the view-only User too. Other accounts and REI's data stay out of reach."""
    return _signed_in(request, session)


def require_new_password(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    """The signed-in account changing its password, a temporary one too (decision 0044)."""
    return _signed_in(request, session, temporary_ok=True)


def require_account_admin(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    """Managing accounts (resetting another's password, recovery codes) is for administrators."""
    user = _signed_in(request, session)
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only an administrator can manage accounts.")
    return user


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    """Running sources by hand is for administrators."""
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only an administrator can run sources.")
    return user


CurrentUserDep = Annotated[User, Depends(require_user)]
