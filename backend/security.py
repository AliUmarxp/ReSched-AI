from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import timedelta

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, utcnow
from .models import AuthSession, User


SESSION_COOKIE = "resched_session"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32
    )
    return "scrypt${}${}${}${}${}".format(
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user: User, response: Response) -> None:
    token = secrets.token_urlsafe(48)
    expires_at = utcnow() + timedelta(hours=settings.session_ttl_hours)
    db.add(AuthSession(user_id=user.id, token_hash=_token_hash(token), expires_at=expires_at))
    user.last_login_at = utcnow()
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def revoke_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == _token_hash(token)))
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


def _extract_token(cookie_token: str | None, authorization: str | None) -> str | None:
    if cookie_token:
        return cookie_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def current_user(
    db: Session = Depends(get_db),
    cookie_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    authorization: str | None = Header(default=None),
) -> User:
    token = _extract_token(cookie_token, authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == _token_hash(token),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > utcnow(),
        )
    )
    if not auth_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid")
    user = db.get(User, auth_session.user_id)
    if not user or user.status != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not approved")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


def workspace_user(user: User = Depends(current_user)) -> User:
    if user.role != "user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A university user account is required for scheduling work",
        )
    return user


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
