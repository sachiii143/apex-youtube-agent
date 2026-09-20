"""
scheduler.py — APEX
Daily auto-scheduler. Requires owner approval before activating.
Uses enhancement engine to improve each video.
"""

import json, sqlite3, threading, time, uuid
from datetime import datetime, timedelta
from pathlib import Path
import audit_log, job_queue

DB_PATH   = Path(__file__).parent / "apex_data.db"
_running  = False
_thread   = None

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS schedules (
        schedule_id  TEXT PRIMARY KEY, name TEXT NOT NULL, topic_pool TEXT NOT NULL,
        time_of_day  TEXT NOT NULL DEFAULT '09:00',
        days_of_week TEXT NOT NULL DEFAULT 'mon,tue,wed,thu,fri,sat,sun',
        active INTEGER NOT NULL DEFAULT 0, approved INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, last_run_at TEXT, next_run_at TEXT,
        run_count INTEGER NOT NULL DEFAULT 0, use_enhancement INTEGER NOT NULL DEFAULT 1
    )""")
    conn.commit()
    return conn

def create_schedule(name, topic_pool, time_of_day="09:00",
                    days_of_week="mon,tue,wed,thu,fri,sat,sun",
                    use_enhancement=True) -> str:
    sid  = str(uuid.uuid4())[:12]
    now  = datetime.utcnow().isoformat()
    next_run = _next_run_time(time_of_day, days_of_week)
    conn = _conn()
    conn.execute("""INSERT INTO schedules
        (schedule_id,name,topic_pool,time_of_day,days_of_week,active,approved,created_at,next_run_at,use_enhancement)
        VALUES (?,?,?,?,?,0,0,?,?,?)""",
        (sid,name,json.dumps(topic_pool),time_of_day,days_of_week,now,next_run,1 if use_enhancement else 0))
    conn.commit(); conn.close()
    audit_log.record("RESEARCH_STARTED",subject=sid,payload={"name":name,"time":time_of_day,"topics":len(topic_pool)})
    return sid

def approve_schedule(sid: str) -> bool:
    conn = _conn()
    conn.execute("UPDATE schedules SET approved=1,active=1 WHERE schedule_id=?",(sid,))
    conn.commit(); conn.close()
    audit_log.record("VIDEO_APPROVED",subject=sid,payload={"action":"schedule_approved"})
    return True

def pause_schedule(sid: str) -> bool:
    conn = _conn(); conn.execute("UPDATE schedules SET active=0 WHERE schedule_id=?",(sid,)); conn.commit(); conn.close(); return True

def resume_schedule(sid: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT approved FROM schedules WHERE schedule_id=?",(sid,)).fetchone()
    if row and row[0]: conn.execute("UPDATE schedules SET active=1 WHERE schedule_id=?",(sid,)); conn.commit()
    conn.close(); return bool(row and row[0])

def get_schedule(sid: str) -> dict | None:
    conn = _conn(); row = conn.execute("SELECT * FROM schedules WHERE schedule_id=?",(sid,)).fetchone(); conn.close()
    if not row: return None
    cols = ["schedule_id","name","topic_pool","time_of_day","days_of_week","active","approved",
            "created_at","last_run_at","next_run_at","run_count","use_enhancement"]
    d = dict(zip(cols,row)); d["topic_pool"] = json.loads(d["topic_pool"]); return d

def list_schedules() -> list:
    conn = _conn(); rows = conn.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall(); conn.close()
    cols = ["schedule_id","name","topic_pool","time_of_day","days_of_week","active","approved",
            "created_at","last_run_at","next_run_at","run_count","use_enhancement"]
    result = []
    for row in rows:
        d = dict(zip(cols,row)); d["topic_pool"]=json.loads(d["topic_pool"]); result.append(d)
    return result

def _next_run_time(time_of_day: str, days_of_week: str) -> str:
    day_map = {"mon":0,"tue":1,"wed":2,"thu":3,"fri":4,"sat":5,"sun":6}
    allowed = {day_map[d.strip()] for d in days_of_week.lower().split(",") if d.strip() in day_map}
    if not allowed: allowed = set(range(7))
    try: h,m = map(int,time_of_day.split(":")); 
    except Exception: h,m = 9,0
    now = datetime.utcnow()
    for days_ahead in range(8):
        candidate = (now+timedelta(days=days_ahead)).replace(hour=h,minute=m,second=0,microsecond=0)
        if candidate.weekday() in allowed and candidate > now:
            return candidate.isoformat()
    return (now+timedelta(days=1)).replace(hour=h,minute=m,second=0,microsecond=0).isoformat()

def _fire_schedule(conn, sched: dict, now: datetime):
    pool    = sched["topic_pool"]; run_count = sched["run_count"]
    topic   = pool[run_count % len(pool)]; ep_num = run_count+1; sid = sched["schedule_id"]
    enhancement_hints = ""
    if sched["use_enhancement"]:
        try:
            from analytics import list_tracked_videos
            from enhancement_engine import build_enhancement_brief
            vids = [v["youtube_id"] for v in list_tracked_videos()[:5]]
            if vids: brief = build_enhancement_brief(vids,next_topic=topic); enhancement_hints=brief.get("prompt_additions","")
        except Exception: pass
    job_id = job_queue.enqueue("generate_episode",
        {"topic":topic,"episode_num":ep_num,"schedule_id":sid,"enhancement_hints":enhancement_hints},
        job_id=f"sched-{sid}-ep-{ep_num}")
    next_run = _next_run_time(sched["time_of_day"],sched["days_of_week"])
    conn.execute("UPDATE schedules SET last_run_at=?,next_run_at=?,run_count=run_count+1 WHERE schedule_id=?",
                 (now.isoformat(),next_run,sid))
    conn.commit()
    audit_log.record("VIDEO_QUEUED",subject=job_id,payload={"schedule":sched["name"],"topic":topic,"episode_num":ep_num})
    print(f"[SCHEDULER] Queued ep {ep_num}: {topic} — next: {next_run}")

def _loop():
    while _running:
        try:
            conn = _conn(); now = datetime.utcnow()
            rows = conn.execute("SELECT * FROM schedules WHERE active=1 AND approved=1").fetchall()
            cols = ["schedule_id","name","topic_pool","time_of_day","days_of_week","active","approved",
                    "created_at","last_run_at","next_run_at","run_count","use_enhancement"]
            for row in rows:
                sched = dict(zip(cols,row)); sched["topic_pool"]=json.loads(sched["topic_pool"])
                next_run = sched.get("next_run_at","")
                if next_run and datetime.fromisoformat(next_run) <= now:
                    _fire_schedule(conn,sched,now)
            conn.close()
        except Exception: pass
        time.sleep(60)

def start_scheduler():
    global _running, _thread
    if _running: return
    _running = True
    _thread  = threading.Thread(target=_loop,daemon=True,name="apex-scheduler")
    _thread.start()
    print("[SCHEDULER] Started")

def stop_scheduler():
    global _running; _running = False
