from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .accounts import find_user, public_user
from .database import utcnow
from .models import User
from .schemas import ConstraintUpdatePayload, LoginPayload, ReviewPayload, SignupPayload
from .security import (
    SESSION_COOKIE,
    admin_user,
    clear_session_cookie,
    create_session,
    current_user,
    get_db,
    hash_password,
    revoke_session,
    verify_password,
    workspace_user,
)
from .tenant_store import audit, ensure_workspace, get_constraint_settings, update_constraint_settings


router = APIRouter(prefix="/api")


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(body: SignupPayload, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User.id).where(or_(User.username == body.username, User.email == str(body.email)))):
        raise HTTPException(status_code=409, detail="Username or email is already registered")
    user = User(
        username=body.username,
        email=str(body.email),
        password_hash=hash_password(body.password),
        role="user",
        status="pending",
        full_name=body.full_name.strip(),
        phone=body.phone.strip() if body.phone else None,
        institution_name=body.institution_name.strip(),
        department=body.department.strip() if body.department else None,
        designation=body.designation.strip() if body.designation else None,
        signup_reason=body.signup_reason.strip() if body.signup_reason else None,
    )
    db.add(user)
    try:
        db.flush()
        audit(db, "account.signup_requested", user.id, user.id)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email is already registered")
    return {"message": "Registration submitted for administrator review", "user": public_user(user)}


@router.post("/auth/login")
def login(body: LoginPayload, response: Response, db: Session = Depends(get_db)) -> dict:
    user = find_user(db, body.identifier)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    if user.status == "pending":
        raise HTTPException(status_code=403, detail="Your registration is awaiting administrator approval")
    if user.status == "denied":
        raise HTTPException(status_code=403, detail="Your registration request was denied")
    create_session(db, user, response)
    return {"ok": True, "user": public_user(user)}


@router.post("/auth/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict:
    revoke_session(db, token)
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"user": public_user(user)}


@router.get("/admin/requests")
def registration_requests(
    status_filter: str = "pending",
    db: Session = Depends(get_db),
    _: User = Depends(admin_user),
) -> dict:
    query = select(User).where(User.role != "admin")
    if status_filter in {"pending", "approved", "denied"}:
        query = query.where(User.status == status_filter)
    users = db.scalars(query.order_by(User.created_at.desc())).all()
    return {"requests": [public_user(user) for user in users], "count": len(users)}


@router.put("/admin/requests/{user_id}")
def review_registration(
    user_id: str,
    body: ReviewPayload,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_user),
) -> dict:
    user = db.get(User, user_id)
    if not user or user.role == "admin":
        raise HTTPException(status_code=404, detail="Registration request not found")
    user.status = body.decision
    user.admin_note = body.admin_note.strip() if body.admin_note else None
    user.reviewed_at = utcnow()
    if body.decision == "approved":
        ensure_workspace(db, user.id, seed=False)
    audit(db, f"account.{body.decision}", admin.id, user.id, note=user.admin_note)
    db.commit()
    return {"message": f"Account {body.decision}", "user": public_user(user)}


@router.get("/constraints")
def constraints(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict:
    return {"constraints": get_constraint_settings(db, user.id)}


@router.put("/constraints")
def update_constraints(
    body: ConstraintUpdatePayload,
    db: Session = Depends(get_db),
    user: User = Depends(workspace_user),
) -> dict:
    try:
        rows = update_constraint_settings(
            db,
            user.id,
            [item.model_dump() for item in body.constraints],
            user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"constraints": rows}
