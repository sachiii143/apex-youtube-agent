"""
audit_log.py — APEX Phase 1b
Immutable append-only event log. Every external action recorded.
No updates, no deletes — append only. Secrets auto-redacted.
"""

import sqlite3, json, uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "apex_data.db"

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id    TEXT NOT NULL UNIQUE,
        action      TEXT NOT NULL,
        actor       TEXT NOT NULL DEFAULT 'system',
        subject     TEXT,
        payload     TEXT,
        recorded_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def record(action: str, subject: str = None, payload: dict = None, actor: str = "system") -> str:
    event_id = str(uuid.uuid4())
    now      = datetime.utcnow().isoformat()
    safe     = _redact(payload or {})
    conn = _conn()
    conn.execute(
        "INSERT INTO audit_log (event_id,action,actor,subject,payload,recorded_at) VALUES (?,?,?,?,?,?)",
        (event_id, action, actor, subject, json.dumps(safe), now)
    )
    conn.commit(); conn.close()
    return event_id

def _redact(d: dict) -> dict:
    sensitive = {"api_key","secret","token","password","key","credential"}
    out = {}
    for k, v in d.items():
        if any(s in k.lower() for s in sensitive):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _redact(v)
        else:
            out[k] = v
    return out

def tail(limit: int = 50, action_filter: str = None) -> list:
    conn = _conn()
    if action_filter:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE action=? ORDER BY id DESC LIMIT ?",
            (action_filter, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    cols = ["id","event_id","action","actor","subject","payload","recorded_at"]
    result = []
    for row in rows:
        d = dict(zip(cols, row))
        if d["payload"]:
            try: d["payload"] = json.loads(d["payload"])
            except: pass
        result.append(d)
    return result

def summary() -> dict:
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
    by_action = dict(conn.execute(
        "SELECT action, COUNT(*) FROM audit_log GROUP BY action ORDER BY COUNT(*) DESC"
    ).fetchall())
    conn.close()
    return {"total_events": total, "by_action": by_action}
