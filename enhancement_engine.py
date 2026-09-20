"""
enhancement_engine.py — APEX
Uses real analytics to improve next video. Evidence-based only.
"""

import json, sqlite3
from datetime import datetime
from pathlib import Path
import audit_log

DB_PATH = Path(__file__).parent / "apex_data.db"

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def analyse_performance(youtube_ids: list) -> dict:
    if not youtube_ids:
        return {"error":"No videos to analyse","recommendations":[],
                "disclaimer":"No guaranteed outcome."}
    conn = _conn()
    metrics = {}
    phs = ",".join("?"*len(youtube_ids))
    for metric in ["views","avg_retention_pct","ctr","watch_minutes","likes"]:
        row = conn.execute(
            f"SELECT AVG(value),MAX(value),MIN(value),COUNT(*) FROM video_analytics WHERE youtube_id IN ({phs}) AND metric=?",
            youtube_ids+[metric]).fetchone()
        if row and row[3]>0:
            metrics[metric] = {"avg":round(float(row[0] or 0),2),"max":round(float(row[1] or 0),2),
                               "min":round(float(row[2] or 0),2),"n":row[3],"evidence_type":"observed"}
    conn.close()
    return {"videos_analysed":len(youtube_ids),"metrics":metrics,
            "recommendations":_generate_recommendations(metrics),
            "analysed_at":datetime.utcnow().isoformat(),
            "disclaimer":"Recommendations based on observed data. No guaranteed improvement."}

def _generate_recommendations(metrics: dict) -> list:
    recs = []
    ctr = metrics.get("ctr",{}); ret = metrics.get("avg_retention_pct",{}); views = metrics.get("views",{})
    if ctr.get("avg",0)<3.0 and ctr.get("n",0)>0:
        recs.append({"area":"Thumbnail/Title","recommendation":"CTR below 3% — try stronger emotion in thumbnail, add number or question to title",
                     "evidence":f"Observed avg CTR: {ctr['avg']}%","evidence_type":"observed","priority":"high"})
    if ret.get("avg",0)<40.0 and ret.get("n",0)>0:
        recs.append({"area":"Script pacing","recommendation":"Retention below 40% — shorten scenes, add comedy beat faster in scene 1",
                     "evidence":f"Observed avg retention: {ret['avg']}%","evidence_type":"observed","priority":"high"})
    if views.get("avg",0)<100 and views.get("n",0)>=3:
        recs.append({"area":"SEO/Discovery","recommendation":"Low views — research trending topics before next script, improve tags",
                     "evidence":f"Observed avg views: {views['avg']} across {views['n']} videos","evidence_type":"observed","priority":"high"})
    if not recs:
        recs.append({"area":"General","recommendation":"Not enough data yet — keep publishing daily","evidence":"Fewer than 3 videos","evidence_type":"observed","priority":"low"})
    return recs

def build_enhancement_brief(youtube_ids: list, next_topic: str = "") -> dict:
    analysis = analyse_performance(youtube_ids)
    recs     = analysis.get("recommendations",[])
    hints    = ["ENHANCEMENT INSTRUCTIONS (based on observed analytics):"]
    for r in recs:
        if r["priority"] in ("high","medium"):
            hints.append(f"  [{r['area'].upper()}] {r['recommendation']}")
    if len(hints)==1: hints.append("  Performance is good — maintain current approach")
    brief = {"type":"enhancement_brief","based_on_videos":youtube_ids,"next_topic":next_topic,
             "performance":analysis,"prompt_additions":"\n".join(hints),
             "created_at":datetime.utcnow().isoformat(),
             "disclaimer":"Enhancement based on observed data. No guaranteed outcome."}
    out = Path(__file__).parent/"analytics"/f"enhancement_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
    out.write_text(json.dumps(brief,indent=2))
    audit_log.record("RESEARCH_DONE",subject="enhancement_brief",payload={"videos":len(youtube_ids),"recs":len(recs)})
    return brief

def _build_prompt_additions(recs: list) -> str:
    lines = ["ENHANCEMENT INSTRUCTIONS (based on observed analytics):"]
    high  = [r for r in recs if r["priority"]=="high"]
    for r in high: lines.append(f"  [{r['area'].upper()}] {r['recommendation']}")
    if not high: lines.append("  Performance is good — maintain current approach")
    return "\n".join(lines)
