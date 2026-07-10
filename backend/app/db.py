"""SQLite layer with per-user scoping.

Everything is tied to a user id so memory can be permanent and account-specific
once Google sign-in is on. In local mode (no Google configured) there's a single
implicit "local" user, so it just works without logging in.
"""
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


def _cols(conn, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                google_sub TEXT UNIQUE,
                email      TEXT DEFAULT '',
                name       TEXT DEFAULT '',
                picture    TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_settings (
                user_id          INTEGER PRIMARY KEY,
                anthropic_key    TEXT DEFAULT '',
                exa_key          TEXT DEFAULT '',
                openalex_mailto  TEXT DEFAULT '',
                model            TEXT DEFAULT 'claude-opus-4-8',
                training_enabled INTEGER DEFAULT 1,
                reliance         INTEGER DEFAULT 60,
                use_research     INTEGER DEFAULT 1,
                seeded           INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS examples (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL,
                her_message  TEXT NOT NULL,
                context      TEXT DEFAULT '',
                true_meaning TEXT NOT NULL,
                intent       TEXT NOT NULL,
                is_seed      INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS events (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                text       TEXT NOT NULL
            );
            """
        )
        # tiny migrations for databases created by an earlier version
        if "user_id" not in _cols(conn, "examples"):
            conn.execute("ALTER TABLE examples ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        if "user_id" not in _cols(conn, "events"):
            conn.execute("ALTER TABLE events ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
        if "seeded" not in _cols(conn, "user_settings"):
            conn.execute("ALTER TABLE user_settings ADD COLUMN seeded INTEGER DEFAULT 0")


# ---- users --------------------------------------------------------------

def _row_to_user(row) -> dict:
    return dict(row) if row else None


def get_user(user_id: int) -> Optional[dict]:
    with get_conn() as conn:
        return _row_to_user(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())


def get_or_create_local_user() -> dict:
    """The single implicit user when Google auth isn't configured."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = 'local'").fetchone()
        if row:
            return dict(row)
        cur = conn.execute(
            "INSERT INTO users (google_sub, email, name, created_at) VALUES ('local', '', 'You', ?)",
            (_now(),),
        )
        uid = cur.lastrowid
    _ensure_settings(uid)
    return get_user(uid)


def get_or_create_google_user(sub: str, email: str, name: str, picture: str) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
        if row:
            conn.execute("UPDATE users SET email=?, name=?, picture=? WHERE id=?",
                         (email or "", name or "", picture or "", row["id"]))
            uid = row["id"]
        else:
            cur = conn.execute(
                "INSERT INTO users (google_sub, email, name, picture, created_at) VALUES (?,?,?,?,?)",
                (sub, email or "", name or "", picture or "", _now()),
            )
            uid = cur.lastrowid
    _ensure_settings(uid)
    return get_user(uid)


# ---- per-user settings --------------------------------------------------

def _ensure_settings(user_id: int) -> None:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
        if not exists:
            conn.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))


def get_settings(user_id: int) -> dict:
    _ensure_settings(user_id)
    with get_conn() as conn:
        return dict(conn.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,)).fetchone())


_ALLOWED_SETTING_FIELDS = {
    "anthropic_key", "exa_key", "openalex_mailto", "model",
    "training_enabled", "reliance", "use_research",
}


def mark_seeded(user_id: int) -> None:
    _ensure_settings(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE user_settings SET seeded = 1 WHERE user_id = ?", (user_id,))


def save_settings(user_id: int, **fields) -> None:
    _ensure_settings(user_id)
    updates = {k: v for k, v in fields.items() if k in _ALLOWED_SETTING_FIELDS and v is not None}
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    with get_conn() as conn:
        conn.execute(f"UPDATE user_settings SET {cols} WHERE user_id = ?",
                     (*updates.values(), user_id))


# ---- conversation memory (messages) -------------------------------------

def add_message(user_id: int, role: str, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (user_id, role, content, created_at) VALUES (?,?,?,?)",
            (user_id, role, content.strip(), _now()),
        )
        return cur.lastrowid


def list_messages(user_id: int, limit: Optional[int] = None) -> list[dict]:
    """Oldest-first for display / prompt building."""
    with get_conn() as conn:
        if limit:
            rows = conn.execute(
                "SELECT * FROM (SELECT * FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?)"
                " ORDER BY id ASC",
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM messages WHERE user_id=? ORDER BY id ASC", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def clear_messages(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM messages WHERE user_id=?", (user_id,)).rowcount


# ---- examples (learned patterns) ----------------------------------------

def add_example(user_id: int, her_message: str, context: str, true_meaning: str,
                intent: str, is_seed: int = 0) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO examples (user_id, created_at, her_message, context, true_meaning, intent, is_seed)"
            " VALUES (?,?,?,?,?,?,?)",
            (user_id, _now(), her_message.strip(), context.strip(),
             true_meaning.strip(), intent.strip(), is_seed),
        )
        return cur.lastrowid


def example_exists(user_id: int, her_message: str, true_meaning: str) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM examples WHERE user_id=? AND her_message=? AND true_meaning=?",
            (user_id, her_message.strip(), true_meaning.strip()),
        ).fetchone() is not None


def list_examples(user_id: int) -> list[dict]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM examples WHERE user_id=? ORDER BY id DESC", (user_id,)).fetchall()]


def delete_example(user_id: int, example_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM examples WHERE id=? AND user_id=?", (example_id, user_id))


def clear_seed_examples(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM examples WHERE user_id=? AND is_seed=1", (user_id,)).rowcount


def clear_all_examples(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM examples WHERE user_id=?", (user_id,)).rowcount


def count_examples(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM examples WHERE user_id=?", (user_id,)).fetchone()["c"]


# ---- events (notable facts / recent stuff) ------------------------------

def add_event(user_id: int, text: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO events (user_id, created_at, text) VALUES (?,?,?)",
            (user_id, _now(), text.strip()),
        )
        return cur.lastrowid


def event_exists(user_id: int, text: str) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM events WHERE user_id=? AND text=?", (user_id, text.strip())
        ).fetchone() is not None


def list_events(user_id: int, limit: Optional[int] = None) -> list[dict]:
    q = "SELECT * FROM events WHERE user_id=? ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, (user_id,)).fetchall()]


def delete_event(user_id: int, event_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM events WHERE id=? AND user_id=?", (event_id, user_id))


def clear_events(user_id: int) -> int:
    with get_conn() as conn:
        return conn.execute("DELETE FROM events WHERE user_id=?", (user_id,)).rowcount
