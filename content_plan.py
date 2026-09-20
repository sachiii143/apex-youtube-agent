"""
content_plan.py — APEX Phase 2
Research brief → content plan → episode queue.
"""

import json, uuid, sqlite3
from datetime import datetime
from pathlib import Path
import audit_log, job_queue

DB_PATH   = Path(__file__).parent / "apex_data.db"
PLANS_DIR = Path(__file__).parent / "plans"
PLANS_DIR.mkdir(exist_ok=True)

def _conn():
    conn=sqlite3.connect(DB_PATH,check_same_thread=False); conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS content_plans (
        plan_id TEXT PRIMARY KEY, brief_id TEXT, topic TEXT NOT NULL,
        strategy TEXT NOT NULL, episodes TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL,
        approved_at TEXT, notes TEXT
    )""")
    conn.commit(); return conn

def create_from_brief(brief:dict, episode_count:int=5) -> dict:
    plan_id=str(uuid.uuid4())[:12]; topic=brief.get("topic",""); scored=brief.get("scored_ideas",[])
    top_idea=(brief.get("top_idea") or {}).get("idea",topic)
    episodes=[]; seen=set()
    for idea in scored[:episode_count]:
        if idea["idea"] in seen: continue
        seen.add(idea["idea"])
        episodes.append({"episode_num":len(episodes)+1,"topic":idea["idea"],"score":idea["composite"],
                         "recommendation":idea["recommendation"],"status":"queued","job_id":None,"script_id":None})
    while len(episodes)<episode_count:
        n=len(episodes)+1
        episodes.append({"episode_num":n,"topic":f"{top_idea} — Part {n}","score":0.4,
                         "recommendation":"RESEARCH MORE","status":"queued","job_id":None,"script_id":None})
    strategy={"goal":f"5-10 comedy sketch videos/day about {topic}","target_audience":"Kids and young adults, family safe",
               "format":"Original comedy sketches — Trishul, Sandy, Libhu","posting_cadence":"1 video per day minimum",
               "evidence_basis":f"{brief['evidence']['total_sources']} sources from research brief {brief['brief_id']}",
               "disclaimer":"Strategy based on observed research. No guaranteed outcome."}
    plan={"plan_id":plan_id,"brief_id":brief.get("brief_id",""),"topic":topic,"strategy":strategy,
          "episodes":episodes,"status":"draft","created_at":datetime.utcnow().isoformat()}
    (PLANS_DIR/f"plan_{plan_id}.json").write_text(json.dumps(plan,indent=2,ensure_ascii=False))
    conn=_conn()
    conn.execute("INSERT INTO content_plans (plan_id,brief_id,topic,strategy,episodes,status,created_at) VALUES (?,?,?,?,?,?,?)",
                 (plan_id,brief.get("brief_id",""),topic,json.dumps(strategy),json.dumps(episodes),"draft",datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    audit_log.record("RESEARCH_DONE",subject=plan_id,payload={"topic":topic,"episodes":len(episodes)})
    return plan

def approve_plan(plan_id:str) -> bool:
    conn=_conn(); row=conn.execute("SELECT episodes,topic FROM content_plans WHERE plan_id=?",(plan_id,)).fetchone()
    if not row: conn.close(); return False
    episodes=json.loads(row[0])
    for ep in episodes:
        jid=job_queue.enqueue("generate_episode",{"topic":ep["topic"],"episode_num":ep["episode_num"],"plan_id":plan_id},
                              job_id=f"plan-{plan_id}-ep-{ep['episode_num']}")
        ep["job_id"]=jid; ep["status"]="enqueued"
    conn.execute("UPDATE content_plans SET status='approved',approved_at=?,episodes=? WHERE plan_id=?",
                 (datetime.utcnow().isoformat(),json.dumps(episodes),plan_id))
    conn.commit(); conn.close()
    path=PLANS_DIR/f"plan_{plan_id}.json"
    if path.exists():
        data=json.loads(path.read_text()); data["episodes"]=episodes; data["status"]="approved"
        path.write_text(json.dumps(data,indent=2))
    audit_log.record("VIDEO_APPROVED",subject=plan_id,payload={"episodes_queued":len(episodes)})
    return True

def get_plan(plan_id:str) -> dict | None:
    path=PLANS_DIR/f"plan_{plan_id}.json"; return json.loads(path.read_text()) if path.exists() else None

def list_plans() -> list:
    conn=_conn(); rows=conn.execute("SELECT plan_id,topic,status,created_at FROM content_plans ORDER BY created_at DESC").fetchall(); conn.close()
    return [{"plan_id":r[0],"topic":r[1],"status":r[2],"created_at":r[3]} for r in rows]

def update_episode_status(plan_id:str, episode_num:int, status:str, script_id:str=None):
    conn=_conn(); row=conn.execute("SELECT episodes FROM content_plans WHERE plan_id=?",(plan_id,)).fetchone()
    if not row: conn.close(); return
    episodes=json.loads(row[0])
    for ep in episodes:
        if ep["episode_num"]==episode_num:
            ep["status"]=status
            if script_id: ep["script_id"]=script_id
    conn.execute("UPDATE content_plans SET episodes=? WHERE plan_id=?",(json.dumps(episodes),plan_id))
    conn.commit(); conn.close()
