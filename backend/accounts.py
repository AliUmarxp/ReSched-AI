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
        "is_demo": bool(settings.enable_demo_account and user.username == settings.demo_username),
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
    audit(db, "account.bootstrap_admin", admin.id, admin.id)
    db.commit()
    return admin


def bootstrap_demo(db: Session) -> User | None:
    if not settings.enable_demo_account:
        return None
    existing = db.scalar(select(User).where(User.username == settings.demo_username))
    if existing:
        ensure_workspace(db, existing.id, seed=True)
        return existing
    # A deployment can designate an already-existing seeded account as the demo
    # without knowing or replacing its password. Creating a brand-new demo account,
    # however, always requires an explicit password from the secret manager.
    if not settings.demo_password:
        return None
    demo = User(
        username=settings.demo_username,
        email=settings.demo_email,
        password_hash=hash_password(settings.demo_password),
        role="user",
        status="approved",
        full_name="Demo Registrar",
        institution_name="Demo University",
        designation="Registrar",
        reviewed_at=utcnow(),
    )
    db.add(demo)
    db.flush()
    ensure_workspace(db, demo.id, seed=True)
    audit(db, "account.bootstrap_demo", demo.id, demo.id)
    db.commit()
    return demo


def find_user(db: Session, identifier: str) -> User | None:
    value = identifier.strip().lower()
    return db.scalar(select(User).where(or_(User.username == value, User.email == value)))
