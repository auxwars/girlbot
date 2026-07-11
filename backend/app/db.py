"""Storage layer, per-user scoped. Works on either SQLite or Postgres.

Backend is chosen automatically:
  - if DATABASE_URL is set (e.g. Railway's Postgres plugin) -> Postgres
  - otherwise -> a local SQLite file (zero setup for local dev)

Everything is tied to a user id so memory can be permanent and account-specific
once Google sign-in is on. In local mode (no Google) there's a single implicit
"local" user, so it just works without logging in.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

from .config import settings

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_PG = DATABASE_URL.startswith("postgres")

if IS_PG:
    import psycopg
    from psycopg.rows import dict_row

# Primary-key declaration differs between the two engines.
_PK = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect():
    if IS_PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _conn() -> Iterator:
    c = _connect()
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _ph(sql: str) -> str:
    """SQLite uses ? placeholders, Postgres uses %s."""
    return sql.replace("?", "%s") if IS_PG else sql


def _exec(c, sql: str, params: tuple = ()):
    cur = c.cursor()
    cur.execute(_ph(sql), params)
    return cur


def _fetchone(c, sql: str, params: tuple = ()) -> Optional[dict]:
    row = _exec(c, sql, params).fetchone()
    return dict(row) if row else None


def _fetchall(c, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in _exec(c, sql, params).fetchall()]


def _insert(c, sql: str, params: tuple = ()) -> int:
    """Run an INSERT and return the new row id on either backend."""
    if IS_PG:
        return _exec(c, sql + " RETURNING id", params).fetchone()["id"]
    return _exec(c, sql, params).lastrowid


# --------------------------------------------------------------------------
# schema
# --------------------------------------------------------------------------

def init_db() -> None:
    stmts = [
        f"""CREATE TABLE IF NOT EXISTS users (
                id         {_PK},
                google_sub TEXT UNIQUE,
                email      TEXT DEFAULT '',
                name       TEXT DEFAULT '',
                picture    TEXT DEFAULT '',
                created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS user_settings (
                user_id          INTEGER PRIMARY KEY,
                anthropic_key    TEXT DEFAULT '',
                exa_key          TEXT DEFAULT '',
                openalex_mailto  TEXT DEFAULT '',
                model            TEXT DEFAULT 'claude-opus-4-8',
                training_enabled INTEGER DEFAULT 1,
                reliance         INTEGER DEFAULT 60,
                use_research     INTEGER DEFAULT 1,
                seeded           INTEGER DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS messages (
                id         {_PK},
                user_id    INTEGER NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
        )""",
        f"""CREATE TABLE IF NOT EXISTS examples (
                id           {_PK},
                user_id      INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL,
                her_message  TEXT NOT NULL,
                context      TEXT DEFAULT '',
                true_meaning TEXT NOT NULL,
                intent       TEXT NOT NULL,
                is_seed      INTEGER NOT NULL DEFAULT 0
        )""",
        f"""CREATE TABLE IF NOT EXISTS events (
                id         {_PK},
                user_id    INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                text       TEXT NOT NULL
        )""",
    ]
    with _conn() as c:
        for s in stmts:
            _exec(c, s)
        # migrate SQLite databases created by an earlier (pre-user) version
        if not IS_PG:
            cols = lambda t: {r["name"] for r in _exec(c, f"PRAGMA table_info({t})").fetchall()}
            if "user_id" not in cols("examples"):
                _exec(c, "ALTER TABLE examples ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            if "user_id" not in cols("events"):
                _exec(c, "ALTER TABLE events ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")
            if "seeded" not in cols("user_settings"):
                _exec(c, "ALTER TABLE user_settings ADD COLUMN seeded INTEGER DEFAULT 0")


# --------------------------------------------------------------------------
# users
# --------------------------------------------------------------------------

def get_user(user_id: int) -> Optional[dict]:
    with _conn() as c:
        return _fetchone(c, "SELECT * FROM users WHERE id = ?", (user_id,))


def get_or_create_local_user() -> dict:
    """The single implicit user when Google auth isn't configured."""
    with _conn() as c:
        row = _fetchone(c, "SELECT * FROM users WHERE google_sub = 'local'")
        if row:
            return row
        uid = _insert(c, "INSERT INTO users (google_sub, email, name, created_at)"
                         " VALUES ('local', '', 'You', ?)", (_now(),))
    _ensure_settings(uid)
    return get_user(uid)


def get_or_create_google_user(sub: str, email: str, name: str, picture: str) -> dict:
    with _conn() as c:
        row = _fetchone(c, "SELECT * FROM users WHERE google_sub = ?", (sub,))
        if row:
            _exec(c, "UPDATE users SET email=?, name=?, picture=? WHERE id=?",
                  (email or "", name or "", picture or "", row["id"]))
            uid = row["id"]
        else:
            uid = _insert(c, "INSERT INTO users (google_sub, email, name, picture, created_at)"
                             " VALUES (?,?,?,?,?)",
                          (sub, email or "", name or "", picture or "", _now()))
    _ensure_settings(uid)
    return get_user(uid)


# --------------------------------------------------------------------------
# per-user settings
# --------------------------------------------------------------------------

def _ensure_settings(user_id: int) -> None:
    with _conn() as c:
        exists = _fetchone(c, "SELECT 1 AS x FROM user_settings WHERE user_id=?", (user_id,))
        if not exists:
            _exec(c, "INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))


def get_settings(user_id: int) -> dict:
    _ensure_settings(user_id)
    with _conn() as c:
        return _fetchone(c, "SELECT * FROM user_settings WHERE user_id=?", (user_id,))


def mark_seeded(user_id: int) -> None:
    _ensure_settings(user_id)
    with _conn() as c:
        _exec(c, "UPDATE user_settings SET seeded = 1 WHERE user_id = ?", (user_id,))


_ALLOWED_SETTING_FIELDS = {
    "anthropic_key", "exa_key", "openalex_mailto", "model",
    "training_enabled", "reliance", "use_research",
}


def save_settings(user_id: int, **fields) -> None:
    _ensure_settings(user_id)
    updates = {k: v for k, v in fields.items() if k in _ALLOWED_SETTING_FIELDS and v is not None}
    if not updates:
        return
    cols = ", ".join(f"{k} = ?" for k in updates)
    with _conn() as c:
        _exec(c, f"UPDATE user_settings SET {cols} WHERE user_id = ?",
              (*updates.values(), user_id))


# --------------------------------------------------------------------------
# conversation memory (messages)
# --------------------------------------------------------------------------

def add_message(user_id: int, role: str, content: str) -> int:
    with _conn() as c:
        return _insert(c, "INSERT INTO messages (user_id, role, content, created_at)"
                          " VALUES (?,?,?,?)", (user_id, role, content.strip(), _now()))


def list_messages(user_id: int, limit: Optional[int] = None) -> list[dict]:
    """Oldest-first for display / prompt building."""
    with _conn() as c:
        if limit:
            return _fetchall(
                c,
                "SELECT * FROM (SELECT * FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?) sub"
                " ORDER BY id ASC",
                (user_id, limit),
            )
        return _fetchall(c, "SELECT * FROM messages WHERE user_id=? ORDER BY id ASC", (user_id,))


def clear_messages(user_id: int) -> int:
    with _conn() as c:
        return _exec(c, "DELETE FROM messages WHERE user_id=?", (user_id,)).rowcount


# --------------------------------------------------------------------------
# examples (learned patterns)
# --------------------------------------------------------------------------

def add_example(user_id: int, her_message: str, context: str, true_meaning: str,
                intent: str, is_seed: int = 0) -> int:
    with _conn() as c:
        return _insert(
            c,
            "INSERT INTO examples (user_id, created_at, her_message, context, true_meaning, intent, is_seed)"
            " VALUES (?,?,?,?,?,?,?)",
            (user_id, _now(), her_message.strip(), context.strip(),
             true_meaning.strip(), intent.strip(), is_seed),
        )


def example_exists(user_id: int, her_message: str, true_meaning: str) -> bool:
    with _conn() as c:
        return _fetchone(
            c, "SELECT 1 AS x FROM examples WHERE user_id=? AND her_message=? AND true_meaning=?",
            (user_id, her_message.strip(), true_meaning.strip()),
        ) is not None


def list_examples(user_id: int) -> list[dict]:
    with _conn() as c:
        return _fetchall(c, "SELECT * FROM examples WHERE user_id=? ORDER BY id DESC", (user_id,))


def delete_example(user_id: int, example_id: int) -> None:
    with _conn() as c:
        _exec(c, "DELETE FROM examples WHERE id=? AND user_id=?", (example_id, user_id))


def clear_seed_examples(user_id: int) -> int:
    with _conn() as c:
        return _exec(c, "DELETE FROM examples WHERE user_id=? AND is_seed=1", (user_id,)).rowcount


def clear_all_examples(user_id: int) -> int:
    with _conn() as c:
        return _exec(c, "DELETE FROM examples WHERE user_id=?", (user_id,)).rowcount


def count_examples(user_id: int) -> int:
    with _conn() as c:
        return _fetchone(c, "SELECT COUNT(*) AS c FROM examples WHERE user_id=?", (user_id,))["c"]


# --------------------------------------------------------------------------
# events (notable facts / recent stuff)
# --------------------------------------------------------------------------

def add_event(user_id: int, text: str) -> int:
    with _conn() as c:
        return _insert(c, "INSERT INTO events (user_id, created_at, text) VALUES (?,?,?)",
                       (user_id, _now(), text.strip()))


def event_exists(user_id: int, text: str) -> bool:
    with _conn() as c:
        return _fetchone(c, "SELECT 1 AS x FROM events WHERE user_id=? AND text=?",
                         (user_id, text.strip())) is not None


def list_events(user_id: int, limit: Optional[int] = None) -> list[dict]:
    q = "SELECT * FROM events WHERE user_id=? ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    with _conn() as c:
        return _fetchall(c, q, (user_id,))


def delete_event(user_id: int, event_id: int) -> None:
    with _conn() as c:
        _exec(c, "DELETE FROM events WHERE id=? AND user_id=?", (event_id, user_id))


def clear_events(user_id: int) -> int:
    with _conn() as c:
        return _exec(c, "DELETE FROM events WHERE user_id=?", (user_id,)).rowcount
