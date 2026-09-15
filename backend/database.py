from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


if settings.database_url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)


engine_options: dict = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    if os.getenv("VERCEL"):
        engine_options["poolclass"] = NullPool
    else:
        engine_options.update({"pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_database() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
