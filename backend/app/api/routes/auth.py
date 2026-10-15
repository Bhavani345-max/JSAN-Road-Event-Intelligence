from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import APIRouter, HTTPException, Request, Response

from app.api.deps import SessionDep
from app.schemas.auth import LoginIn, UserOut
from app.services.auth_service import (
    authenticate,
    create_session,
    normalize_email,
    revoke_session,
    user_for_token,
    user_public,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
# Failed sign-ins in the last window, per account (decision 0032).
#
# There is no per-visitor limit: behind Railway's edge, CDN and the console's
# /api proxy, no request header identifies a visitor reliably (tested in
# production on 15 October 2026: X-Forwarded-For named whichever relay passed
# the request on), and an address limit keyed on a relay locks out unrelated
# users. Forwarded-address headers are therefore not read at all.
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_ATTEMPT_LOCK = Lock()
_ATTEMPT_WINDOW_SECONDS = 15 * 60
# Failed sign-ins one account may have in the window.
_ATTEMPT_LIMIT = 8
# Accounts tracked before those whose failures have aged out are swept.
_MAX_TRACKED_KEYS = 10_000


def _recent_failures(key: str, now: float) -> int:
    """Failures of `key` in the window; a key with none left is forgotten."""
    attempts = _LOGIN_ATTEMPTS.get(key)
    if not attempts:
        return 0
    while attempts and now - attempts[0] >= _ATTEMPT_WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        del _LOGIN_ATTEMPTS[key]
    return len(attempts)


def _refuse_if_limited(account: str) -> None:
    now = monotonic()
    with _ATTEMPT_LOCK:
        if _recent_failures(account, now) >= _ATTEMPT_LIMIT:
            raise HTTPException(status_code=429, detail="Too many sign-in attempts. Try again in 15 minutes.")


def _record_failure(account: str) -> None:
    now = monotonic()
    with _ATTEMPT_LOCK:
        _recent_failures(account, now)
        _LOGIN_ATTEMPTS[account].append(now)
        # Made-up emails each add a key: forget those whose failures have aged out.
        if len(_LOGIN_ATTEMPTS) > _MAX_TRACKED_KEYS:
            for key in list(_LOGIN_ATTEMPTS):
                _recent_failures(key, now)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, session: SessionDep) -> UserOut:
    # Counted per account: one account's failures never lock out another.
    account = f"account:{normalize_email(body.email)}"
    _refuse_if_limited(account)
    user = authenticate(session, body.email, body.password)
    if user is None:
        session.rollback()
        _record_failure(account)
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
        _LOGIN_ATTEMPTS.pop(account, None)
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
