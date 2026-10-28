from collections import defaultdict, deque
from contextlib import nullcontext
from math import ceil
from threading import Lock
from time import monotonic
from typing import Annotated, NoReturn

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select

from app.api.auth_deps import require_account, require_account_admin, require_new_password
from app.api.deps import SessionDep
from app.models import User
from app.schemas.auth import (
    AuthOptionsOut,
    CurrentPasswordIn,
    EmailIn,
    LinkResetIn,
    LoginIn,
    PasswordChangeIn,
    ProfileIn,
    RecoveredOut,
    RecoverIn,
    RecoveryCodesOut,
    RecoveryCodesStatusOut,
    RegisterIn,
    TemporaryPasswordOut,
    TokenIn,
    UserOut,
)
from app.services import account_service
from app.services.email_service import (
    password_changed_message,
    reset_message,
    send_quietly,
    verification_message,
)
from app.services.auth_service import (
    authenticate,
    change_own_password,
    change_own_profile,
    create_recovery_codes,
    create_session,
    normalize_email,
    record_security_event,
    recover_with_code,
    recovery_code_status,
    reset_password_by_admin,
    revoke_session,
    status_problem,
    user_for_token,
    user_public,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
# Failed attempts in the last window, per account (decisions 0032, 0044): wrong
# passwords at sign-in, wrong current passwords and wrong recovery codes alike.
#
# There is no per-visitor limit: behind Railway's edge, CDN and the console's
# /api proxy, no request header identifies a visitor reliably (tested in
# production on 15 October 2026: X-Forwarded-For named whichever relay passed
# the request on), and an address limit keyed on a relay locks out unrelated
# users. Forwarded-address headers are therefore not read at all.
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
_ATTEMPT_LOCK = Lock()
# Failures are counted over this window, and a locked account waits a whole one.
_ATTEMPT_WINDOW_SECONDS = 30 * 60
# Failed attempts one account may have in the window; the last of them locks it
# (the user's rule of 28 October 2026: warn from the 3rd, lock at the 5th).
_ATTEMPT_LIMIT = 5
# From this failure on, the answer says how many attempts are left.
_WARN_FROM = 3
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


def _minutes(seconds: float) -> str:
    minutes = max(1, ceil(seconds / 60))
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _refuse_if_limited(account: str) -> None:
    now = monotonic()
    with _ATTEMPT_LOCK:
        if _recent_failures(account, now) >= _ATTEMPT_LIMIT:
            wait = _LOGIN_ATTEMPTS[account][0] + _ATTEMPT_WINDOW_SECONDS - now
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. This account is locked; try again in {_minutes(wait)}.",
            )


def _record_failure(account: str) -> int:
    """Counts a failure and returns the account's failures in the window. The one
    that reaches the limit locks the account for a whole window from now."""
    now = monotonic()
    with _ATTEMPT_LOCK:
        _recent_failures(account, now)
        attempts = _LOGIN_ATTEMPTS[account]
        attempts.append(now)
        count = len(attempts)
        if count >= _ATTEMPT_LIMIT:
            # Every failure now counts from this moment: they age out together,
            # a full window after the lock began.
            _LOGIN_ATTEMPTS[account] = deque([now] * count)
        # Made-up emails each add a key: forget those whose failures have aged out.
        if len(_LOGIN_ATTEMPTS) > _MAX_TRACKED_KEYS:
            for key in list(_LOGIN_ATTEMPTS):
                _recent_failures(key, now)
        return count


def _refuse_failed(account: str, message: str, status_code: int, on_lock=None) -> NoReturn:
    """Counts the failure and refuses it: from the warning on, with the attempts
    left; at the limit, with the lock. The same for every email, known or not."""
    count = _record_failure(account)
    if count >= _ATTEMPT_LIMIT:
        if on_lock:
            on_lock()
        raise HTTPException(
            status_code=429,
            detail=(
                f"{message} Too many failed attempts: this account is locked for "
                f"{_minutes(_ATTEMPT_WINDOW_SECONDS)}."
            ),
        )
    if count >= _WARN_FROM:
        left = _ATTEMPT_LIMIT - count
        message = (
            f"{message} {left} attempt{'s' if left != 1 else ''} left before this account is locked "
            f"for {_minutes(_ATTEMPT_WINDOW_SECONDS)}."
        )
    raise HTTPException(status_code=status_code, detail=message)


def _clear_failures(account: str) -> None:
    with _ATTEMPT_LOCK:
        _LOGIN_ATTEMPTS.pop(account, None)


