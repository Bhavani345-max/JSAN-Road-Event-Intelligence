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


def require_user(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    settings = request.app.state.settings
    user = user_for_token(session, request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in {value.rstrip("/") for value in settings.cors_origin_list}:
            raise HTTPException(status_code=403, detail="This origin is not allowed to make changes.")
        if user.role not in REVIEW_ROLES:
            raise HTTPException(status_code=403, detail="Your account can view events but not change them.")
    return user


def require_admin(user: Annotated[User, Depends(require_user)]) -> User:
    """Running sources by hand is for administrators."""
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only an administrator can run sources.")
    return user


CurrentUserDep = Annotated[User, Depends(require_user)]
