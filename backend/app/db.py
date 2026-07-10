"""Tiny SQLite layer. No ORM — just enough to store what we learn from."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from .config import settings


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS examples (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT NOT NULL,
                her_message  TEXT NOT NULL,
                context      TEXT DEFAULT '',
                true_meaning TEXT NOT NULL,
                intent       TEXT NOT NULL,
                is_seed      INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                text       TEXT NOT NULL
            );
            """
        )


# ---- examples -----------------------------------------------------------

def add_example(her_message: str, context: str, true_meaning: str,
                intent: str, is_seed: int = 0) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO examples (created_at, her_message, context, true_meaning, intent, is_seed)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (_now(), her_message.strip(), context.strip(), true_meaning.strip(),
             intent.strip(), is_seed),
        )
        return cur.lastrowid


def list_examples() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM examples ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_example(example_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM examples WHERE id = ?", (example_id,))


def clear_seed_examples() -> int:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM examples WHERE is_seed = 1")
        return cur.rowcount


def count_examples() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM examples").fetchone()["c"]


# ---- events (short-term memory) ----------------------------------------

def add_event(text: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (created_at, text) VALUES (?, ?)",
            (_now(), text.strip()),
        )
        return cur.lastrowid


def list_events(limit: Optional[int] = None) -> list[dict]:
    q = "SELECT * FROM events ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q).fetchall()]


def delete_event(event_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
