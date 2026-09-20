"""
memory.py — APEX
Persistent SQLite memory — Nova remembers everything from day one.
Facts, chat history, session log.
"""

import sqlite3, json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "apex_data.db"

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS chat_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        session_id TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS session_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        started_at TEXT NOT NULL,
        summary TEXT
    )""")
    conn.commit()
    return conn

# ── Facts (persistent key-value memory) ──────────────────────────────────────

def remember(key: str, value: str):
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO facts (key,value,updated_at) VALUES (?,?,?)",
                 (key, value, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def recall(key: str) -> str | None:
    conn = _conn()
    row = conn.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None

def recall_all() -> dict:
    conn = _conn()
    rows = conn.execute("SELECT key,value FROM facts ORDER BY updated_at DESC").fetchall()
    conn.close()
    return dict(rows)

def forget(key: str):
    conn = _conn()
    conn.execute("DELETE FROM facts WHERE key=?", (key,))
    conn.commit(); conn.close()

# ── Chat history ──────────────────────────────────────────────────────────────

def save_message(role: str, content: str, session_id: str = "default"):
    conn = _conn()
    conn.execute("INSERT INTO chat_log (role,content,timestamp,session_id) VALUES (?,?,?,?)",
                 (role, content, datetime.utcnow().isoformat(), session_id))
    conn.commit(); conn.close()

def get_history(limit: int = 20, session_id: str = None) -> list:
    conn = _conn()
    if session_id:
        rows = conn.execute(
            "SELECT role,content,timestamp FROM chat_log WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT role,content,timestamp FROM chat_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [{"role":r[0],"content":r[1],"timestamp":r[2]} for r in reversed(rows)]

def get_context_messages(limit: int = 10) -> list:
    """Return last N messages formatted for LLM context."""
    history = get_history(limit=limit)
    return [{"role": m["role"], "content": m["content"]} for m in history]

def chat_summary() -> dict:
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM chat_log WHERE timestamp >= date('now')"
    ).fetchone()[0]
    conn.close()
    return {"total_messages": total, "today": today}
