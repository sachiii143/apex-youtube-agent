"""
approval.py — APEX Phase 1c
Every publish/spend action blocked until owner approves.
Cards expire after 24h. Any field change invalidates the card.
"""

import sqlite3, json, uuid, hashlib
from datetime import datetime, timedelta
from pathlib import Path
import audit_log

DB_PATH = Path(__file__).parent / "apex_data.db"
CARD_TTL_HOURS = 24

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS approval_cards (
        card_id      TEXT PRIMARY KEY,
        action_type  TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        payload      TEXT NOT NULL,
        status       TEXT NOT NULL DEFAULT 'pending',
        issued_at    TEXT NOT NULL,
        expires_at   TEXT NOT NULL,
        decided_at   TEXT,
        decided_by   TEXT,
        notes        TEXT
    )""")
    conn.commit()
    return conn

def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

def issue(action_type: str, payload: dict, ttl_hours: int = CARD_TTL_HOURS) -> str:
    card_id = str(uuid.uuid4())
    now     = datetime.utcnow()
    expires = (now + timedelta(hours=ttl_hours)).isoformat()
    conn = _conn()
    conn.execute("""INSERT INTO approval_cards
        (card_id,action_type,payload_hash,payload,status,issued_at,expires_at)
        VALUES (?,?,?,?,?,?,?)""",
        (card_id, action_type, _hash(payload), json.dumps(payload), "pending", now.isoformat(), expires))
    conn.commit(); conn.close()
    audit_log.record("APPROVAL_ISSUED", subject=card_id, payload={"action_type": action_type})
    return card_id

def approve(card_id: str, decided_by: str = "owner", notes: str = "") -> dict:
    return _decide(card_id, "approved", decided_by, notes)

def reject(card_id: str, decided_by: str = "owner", notes: str = "") -> dict:
    return _decide(card_id, "rejected", decided_by, notes)

def _decide(card_id, status, decided_by, notes):
    conn = _conn()
    row = conn.execute("SELECT * FROM approval_cards WHERE card_id=?", (card_id,)).fetchone()
    if not row: conn.close(); return {"ok": False, "reason": "Card not found"}
    cols = ["card_id","action_type","payload_hash","payload","status","issued_at","expires_at","decided_at","decided_by","notes"]
    card = dict(zip(cols, row))
    if card["status"] != "pending": conn.close(); return {"ok": False, "reason": f"Card already {card['status']}"}
    if datetime.utcnow().isoformat() > card["expires_at"]:
        conn.execute("UPDATE approval_cards SET status='expired' WHERE card_id=?", (card_id,))
        conn.commit(); conn.close()
        audit_log.record("APPROVAL_EXPIRED", subject=card_id)
        return {"ok": False, "reason": "Card expired"}
    conn.execute("UPDATE approval_cards SET status=?,decided_at=?,decided_by=?,notes=? WHERE card_id=?",
                 (status, datetime.utcnow().isoformat(), decided_by, notes, card_id))
    conn.commit(); conn.close()
    return {"ok": True, "status": status, "card_id": card_id}

def check(card_id: str, payload: dict) -> dict:
    conn = _conn()
    row = conn.execute("SELECT * FROM approval_cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    if not row: return {"ok": False, "reason": "Card not found"}
    cols = ["card_id","action_type","payload_hash","payload","status","issued_at","expires_at","decided_at","decided_by","notes"]
    card = dict(zip(cols, row))
    if card["status"] != "approved": return {"ok": False, "reason": f"Card is {card['status']}, not approved"}
    if datetime.utcnow().isoformat() > card["expires_at"]: return {"ok": False, "reason": "Card expired after approval"}
    if _hash(payload) != card["payload_hash"]: return {"ok": False, "reason": "Payload changed after card was issued — reissue required"}
    return {"ok": True, "card_id": card_id, "decided_by": card["decided_by"]}

def pending_cards() -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM approval_cards WHERE status='pending' ORDER BY issued_at DESC").fetchall()
    conn.close()
    cols = ["card_id","action_type","payload_hash","payload","status","issued_at","expires_at","decided_at","decided_by","notes"]
    result = []
    for row in rows:
        d = dict(zip(cols, row))
        try: d["payload"] = json.loads(d["payload"])
        except: pass
        result.append(d)
    return result

def get_card(card_id: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM approval_cards WHERE card_id=?", (card_id,)).fetchone()
    conn.close()
    if not row: return None
    cols = ["card_id","action_type","payload_hash","payload","status","issued_at","expires_at","decided_at","decided_by","notes"]
    d = dict(zip(cols, row))
    try: d["payload"] = json.loads(d["payload"])
    except: pass
    return d
