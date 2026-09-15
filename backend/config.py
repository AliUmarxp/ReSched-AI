from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _database_url(value: str) -> str:
    """Select psycopg v3 explicitly for standard provider Postgres URLs."""
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


@dataclass(frozen=True)
class Settings:
    app_env: str
    secret_key: str
    database_url: str
    session_cookie_secure: bool
    session_ttl_hours: int
    admin_username: str
    admin_email: str
    admin_password: str
    allowed_origins: tuple[str, ...]
    enable_demo_account: bool
    demo_username: str
    demo_email: str
    demo_password: str

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


def load_settings() -> Settings:
    origins = tuple(
        item.strip()
        for item in os.getenv(
            "ALLOWED_ORIGINS", "http://127.0.0.1:8002,http://localhost:8002"
        ).split(",")
        if item.strip()
    )
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development"),
        secret_key=os.getenv("APP_SECRET_KEY", "development-only-change-me"),
        database_url=_database_url(os.getenv("DATABASE_URL", "sqlite:///./data/resched_ai_app.sqlite3")),
        session_cookie_secure=_as_bool(os.getenv("SESSION_COOKIE_SECURE"), False),
        session_ttl_hours=_as_int(os.getenv("SESSION_TTL_HOURS"), 24),
        admin_username=os.getenv("ADMIN_USERNAME", "admin"),
        admin_email=os.getenv("ADMIN_EMAIL", "admin@example.com"),
        admin_password=os.getenv("ADMIN_PASSWORD", "admin123"),
        allowed_origins=origins,
        enable_demo_account=_as_bool(os.getenv("ENABLE_DEMO_ACCOUNT"), False),
        demo_username=os.getenv("DEMO_USERNAME", "demo").strip().lower(),
        demo_email=os.getenv("DEMO_EMAIL", "demo@resched.local").strip().lower(),
        demo_password=os.getenv("DEMO_PASSWORD", ""),
    )
    if settings.is_production:
        if len(settings.secret_key) < 32 or settings.secret_key == "development-only-change-me":
            raise RuntimeError("APP_SECRET_KEY must be a unique value of at least 32 characters in production")
        if settings.admin_password in {"admin123", "change-this-before-deployment"}:
            raise RuntimeError("ADMIN_PASSWORD must be changed in production")
        if not settings.session_cookie_secure:
            raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")
        if settings.enable_demo_account and len(settings.demo_password) < 10:
            raise RuntimeError("DEMO_PASSWORD must contain at least 10 characters when the demo account is enabled")
    return settings


settings = load_settings()