def _one_writer_at_a_time(session) -> bool:
    """SQLite (local) takes one writer at a time; PostgreSQL (production) takes many."""
    return session.get_bind().dialect.name == "sqlite"


def _while_no_run_writes(request: Request, session):
    """On SQLite, wait for the source run in progress; on PostgreSQL, never: a run holds
    the run lock throughout, minutes for a first run of a large feed (decision 0040),
    and signing in or out must not wait for it."""
    if _one_writer_at_a_time(session):
        return request.app.state.ingestion_service.lock
    return nullcontext()


def _note_lock(request: Request, session, email: str):
    """Records, for an existing account, that it was locked (never for made-up emails)."""

    def note() -> None:
        session.rollback()
        user = session.scalar(select(User).where(User.email == normalize_email(email)))
        if user is None:
            return
        with _while_no_run_writes(request, session):
            record_security_event(
                session, "sign_in_locked", user,
                detail=f"{_ATTEMPT_LIMIT} failed attempts; locked for {_minutes(_ATTEMPT_WINDOW_SECONDS)}",
            )  # fmt: skip
            session.commit()

    return note


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, request: Request, response: Response, session: SessionDep) -> UserOut:
    # Counted per account: one account's failures never lock out another.
    account = f"account:{normalize_email(body.email)}"
    _refuse_if_limited(account)
    user = authenticate(session, body.email, body.password)
    if user is None:
        session.rollback()
        _refuse_failed(account, "The email or password is incorrect.", 401, _note_lock(request, session, body.email))
    # The right password, but a registration not yet approved, rejected or
    # suspended: no session, and the reason (said only to whoever knows the password).
    problem = status_problem(user)
    if problem:
        session.rollback()
        _clear_failures(account)
        raise HTTPException(status_code=403, detail=problem)

    settings = request.app.state.settings
    with _while_no_run_writes(request, session):
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
    _clear_failures(account)
    return UserOut(**user_public(user))


@router.get("/me", response_model=UserOut)
def me(request: Request, session: SessionDep) -> UserOut:
    settings = request.app.state.settings
    user = user_for_token(session, request.cookies.get(settings.auth_cookie_name))
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return UserOut(**user_public(user))


AccountDep = Annotated[User, Depends(require_account)]
NewPasswordDep = Annotated[User, Depends(require_new_password)]
AccountAdminDep = Annotated[User, Depends(require_account_admin)]


def _check_current_password(request: Request, session, user: User, password: str | None) -> None:
    """Refuses a wrong current password; wrong ones count towards the account's
    sign-in limit, so a left-open session cannot be used to guess it."""
    account = f"account:{user.email}"
    _refuse_if_limited(account)
    if not password or not verify_password(password, user.password_hash):
        _refuse_failed(account, "The current password is incorrect.", 400, _note_lock(request, session, user.email))


def _no_store(response: Response) -> None:
    """An answer holding a secret shown once is never kept by a browser or proxy."""
    response.headers["Cache-Control"] = "no-store"


@router.post("/profile", response_model=UserOut)
def update_profile(body: ProfileIn, request: Request, session: SessionDep, user: AccountDep) -> UserOut:
    """The signed-in account changes its own name or sign-in email (decision 0043)."""
    if body.email is not None and normalize_email(body.email) != user.email:
        _check_current_password(request, session, user, body.current_password)
    with _while_no_run_writes(request, session):
        try:
            change_own_profile(
                session,
                user,
                display_name=body.display_name,
                email=body.email,
                token=request.cookies.get(request.app.state.settings.auth_cookie_name),
            )
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from None
        session.commit()
    return UserOut(**user_public(user))


@router.post("/password")
def change_password(
    body: PasswordChangeIn, request: Request, session: SessionDep, user: NewPasswordDep
) -> dict[str, bool]:
    """The signed-in account changes its own password, a temporary one too; its
    other sessions end (decisions 0043, 0044)."""
    _check_current_password(request, session, user, body.current_password)
    with _while_no_run_writes(request, session):
        try:
            change_own_password(
                session, user, body.new_password, request.cookies.get(request.app.state.settings.auth_cookie_name)
            )
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from None
        session.commit()
    return {"ok": True}


# --- account recovery (decision 0044) -------------------------------------------------


