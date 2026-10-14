from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.models import User
from app.services.auth_service import user_for_token


def require_user(request: Request, session: Annotated[Session, Depends(get_session)]) -> User:
    settings = request.app.state.settings
    user = user_for_token(session, request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in {value.rstrip("/") for value in settings.cors_origin_list}:
            raise HTTPException(status_code=403, detail="This origin is not allowed to make changes.")
    return user


CurrentUserDep = Annotated[User, Depends(require_user)]
