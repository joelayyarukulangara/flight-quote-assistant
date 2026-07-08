"""
SQLite persistence layer.

Tables:
- settings: key/value store for app settings (API keys, defaults, etc.)
- search_cache: cached one-way flight search results, keyed by search params
- saved_quotes: saved quote requests + results for the Saved Quotes tab
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import DB_PATH, DEFAULT_SETTINGS


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS search_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT,
                source TEXT,
                created_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS saved_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                package_name TEXT,
                request_json TEXT,
                result_json TEXT,
                ai_summary TEXT,
                created_at TEXT,
                last_refreshed_at TEXT
            )"""
        )
        existing = {row["key"] for row in conn.execute("SELECT key FROM settings")}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value))


# ---------------------------------------------------------------- settings

def get_setting(key: str, default: str = "") -> str:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def get_all_settings() -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}


def set_setting(key: str, value: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )


def set_settings(values: dict):
    with get_connection() as conn:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, str(value)),
            )


# ------------------------------------------------------------------ cache

def get_cached(cache_key: str, max_age_minutes: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload, source, created_at FROM search_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if not row:
            return None
        created_at = datetime.fromisoformat(row["created_at"])
        if datetime.now() - created_at > timedelta(minutes=max_age_minutes):
            return None
        return {"payload": json.loads(row["payload"]), "source": row["source"], "created_at": created_at}


def set_cached(cache_key: str, payload: list, source: str = "Cached"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO search_cache (cache_key, payload, source, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET payload = excluded.payload, "
            "source = excluded.source, created_at = excluded.created_at",
            (cache_key, json.dumps(payload), source, datetime.now().isoformat()),
        )


def clear_cache_for_key(cache_key: str):
    with get_connection() as conn:
        conn.execute("DELETE FROM search_cache WHERE cache_key = ?", (cache_key,))


# ------------------------------------------------------------- saved quotes

def save_quote(customer_name, package_name, request_json, result_json, ai_summary=""):
    now = datetime.now().isoformat()
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO saved_quotes (customer_name, package_name, request_json, result_json, "
            "ai_summary, created_at, last_refreshed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (customer_name, package_name, request_json, result_json, ai_summary, now, now),
        )
        return cursor.lastrowid


def update_saved_quote(quote_id, result_json=None, ai_summary=None):
    with get_connection() as conn:
        if result_json is not None:
            conn.execute(
                "UPDATE saved_quotes SET result_json = ?, last_refreshed_at = ? WHERE id = ?",
                (result_json, datetime.now().isoformat(), quote_id),
            )
        if ai_summary is not None:
            conn.execute("UPDATE saved_quotes SET ai_summary = ? WHERE id = ?", (ai_summary, quote_id))


def list_saved_quotes(search_text: str = ""):
    with get_connection() as conn:
        if search_text:
            like = f"%{search_text}%"
            rows = conn.execute(
                "SELECT * FROM saved_quotes WHERE customer_name LIKE ? OR package_name LIKE ? "
                "ORDER BY created_at DESC",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM saved_quotes ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_saved_quote(quote_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM saved_quotes WHERE id = ?", (quote_id,)).fetchone()
        return dict(row) if row else None


def delete_saved_quote(quote_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM saved_quotes WHERE id = ?", (quote_id,))
