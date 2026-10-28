"""User management for administrators (decisions 0045, 0046): accounts to create,
roles to give, accounts to deactivate or activate, each account's security history,
and registrations to approve or reject when self-registration is on. Every route
needs an active administrator's session (require_account_admin)."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.auth_deps import require_account_admin
from app.api.deps import SessionDep
from app.api.routes.auth import _check_current_password, _no_store, _while_no_run_writes
from app.models import User
from app.schemas.auth import AccountOut, CreatedAccountOut, CreateAccountIn, RoleChangeIn, SecurityEventOut
from app.services import account_service
from app.services.email_service import approved_message, rejected_message, send_quietly

router = APIRouter(prefix="/admin/users", tags=["user management"])
AdminDep = Annotated[User, Depends(require_account_admin)]
# Who sees what first: waiting registrations, then active, suspended, rejected.
_ORDER = {"pending_approval": 0, "active": 1, "suspended": 2, "rejected": 3}


def _names(session) -> dict[str, str]:
    return dict(session.execute(select(User.user_id, User.display_name)).all())


def _out(user: User, names: dict[str, str]) -> AccountOut:
    return AccountOut(
        id=user.user_id,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        status=user.status,
        email_verified=user.email_verified_at is not None,
        must_change_password=user.must_change_password,
        registered_at=user.registered_at,
        decided_at=user.decided_at,
        decided_by=names.get(user.decided_by) if user.decided_by else None,
        created_at=user.created_at,
    )


@router.get("", response_model=list[AccountOut])
def accounts(session: SessionDep, admin: AdminDep) -> list[AccountOut]:
    names = _names(session)
    users = session.scalars(select(User)).all()
    users = sorted(users, key=lambda u: (_ORDER.get(u.status, 9), -(u.registered_at or u.created_at).timestamp()))
    return [_out(user, names) for user in users]


def _decide(request: Request, session, admin: User, account_id: str, decision) -> User:
    with _while_no_run_writes(request, session):
        try:
            user = decision(session, admin, account_id)
        except LookupError as error:
            session.rollback()
            raise HTTPException(status_code=404, detail=str(error)) from None
        except account_service.DecisionRefused as error:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(error)) from None
        session.commit()
    return user


@router.post("", response_model=CreatedAccountOut, status_code=201)
def create(
    body: CreateAccountIn, request: Request, response: Response, session: SessionDep, admin: AdminDep
) -> CreatedAccountOut:
    """A new account with the role given, active at once, and a temporary password shown
    once here; the person chooses their own at the first sign-in (decision 0046)."""
    _check_current_password(request, session, admin, body.current_password)
    with _while_no_run_writes(request, session):
        try:
            user, temporary = account_service.create_account(
                session, admin, name=body.display_name, email=body.email, role=body.role
            )
            session.commit()
        except (account_service.DuplicateAccount, account_service.DecisionRefused) as error:
            session.rollback()
            raise HTTPException(status_code=409, detail=str(error)) from None
        except IntegrityError:  # created at the same moment by another request
            session.rollback()
            raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    _no_store(response)
    return CreatedAccountOut(account=_out(user, _names(session)), temporary_password=temporary)


@router.post("/{account_id}/role", response_model=AccountOut)
def change_role(account_id: str, body: RoleChangeIn, request: Request, session: SessionDep, admin: AdminDep) -> AccountOut:
    """Admin or User for another active account, confirmed with the administrator's password."""
    _check_current_password(request, session, admin, body.current_password)
    user = _decide(
        request, session, admin, account_id,
        lambda session, admin, account_id: account_service.change_role(session, admin, account_id, body.role),
    )  # fmt: skip
    return _out(user, _names(session))


@router.post("/{account_id}/approve", response_model=AccountOut)
def approve(account_id: str, request: Request, background: BackgroundTasks, session: SessionDep, admin: AdminDep) -> AccountOut:
    """A registration that confirmed its email becomes an active, view-only account."""
    user = _decide(request, session, admin, account_id, account_service.approve)
    sender = request.app.state.email_sender
    if sender is not None:
        background.add_task(send_quietly, sender, approved_message(request.app.state.settings, user.email, user.display_name))
    return _out(user, _names(session))


@router.post("/{account_id}/reject", response_model=AccountOut)
def reject(account_id: str, request: Request, background: BackgroundTasks, session: SessionDep, admin: AdminDep) -> AccountOut:
    user = _decide(request, session, admin, account_id, account_service.reject)
    sender = request.app.state.email_sender
    # Never mail an address nobody proved.
    if sender is not None and user.email_verified_at is not None:
        background.add_task(send_quietly, sender, rejected_message(request.app.state.settings, user.email, user.display_name))
    return _out(user, _names(session))


@router.post("/{account_id}/suspend", response_model=AccountOut)
def suspend(account_id: str, request: Request, session: SessionDep, admin: AdminDep) -> AccountOut:
    """The account stops at once: signed out everywhere, refused everything."""
    return _out(_decide(request, session, admin, account_id, account_service.suspend), _names(session))


@router.post("/{account_id}/reactivate", response_model=AccountOut)
def reactivate(account_id: str, request: Request, session: SessionDep, admin: AdminDep) -> AccountOut:
    return _out(_decide(request, session, admin, account_id, account_service.reactivate), _names(session))


@router.get("/{account_id}/history", response_model=list[SecurityEventOut])
def account_history(account_id: str, session: SessionDep, admin: AdminDep) -> list[SecurityEventOut]:
    try:
        events = account_service.history(session, account_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    names = _names(session)
    return [
        SecurityEventOut(
            kind=event.kind,
            occurred_at=event.occurred_at,
            by=names.get(event.actor_id, "a removed account") if event.actor_id else "the server",
            detail=event.detail,
        )
        for event in events
    ]
