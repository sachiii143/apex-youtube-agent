"""
experiment_registry.py — APEX Phase 2
A/B experiment tracking with hypothesis, variants, guardrails, results.
"""

import json, uuid, sqlite3
from datetime import datetime
from pathlib import Path
import audit_log

DB_PATH = Path(__file__).parent / "apex_data.db"

def _conn():
    conn=sqlite3.connect(DB_PATH,check_same_thread=False); conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS experiments (
        exp_id TEXT PRIMARY KEY, name TEXT NOT NULL, hypothesis TEXT NOT NULL,
        metric TEXT NOT NULL, variants TEXT NOT NULL, guardrails TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'running', created_at TEXT NOT NULL,
        concluded_at TEXT, results TEXT, winner TEXT, conclusion TEXT
    )""")
    conn.commit(); return conn

def create(name:str, hypothesis:str, metric:str, variants:list, guardrails:list) -> str:
    exp_id=str(uuid.uuid4())[:12]; conn=_conn()
    conn.execute("INSERT INTO experiments (exp_id,name,hypothesis,metric,variants,guardrails,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                 (exp_id,name,hypothesis,metric,json.dumps(variants),json.dumps(guardrails),"running",datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    audit_log.record("RESEARCH_STARTED",subject=exp_id,payload={"name":name,"metric":metric,"variants":len(variants)})
    return exp_id

def log_result(exp_id:str, variant_name:str, observed_value:float, episode_id:str="", note:str="") -> bool:
    conn=_conn(); row=conn.execute("SELECT results FROM experiments WHERE exp_id=?",(exp_id,)).fetchone()
    if not row: conn.close(); return False
    results=json.loads(row[0] or "{}")
    if variant_name not in results: results[variant_name]=[]
    results[variant_name].append({"value":observed_value,"episode_id":episode_id,"note":note,
                                   "observed_at":datetime.utcnow().isoformat(),"type":"observed"})
    conn.execute("UPDATE experiments SET results=? WHERE exp_id=?",(json.dumps(results),exp_id))
    conn.commit(); conn.close(); return True

def conclude(exp_id:str, winner:str, conclusion:str) -> bool:
    conn=_conn()
    conn.execute("UPDATE experiments SET status='concluded',concluded_at=?,winner=?,conclusion=? WHERE exp_id=?",
                 (datetime.utcnow().isoformat(),winner,conclusion,exp_id))
    conn.commit(); conn.close()
    audit_log.record("RESEARCH_DONE",subject=exp_id,payload={"winner":winner})
    return True

def get(exp_id:str) -> dict | None:
    conn=_conn(); row=conn.execute("SELECT * FROM experiments WHERE exp_id=?",(exp_id,)).fetchone(); conn.close()
    if not row: return None
    cols=["exp_id","name","hypothesis","metric","variants","guardrails","status","created_at","concluded_at","results","winner","conclusion"]
    d=dict(zip(cols,row))
    for k in ("variants","guardrails","results"):
        if d[k]:
            try: d[k]=json.loads(d[k])
            except: d[k]=[] if k!="results" else {}
        else: d[k]=[] if k!="results" else {}
    return d

def list_experiments(status:str=None) -> list:
    conn=_conn()
    if status: rows=conn.execute("SELECT exp_id,name,metric,status,created_at,winner FROM experiments WHERE status=?",(status,)).fetchall()
    else: rows=conn.execute("SELECT exp_id,name,metric,status,created_at,winner FROM experiments").fetchall()
    conn.close()
    return [{"exp_id":r[0],"name":r[1],"metric":r[2],"status":r[3],"created_at":r[4],"winner":r[5]} for r in rows]

def summary(exp_id:str) -> dict:
    exp=get(exp_id)
    if not exp: return {"error":"Not found"}
    out={"exp_id":exp_id,"metric":exp["metric"],"variants":{}}
    for vname,readings in (exp.get("results") or {}).items():
        vals=[r["value"] for r in readings if isinstance(r.get("value"),(int,float))]
        if vals: out["variants"][vname]={"n":len(vals),"mean":round(sum(vals)/len(vals),4),"min":min(vals),"max":max(vals),"type":"observed"}
    if len(out["variants"])>1:
        best=max(out["variants"],key=lambda k:out["variants"][k]["mean"])
        out["leading_variant"]=best; out["note"]="Leading variant based on observed mean — not statistically guaranteed."
    return out
