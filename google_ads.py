"""
google_ads.py — APEX Phase 6
Google Ads — read-only by default. No auto-spend. Every change needs approval.
"""

import os, json, sqlite3
from datetime import datetime
from pathlib import Path
import audit_log, approval

DB_PATH = Path(__file__).parent / "apex_data.db"
ADS_DIR = Path(__file__).parent / "ads"
ADS_DIR.mkdir(exist_ok=True)

DAILY_SPEND_CAP_USD    = 10.0
CAMPAIGN_SPEND_CAP_USD = 50.0

def _conn():
    conn=sqlite3.connect(DB_PATH,check_same_thread=False); conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS ads_campaigns (
        campaign_id TEXT PRIMARY KEY, name TEXT, status TEXT,
        budget_daily REAL, spend_today REAL DEFAULT 0,
        impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0,
        conversions REAL DEFAULT 0, fetched_at TEXT, evidence_type TEXT DEFAULT 'observed'
    )""")
    conn.commit(); return conn

def get_cached_campaigns() -> list:
    conn=_conn(); rows=conn.execute("SELECT * FROM ads_campaigns ORDER BY fetched_at DESC").fetchall(); conn.close()
    cols=["campaign_id","name","status","budget_daily","spend_today","impressions","clicks","conversions","fetched_at","evidence_type"]
    return [dict(zip(cols,r)) for r in rows]

def fetch_campaigns(customer_id:str=None) -> list:
    cid=customer_id or os.environ.get("GOOGLE_ADS_CUSTOMER_ID","")
    if not cid: return [{"error":"GOOGLE_ADS_CUSTOMER_ID not set","howto":"Set in Settings → API Keys"}]
    try:
        from google.ads.googleads.client import GoogleAdsClient
        client=GoogleAdsClient.load_from_env(); ga=client.get_service("GoogleAdsService")
        query="SELECT campaign.id,campaign.name,campaign.status,campaign_budget.amount_micros,metrics.impressions,metrics.clicks,metrics.conversions,metrics.cost_micros FROM campaign WHERE segments.date DURING LAST_7_DAYS ORDER BY metrics.cost_micros DESC LIMIT 20"
        response=ga.search_stream(customer_id=cid,query=query)
        campaigns=[]; conn=_conn()
        for batch in response:
            for row in batch.results:
                c=row.campaign; m=row.metrics; b=row.campaign_budget
                camp={"campaign_id":str(c.id),"name":c.name,"status":c.status.name,
                      "budget_daily":round(b.amount_micros/1_000_000,2),"spend_7d":round(m.cost_micros/1_000_000,2),
                      "impressions":m.impressions,"clicks":m.clicks,"conversions":round(m.conversions,2),
                      "ctr":round(m.clicks/max(m.impressions,1)*100,2),"fetched_at":datetime.utcnow().isoformat(),"evidence_type":"observed"}
                campaigns.append(camp)
                conn.execute("INSERT OR REPLACE INTO ads_campaigns (campaign_id,name,status,budget_daily,impressions,clicks,conversions,fetched_at,evidence_type) VALUES (?,?,?,?,?,?,?,?,?)",
                             (camp["campaign_id"],camp["name"],camp["status"],camp["budget_daily"],camp["impressions"],camp["clicks"],camp["conversions"],camp["fetched_at"],"observed"))
        conn.commit(); conn.close()
        audit_log.record("ADS_READ",subject=cid,payload={"campaigns":len(campaigns)})
        return campaigns
    except ImportError: return [{"error":"google-ads not installed. Run: pip install google-ads"}]
    except Exception as e: return [{"error":str(e)}]

def draft_campaign(name:str, daily_budget_usd:float, keywords:list, ad_text:str, target_video_id:str="") -> dict:
    if daily_budget_usd>DAILY_SPEND_CAP_USD:
        return {"ok":False,"reason":f"Budget ${daily_budget_usd}/day exceeds cap ${DAILY_SPEND_CAP_USD}/day"}
    draft={"type":"campaign_draft","name":name,"daily_budget_usd":daily_budget_usd,
           "keywords":keywords,"ad_text":ad_text[:150],"target_video_id":target_video_id,
           "status":"PAUSED","created_at":datetime.utcnow().isoformat(),
           "spend_cap_daily":DAILY_SPEND_CAP_USD,"spend_cap_campaign":CAMPAIGN_SPEND_CAP_USD}
    ts=datetime.utcnow().strftime("%Y%m%d_%H%M")
    (ADS_DIR/f"draft_{name[:20].replace(' ','_')}_{ts}.json").write_text(json.dumps(draft,indent=2))
    card_payload={"action":"CREATE_CAMPAIGN","name":name,"daily_budget_usd":daily_budget_usd,
                  "keywords":keywords[:10],"ad_text":ad_text[:150],"spend_cap_daily":DAILY_SPEND_CAP_USD}
    card_id=approval.issue("ADS_CAMPAIGN_LAUNCH",card_payload,ttl_hours=48)
    audit_log.record("ADS_DRAFT_CREATED",subject=name,payload={"budget":daily_budget_usd,"keywords":len(keywords)})
    return {"ok":True,"draft":draft,"card_id":card_id,"message":f"Campaign drafted. Needs approval (card:{card_id[:8]}). Budget:${daily_budget_usd}/day"}

def list_drafts() -> list:
    drafts=[]
    for p in sorted(ADS_DIR.glob("draft_*.json"),reverse=True):
        try: drafts.append(json.loads(p.read_text()))
        except Exception: pass
    return drafts

def ads_summary() -> dict:
    campaigns=get_cached_campaigns()
    if not campaigns: return {"status":"no_data","message":"No campaign data yet. Connect Google Ads in Settings."}
    return {"campaigns":len(campaigns),"total_spend_7d":round(sum(c.get("spend_today",0) for c in campaigns),2),
            "total_clicks":sum(c.get("clicks",0) for c in campaigns),
            "total_impressions":sum(c.get("impressions",0) for c in campaigns),
            "spend_cap_daily":DAILY_SPEND_CAP_USD,"evidence_type":"observed",
            "disclaimer":"Read-only data. No spend without explicit approval."}
