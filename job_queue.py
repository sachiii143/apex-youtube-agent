"""
job_queue.py — APEX Phase 1a
Idempotent job queue with retry (max 3) and dead-letter log.
"""

import sqlite3, json, uuid, time, threading, traceback
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "apex_data.db"

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
        job_id       TEXT PRIMARY KEY,
        job_type     TEXT NOT NULL,
        payload      TEXT NOT NULL,
        status       TEXT NOT NULL DEFAULT 'pending',
        attempts     INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL,
        result       TEXT,
        error        TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS dead_letter (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id      TEXT NOT NULL,
        job_type    TEXT NOT NULL,
        payload     TEXT NOT NULL,
        final_error TEXT,
        failed_at   TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def enqueue(job_type: str, payload: dict, job_id: str = None, max_attempts: int = 3) -> str:
    jid = job_id or str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = _conn()
    conn.execute("""INSERT OR IGNORE INTO jobs
        (job_id,job_type,payload,status,attempts,max_attempts,created_at,updated_at)
        VALUES (?,?,?,?,0,?,?,?)""",
        (jid, job_type, json.dumps(payload), "pending", max_attempts, now, now))
    conn.commit(); conn.close()
    return jid

def get_job(job_id: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    conn.close()
    if not row: return None
    cols = ["job_id","job_type","payload","status","attempts","max_attempts","created_at","updated_at","result","error"]
    d = dict(zip(cols, row))
    d["payload"] = json.loads(d["payload"])
    return d

def list_jobs(status: str = None, limit: int = 50) -> list:
    conn = _conn()
    if status:
        rows = conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    cols = ["job_id","job_type","payload","status","attempts","max_attempts","created_at","updated_at","result","error"]
    return [dict(zip(cols, r)) for r in rows]

def list_dead_letter(limit: int = 20) -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM dead_letter ORDER BY failed_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    cols = ["id","job_id","job_type","payload","final_error","failed_at"]
    result = []
    for row in rows:
        d = dict(zip(cols, row))
        try: d["payload"] = json.loads(d["payload"])
        except: pass
        result.append(d)
    return result

_handlers: dict = {}

def register(job_type: str):
    def decorator(fn):
        _handlers[job_type] = fn
        return fn
    return decorator

def _mark(conn, job_id, status, result=None, error=None):
    conn.execute("""UPDATE jobs SET status=?,result=?,error=?,updated_at=?,
                    attempts=attempts+1 WHERE job_id=?""",
                 (status, result, error, datetime.utcnow().isoformat(), job_id))
    conn.commit()

def _process_one(job: dict) -> bool:
    handler = _handlers.get(job["job_type"])
    if not handler:
        conn = _conn(); _mark(conn, job["job_id"], "dead", error=f"No handler for {job['job_type']}"); conn.close()
        return False
    conn = _conn(); _mark(conn, job["job_id"], "running"); conn.close()
    try:
        result = handler(job["payload"])
        conn = _conn(); _mark(conn, job["job_id"], "done", result=json.dumps(result or {})); conn.close()
        return True
    except Exception as e:
        err = traceback.format_exc()
        conn = _conn()
        attempts = job["attempts"] + 1
        if attempts >= job["max_attempts"]:
            _mark(conn, job["job_id"], "dead", error=err)
            conn.execute("INSERT INTO dead_letter (job_id,job_type,payload,final_error,failed_at) VALUES (?,?,?,?,?)",
                (job["job_id"], job["job_type"], json.dumps(job["payload"]), err, datetime.utcnow().isoformat()))
        else:
            _mark(conn, job["job_id"], "pending", error=err)
        conn.commit(); conn.close()
        return False

_worker_running = False
_worker_thread  = None

def start_worker(poll_interval: float = 2.0):
    global _worker_running, _worker_thread
    if _worker_running: return
    _worker_running = True
    def loop():
        while _worker_running:
            try:
                conn = _conn()
                rows = conn.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY created_at LIMIT 5").fetchall()
                conn.close()
                cols = ["job_id","job_type","payload","status","attempts","max_attempts","created_at","updated_at","result","error"]
                for row in rows:
                    job = dict(zip(cols, row))
                    try: job["payload"] = json.loads(job["payload"])
                    except: pass
                    _process_one(job)
            except Exception: pass
            time.sleep(poll_interval)
    _worker_thread = threading.Thread(target=loop, daemon=True, name="apex-worker")
    _worker_thread.start()

def stop_worker():
    global _worker_running
    _worker_running = False
