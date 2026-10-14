from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.deps import SessionDep
from app.schemas.auth import LoginIn, UserOut
from app.services.auth_service import authenticate, create_session, revoke_session, user_for_token, user_public

router = APIRouter(prefix="/auth", tags=["authentication"])
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_ATTEMPT_LOCK = Lock()
_ATTEMPT_WINDOW_SECONDS = 15 * 60
_ATTEMPT_LIMIT = 8


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str) -> None:
    now = monotonic()
    with _ATTEMPT_LOCK:
        attempts = _LOGIN_ATTEMPTS[key]
        while attempts and now - attempts[0] >= _ATTEMPT_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= _ATTEMPT_LIMIT:
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")
        attempts.append(now)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, session: SessionDep) -> UserOut:
    key = _client_key(request)
    _check_rate_limit(key)
    user = authenticate(session, body.email, body.password)
    if user is None:
        session.rollback()
        raise HTTPException(status_code=401, detail="The email or password is incorrect.")

    settings = request.app.state.settings
    with request.app.state.ingestion_service.lock:
        token = create_session(session, user, settings.auth_session_hours)
        session.commit()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        max_age=settings.auth_session_hours * 60 * 60,
        path="/api",
    )
    with _ATTEMPT_LOCK:
        _LOGIN_ATTEMPTS.pop(key, None)
    return UserOut(**user_public(user))


@router.get("/me", response_model=UserOut)
def me(request: Request, session: SessionDep) -> UserOut:
    settings = request.app.state.settings
    user = user_for_token(session, request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return UserOut(**user_public(user))


@router.post("/logout")
def logout(request: Request, response: Response, session: SessionDep) -> dict[str, bool]:
    settings = request.app.state.settings
    with request.app.state.ingestion_service.lock:
        revoke_session(session, request.cookies.get(settings.auth_cookie_name))
        session.commit()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/api",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )
    return {"ok": True}
