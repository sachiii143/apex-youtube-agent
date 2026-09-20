"""
analytics.py — APEX Phase 5
YouTube Analytics — real observed metrics only.
"""

import os, json, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import audit_log

DB_PATH       = Path(__file__).parent / "apex_data.db"
ANALYTICS_DIR = Path(__file__).parent / "analytics"
ANALYTICS_DIR.mkdir(exist_ok=True)

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS video_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, youtube_id TEXT NOT NULL,
        episode_id TEXT, metric TEXT NOT NULL, value REAL NOT NULL,
        period_start TEXT NOT NULL, period_end TEXT NOT NULL,
        fetched_at TEXT NOT NULL, evidence_type TEXT NOT NULL DEFAULT 'observed'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS video_registry (
        youtube_id TEXT PRIMARY KEY, episode_id TEXT, title TEXT,
        published_at TEXT, url TEXT, registered_at TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def fetch_video_metrics(youtube_id: str, days_back: int = 28) -> dict:
    token_path = Path(__file__).parent / "youtube_token.json"
    if not token_path.exists():
        return {"youtube_id":youtube_id,"error":"YouTube Analytics OAuth not configured",
                "howto":"Run: python upload_to_youtube.py --setup",
                "evidence_type":"none","freshness":datetime.utcnow().isoformat()}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds      = Credentials.from_authorized_user_file(str(token_path))
        analytics  = build("youtubeAnalytics","v2",credentials=creds)
        end_date   = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow()-timedelta(days=days_back)).strftime("%Y-%m-%d")
        resp = analytics.reports().query(
            ids="channel==MINE",startDate=start_date,endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,comments,shares,subscribersGained",
            filters=f"video=={youtube_id}",dimensions="video").execute()
        rows = resp.get("rows",[])
        if not rows: return {"youtube_id":youtube_id,"error":"No data yet","freshness":datetime.utcnow().isoformat()}
        cols = [c["name"] for c in resp.get("columnHeaders",[])]
        data = dict(zip(cols,rows[0]))
        metrics = {"youtube_id":youtube_id,"period_start":start_date,"period_end":end_date,
                   "fetched_at":datetime.utcnow().isoformat(),"evidence_type":"observed",
                   "views":int(data.get("views",0)),"watch_minutes":round(float(data.get("estimatedMinutesWatched",0)),1),
                   "avg_view_duration_s":round(float(data.get("averageViewDuration",0)),1),
                   "avg_retention_pct":round(float(data.get("averageViewPercentage",0)),1),
                   "likes":int(data.get("likes",0)),"comments":int(data.get("comments",0)),
                   "shares":int(data.get("shares",0)),"subs_gained":int(data.get("subscribersGained",0)),
                   "ctr":0.0,"card_ctr":0.0,
                   "disclaimer":"All metrics observed from YouTube Analytics API."}
        _save_metrics(youtube_id, metrics)
        (ANALYTICS_DIR/f"{youtube_id}_{end_date}.json").write_text(json.dumps(metrics,indent=2))
        audit_log.record("RESEARCH_DONE",subject=youtube_id,
                         payload={"type":"analytics","views":metrics["views"]})
        return metrics
    except Exception as e:
        return {"error":str(e),"youtube_id":youtube_id,"freshness":datetime.utcnow().isoformat()}

def _save_metrics(youtube_id: str, metrics: dict):
    conn = _conn(); now = datetime.utcnow().isoformat()
    for key in ["views","watch_minutes","avg_view_duration_s","avg_retention_pct",
                "likes","comments","shares","subs_gained","ctr","card_ctr"]:
        if key in metrics:
            conn.execute("""INSERT INTO video_analytics
                (youtube_id,metric,value,period_start,period_end,fetched_at,evidence_type)
                VALUES (?,?,?,?,?,?,?)""",
                (youtube_id,key,float(metrics[key]),metrics.get("period_start",""),
                 metrics.get("period_end",""),now,"observed"))
    conn.commit(); conn.close()

def register_video(youtube_id: str, episode_id: str, title: str, published_at: str):
    conn = _conn()
    conn.execute("""INSERT OR REPLACE INTO video_registry
        (youtube_id,episode_id,title,published_at,url,registered_at) VALUES (?,?,?,?,?,?)""",
        (youtube_id,episode_id,title,published_at,f"https://youtube.com/watch?v={youtube_id}",
         datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

def list_tracked_videos() -> list:
    conn = _conn()
    rows = conn.execute("SELECT * FROM video_registry ORDER BY published_at DESC").fetchall()
    conn.close()
    cols = ["youtube_id","episode_id","title","published_at","url","registered_at"]
    return [dict(zip(cols,r)) for r in rows]

def get_metrics_history(youtube_id: str) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT metric,value,period_start,period_end,fetched_at FROM video_analytics WHERE youtube_id=? ORDER BY fetched_at DESC LIMIT 200",
        (youtube_id,)).fetchall()
    conn.close()
    cols = ["metric","value","period_start","period_end","fetched_at"]
    return [dict(zip(cols,r)) for r in rows]

def channel_summary() -> dict:
    conn = _conn()
    videos  = conn.execute("SELECT COUNT(*) FROM video_registry").fetchone()[0]
    total_v = conn.execute("SELECT SUM(value) FROM video_analytics WHERE metric='views'").fetchone()[0] or 0
    total_w = conn.execute("SELECT SUM(value) FROM video_analytics WHERE metric='watch_minutes'").fetchone()[0] or 0
    avg_ctr = conn.execute("SELECT AVG(value) FROM video_analytics WHERE metric='ctr' AND value>0").fetchone()[0] or 0
    avg_ret = conn.execute("SELECT AVG(value) FROM video_analytics WHERE metric='avg_retention_pct' AND value>0").fetchone()[0] or 0
    conn.close()
    return {"videos_tracked":videos,"total_views":int(total_v),"total_watch_min":round(float(total_w),1),
            "avg_ctr_pct":round(float(avg_ctr),2),"avg_retention_pct":round(float(avg_ret),2),
            "as_of":datetime.utcnow().isoformat(),"evidence_type":"observed",
            "disclaimer":"Aggregated from observed YouTube Analytics data only."}