@router.post("/accounts/{account_id}/temporary-password", response_model=TemporaryPasswordOut)
def reset_account_password(
    account_id: str,
    body: CurrentPasswordIn,
    request: Request,
    response: Response,
    session: SessionDep,
    admin: AccountAdminDep,
) -> TemporaryPasswordOut:
    """An administrator gives another, non-administrator account a temporary password,
    shown once here; that account chooses its own at its next sign-in. Its sessions
    end, and its sign-in lock (if any) is lifted."""
    _check_current_password(request, session, admin, body.current_password)
    with _while_no_run_writes(request, session):
        try:
            account, temporary = reset_password_by_admin(session, admin, account_id)
        except LookupError as error:
            session.rollback()
            raise HTTPException(status_code=404, detail=str(error)) from None
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from None
        session.commit()
    _clear_failures(f"account:{account.email}")
    _no_store(response)
    return TemporaryPasswordOut(account=UserOut(**user_public(account)), temporary_password=temporary)


@router.get("/recovery-codes", response_model=RecoveryCodesStatusOut)
def recovery_codes(session: SessionDep, admin: AccountAdminDep) -> RecoveryCodesStatusOut:
    """How many of the administrator's recovery codes are left; never the codes."""
    status = recovery_code_status(session, admin)
    return RecoveryCodesStatusOut(remaining=status.remaining, total=status.total, created_at=status.created_at)


@router.post("/recovery-codes", response_model=RecoveryCodesOut)
def new_recovery_codes(
    body: CurrentPasswordIn, request: Request, response: Response, session: SessionDep, admin: AccountAdminDep
) -> RecoveryCodesOut:
    """A new set of the administrator's single-use recovery codes, shown once; the
    earlier ones stop working."""
    _check_current_password(request, session, admin, body.current_password)
    with _while_no_run_writes(request, session):
        codes = create_recovery_codes(session, admin)
        session.commit()
    _no_store(response)
    return RecoveryCodesOut(codes=codes, created_at=recovery_code_status(session, admin).created_at)


@router.post("/recover", response_model=RecoveredOut)
def recover(body: RecoverIn, request: Request, session: SessionDep) -> RecoveredOut:
    """Forgot password: a new password with one of the account's recovery codes. Every
    wrong email or code gets the same answer and counts towards that email's limit."""
    account = f"account:{normalize_email(body.email)}"
    _refuse_if_limited(account)
    with _while_no_run_writes(request, session):
        try:
            left = recover_with_code(session, body.email, body.recovery_code, body.new_password)
        except ValueError as error:  # the new password breaks the policy; no code was used
            session.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from None
        if left is None:
            session.rollback()
        else:
            session.commit()
    if left is None:
        _refuse_failed(account, "The email or recovery code is not valid.", 400, _note_lock(request, session, body.email))
    _clear_failures(account)
    return RecoveredOut(ok=True, codes_left=left)


# --- registration and reset links (decision 0045) ----------------------------------------

# Requests per key in their window: registrations and reset requests per email and
# in all, and wrong links in all. In memory, like the sign-in limit.
_REQUESTS: dict[str, deque[float]] = defaultdict(deque)
_TOO_MANY = "Too many requests. Try again later."
# Self-registration is off unless switched on (decision 0046).
_REGISTRATION_CLOSED = "Registration is closed: accounts are created by your REI administrator."
# Wrong or expired links, from everyone together, before links wait (tokens are
# 256-bit: this is a brake, not their protection).
_LINK_FAILURE_LIMIT = 60
_LINK_FAILURE_WINDOW_SECONDS = 600
_BAD_LINK = "This link is not valid: it may have expired or been used already. Ask for a new one."
REGISTERED = (
    "Thank you. If this email can be registered, we sent it a link to confirm the address. "
    "After you confirm, an administrator reviews your request; you can sign in once it is approved."
)
RESET_SENT = (
    "If an active account with a confirmed email uses this address, we sent it a link to reset "
    "the password. Check your inbox; the link works once."
)


def _within(key: str, limit: int, window_seconds: float, *, count: bool = True) -> bool:
    """Whether `key` is under its limit; `count` records this request."""
    now = monotonic()
    with _ATTEMPT_LOCK:
        times = _REQUESTS[key]
        while times and now - times[0] >= window_seconds:
            times.popleft()
        if len(times) >= limit:
            return False
        if count:
            times.append(now)
        if len(_REQUESTS) > _MAX_TRACKED_KEYS:
            for other in [k for k, v in _REQUESTS.items() if not v]:
                del _REQUESTS[other]
        return True


def _email_unavailable(what: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"{what} is not available yet: REI cannot send email until an administrator sets up an email service.",
    )


@router.get("/options", response_model=AuthOptionsOut)
def options(request: Request) -> AuthOptionsOut:
    """What the sign-in page can offer: registration and reset links need email."""
    settings = request.app.state.settings
    sending = request.app.state.email_sender is not None
    open_ = settings.registration_open and sending
    return AuthOptionsOut(
        registration_open=open_,
        email_reset=settings.email_configured and sending,
        allowed_domains=sorted(settings.allowed_email_domain_set) if open_ else [],
    )


