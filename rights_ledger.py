"""
rights_ledger.py — APEX
Asset rights ledger: license, expiry, provenance for every asset.
Copyright scan gate — blocks publish if rights unclear.
"""

import sqlite3, json, uuid
from datetime import datetime
from pathlib import Path
import audit_log

DB_PATH = Path(__file__).parent / "apex_data.db"

BLOCKED_NAMES = [
    "ben 10","ben10","adventure time","finn the human","jake the dog",
    "regular show","mordecai","rigby","benson","gumball watterson",
    "steven universe","clarence","we bare bears","teen titans",
    "tom and jerry","scooby doo","bugs bunny","daffy duck",
    "mickey mouse","donald duck","spongebob","patrick star",
    "pikachu","pokemon","naruto","dragon ball",
]

def _conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS rights_ledger (
        asset_id    TEXT PRIMARY KEY,
        asset_type  TEXT NOT NULL,
        filename    TEXT NOT NULL,
        source      TEXT NOT NULL,
        license     TEXT NOT NULL,
        license_url TEXT,
        owner       TEXT NOT NULL,
        expiry_date TEXT,
        episode_id  TEXT,
        provenance  TEXT,
        cleared     INTEGER NOT NULL DEFAULT 0,
        created_at  TEXT NOT NULL
    )""")
    conn.commit()
    return conn

def register_asset(asset_type: str, filename: str, source: str,
                   license_name: str, license_url: str = "",
                   owner: str = "channel creator", expiry_date: str = None,
                   episode_id: str = "", provenance: str = "") -> str:
    asset_id = str(uuid.uuid4())[:12]
    cleared  = 1 if _is_cleared(license_name, source) else 0
    conn = _conn()
    conn.execute("""INSERT INTO rights_ledger
        (asset_id,asset_type,filename,source,license,license_url,owner,
         expiry_date,episode_id,provenance,cleared,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (asset_id,asset_type,filename,source,license_name,license_url,
         owner,expiry_date,episode_id,provenance,cleared,datetime.utcnow().isoformat()))
    conn.commit(); conn.close()
    return asset_id

def _is_cleared(license_name: str, source: str) -> bool:
    cleared = {"cc0","cc-0","public domain","original","channel creator",
               "pollinations-free","mit","apache-2.0","cc-by-4.0","cc-by-3.0",
               "free to use","youtube audio library","pixabay music license",
               "gtts generated narration","gtts-narration"}
    return license_name.lower() in cleared

def check_episode_rights(episode_id: str) -> dict:
    conn = _conn()
    rows = conn.execute(
        "SELECT asset_id,asset_type,filename,source,license,cleared FROM rights_ledger WHERE episode_id=?",
        (episode_id,)
    ).fetchall()
    conn.close()
    cleared_count = 0; uncleared = []
    for row in rows:
        asset_id,atype,fname,source,lic,cleared = row
        if cleared: cleared_count += 1
        else: uncleared.append({"asset_id":asset_id,"type":atype,"file":fname,"license":lic})
    return {"episode_id":episode_id,"total_assets":len(rows),"cleared":cleared_count,
            "uncleared":uncleared,"ok":len(uncleared)==0 and len(rows)>0,
            "checked_at":datetime.utcnow().isoformat()}

def scan_script_for_violations(script_text: str) -> list:
    violations = []
    lower = script_text.lower()
    for name in BLOCKED_NAMES:
        if name in lower:
            violations.append({"blocked_name":name,"reason":"Known copyrighted character/show name",
                               "action":"Remove or replace with original character"})
    return violations

def auto_register_episode_assets(script: dict, image_paths: list, audio_paths: list) -> list:
    episode_id = script.get("episode_id","")
    asset_ids  = []
    asset_ids.append(register_asset("script",f"{episode_id}_v1.json",
        "APEX AI — generated with Trishul/Sandy/Libhu original IP","Original",
        owner="channel creator",episode_id=episode_id,provenance="apex_agent.py write_script()"))
    for i, path in enumerate(image_paths):
        fname  = Path(path).name
        source = "Pollinations.ai"; lic = "Pollinations-free"
        if "placeholder" in fname.lower(): source = "APEX placeholder"; lic = "Original"
        asset_ids.append(register_asset("image",fname,source,lic,
            "https://pollinations.ai",owner="channel creator (generated)",
            episode_id=episode_id,provenance=f"image_engine.generate() scene {i+1}"))
    for i, path in enumerate(audio_paths):
        asset_ids.append(register_asset("audio",Path(path).name,
            "gTTS — Google Text-to-Speech","gTTS generated narration",
            owner="channel creator (generated)",episode_id=episode_id,
            provenance=f"video_builder._tts() scene {i+1}"))
    return asset_ids

def list_assets(episode_id: str = None) -> list:
    conn = _conn()
    if episode_id:
        rows = conn.execute("SELECT * FROM rights_ledger WHERE episode_id=? ORDER BY created_at",(episode_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM rights_ledger ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    cols = ["asset_id","asset_type","filename","source","license","license_url",
            "owner","expiry_date","episode_id","provenance","cleared","created_at"]
    return [dict(zip(cols,r)) for r in rows]
