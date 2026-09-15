from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .config import settings
from .database import utcnow
from .models import User
from .security import hash_password
from .tenant_store import audit, ensure_workspace


def public_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "full_name": user.full_name,
        "phone": user.phone,
        "institution_name": user.institution_name,
        "department": user.department,
        "designation": user.designation,
        "signup_reason": user.signup_reason,
        "admin_note": user.admin_note,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "reviewed_at": user.reviewed_at.isoformat() if user.reviewed_at else None,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


def bootstrap_admin(db: Session) -> User:
    existing = db.scalar(select(User).where(User.role == "admin"))
    if existing:
        return existing
    admin = User(
        username=settings.admin_username.strip().lower(),
        email=settings.admin_email.strip().lower(),
        password_hash=hash_password(settings.admin_password),
        role="admin",
        status="approved",
        full_name="System Administrator",
        institution_name="ReSched AI",
        designation="Administrator",
        reviewed_at=utcnow(),
    )
    db.add(admin)
    db.flush()
    ensure_workspace(db, admin.id)
    audit(db, "account.bootstrap_admin", admin.id, admin.id)
    db.commit()
    return admin


def find_user(db: Session, identifier: str) -> User | None:
    value = identifier.strip().lower()
    return db.scalar(select(User).where(or_(User.username == value, User.email == value)))