@router.post("/register", status_code=202)
def register(body: RegisterIn, request: Request, background: BackgroundTasks, session: SessionDep) -> dict:
    """A new employee asks for an account: a link proves the email, then an administrator
    decides. The same answer whether or not the email already has an account."""
    settings = request.app.state.settings
    sender = request.app.state.email_sender
    if not settings.registration_enabled:
        raise HTTPException(status_code=404, detail=_REGISTRATION_CLOSED)
    if not (settings.registration_open and sender):
        raise _email_unavailable("Registration")
    problem = account_service.email_domain_problem(body.email, settings.allowed_email_domain_set)
    problem = problem or account_service.password_problem(body.password, body.email)
    if problem:
        raise HTTPException(status_code=400, detail=problem)
    if not _within(f"register:{body.email}", 3, 3600) or not _within("register:*", 30, 3600):
        raise HTTPException(status_code=429, detail=_TOO_MANY)
    with _while_no_run_writes(request, session):
        result = account_service.register(
            session, name=body.full_name, email=body.email, password=body.password,
            verification_minutes=settings.email_verification_minutes,
        )  # fmt: skip
        session.commit()
    if result:
        user, token = result
        background.add_task(send_quietly, sender, verification_message(settings, user.email, user.display_name, token))
    return {"ok": True, "message": REGISTERED}


def _refuse_bad_links() -> None:
    if not _within("links:failed", _LINK_FAILURE_LIMIT, _LINK_FAILURE_WINDOW_SECONDS, count=False):
        raise HTTPException(status_code=429, detail=_TOO_MANY)


@router.post("/verify-email")
def verify_email(body: TokenIn, request: Request, session: SessionDep) -> dict[str, bool]:
    """The registration's emailed link: its email is proved; an administrator decides next."""
    if not request.app.state.settings.registration_enabled:
        raise HTTPException(status_code=404, detail=_REGISTRATION_CLOSED)
    _refuse_bad_links()
    with _while_no_run_writes(request, session):
        user = account_service.verify_email(session, body.token)
        if user is None:
            session.rollback()
        else:
            session.commit()
    if user is None:
        _within("links:failed", _LINK_FAILURE_LIMIT, _LINK_FAILURE_WINDOW_SECONDS)
        raise HTTPException(status_code=400, detail=_BAD_LINK)
    return {"ok": True}


@router.post("/forgot", status_code=202)
def forgot(body: EmailIn, request: Request, background: BackgroundTasks, session: SessionDep) -> dict:
    """Email me a reset link. The same answer whether or not the email has an account."""
    settings = request.app.state.settings
    sender = request.app.state.email_sender
    if not (settings.email_configured and sender):
        raise _email_unavailable("Resetting a password by email")
    if not _within(f"forgot:{body.email}", 3, 1800) or not _within("forgot:*", 60, 3600):
        raise HTTPException(status_code=429, detail=_TOO_MANY)
    with _while_no_run_writes(request, session):
        result = account_service.request_reset(session, body.email, settings.password_reset_minutes)
        session.commit()
    if result:
        user, token = result
        background.add_task(send_quietly, sender, reset_message(settings, user.email, user.display_name, token))
    return {"ok": True, "message": RESET_SENT}


@router.post("/reset-password")
def reset_password(body: LinkResetIn, request: Request, background: BackgroundTasks, session: SessionDep) -> dict[str, bool]:
    """A new password with an emailed reset link; every session of the account ends."""
    _refuse_bad_links()
    with _while_no_run_writes(request, session):
        try:
            user = account_service.reset_with_token(session, body.token, body.new_password)
        except ValueError as error:  # the password is not accepted; the link was not used
            session.rollback()
            raise HTTPException(status_code=400, detail=str(error)) from None
        if user is None:
            session.rollback()
        else:
            session.commit()
    if user is None:
        _within("links:failed", _LINK_FAILURE_LIMIT, _LINK_FAILURE_WINDOW_SECONDS)
        raise HTTPException(status_code=400, detail=_BAD_LINK)
    _clear_failures(f"account:{user.email}")
    sender = request.app.state.email_sender
    if sender is not None:
        background.add_task(send_quietly, sender, password_changed_message(request.app.state.settings, user.email, user.display_name))
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response, session: SessionDep) -> dict[str, bool]:
    settings = request.app.state.settings
    with _while_no_run_writes(request, session):
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
