from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .seed_data import get_seed_data


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "resched_ai.sqlite3"

ENTITY_NAMES = {
    "institution",
    "sourceInsights",
    "aiProfile",
    "programs",
    "timeSlots",
    "teachers",
    "courses",
    "sections",
    "rooms",
    "repeatStudents",
}


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_sets (
                name TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) AS count FROM entity_sets").fetchone()["count"]
        if count == 0:
            seed_database(conn)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_database(conn: sqlite3.Connection | None = None) -> dict:
    dataset = get_seed_data()
    own_conn = conn is None
    if conn is None:
        conn = connect()
    try:
        conn.execute("DELETE FROM entity_sets")
        conn.execute("DELETE FROM runs")
        for name, payload in dataset.items():
            conn.execute(
                """
                INSERT INTO entity_sets (name, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (name, json.dumps(payload), now_iso()),
            )
        if own_conn:
            conn.commit()
    finally:
        if own_conn:
            conn.close()
    return dataset


def load_dataset() -> dict[str, Any]:
    init_db()
    with connect() as conn:
        rows = conn.execute("SELECT name, payload FROM entity_sets").fetchall()
    dataset = {row["name"]: json.loads(row["payload"]) for row in rows}
    for key, value in get_seed_data().items():
        dataset.setdefault(key, value)
    return dataset


def save_entity_set(name: str, payload: Any) -> dict[str, Any]:
    if name not in ENTITY_NAMES:
        raise ValueError(f"Unknown entity set: {name}")
    init_db()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO entity_sets (name, payload, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
            """,
            (name, json.dumps(payload), now_iso()),
        )
    return load_dataset()


def save_run(payload: dict[str, Any]) -> dict[str, Any]:
    init_db()
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO runs (created_at, payload) VALUES (?, ?)",
            (now_iso(), json.dumps(payload)),
        )
        run_id = cursor.lastrowid
    latest = dict(payload)
    latest["id"] = run_id
    return latest


def latest_run() -> dict[str, Any] | None:
    init_db()
    with connect() as conn:
        row = conn.execute(
            "SELECT id, created_at, payload FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload"])
    payload["id"] = row["id"]
    payload["created_at"] = row["created_at"]
    return payload
