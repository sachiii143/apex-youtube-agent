"""
publisher.py — APEX
YouTube upload with mandatory approval gate.
No upload without valid, unexpired, payload-locked card.
"""

import os, json, time
from datetime import datetime
from pathlib import Path
import approval, audit_log

BASE_DIR    = Path(__file__).parent
PUBLISH_DIR = BASE_DIR / "published"
PUBLISH_DIR.mkdir(exist_ok=True)

def upload(card_id: str, dry_run: bool = False) -> dict:
    card = approval.get_card(card_id)
    if not card: return _fail(card_id,"Card not found")
    payload = card["payload"]
    check   = approval.check(card_id, payload)
    if not check["ok"]: return _fail(card_id, check["reason"])
    for field in ["title","video_path","episode_id"]:
        if not payload.get(field): return _fail(card_id,f"Missing field: {field}")
    if not os.path.exists(payload["video_path"]): return _fail(card_id,f"Video not found: {payload['video_path']}")

    episode_id = payload["episode_id"]; title = payload["title"]

    if dry_run:
        fake_id = f"dryrun_{episode_id}_{int(time.time())}"
        result  = _record(episode_id, card_id, fake_id, payload, dry_run=True)
        audit_log.record("VIDEO_UPLOADED",subject=episode_id,payload={"youtube_id":fake_id,"dry_run":True,"title":title})
        return result

    try:
        import upload_to_youtube as yt
        res = yt.upload(video_path=payload["video_path"],title=payload["title"],
                        description=payload.get("description",""),tags=payload.get("tags",[]),
                        privacy=payload.get("visibility","public"),made_for_kids=payload.get("made_for_kids",True))
        yt_id = res.get("id","")
        if not yt_id: raise ValueError("No video ID returned")
        if payload.get("thumbnail_path") and os.path.exists(payload["thumbnail_path"]):
            try: yt.set_thumbnail(yt_id, payload["thumbnail_path"])
            except Exception: pass
        result = _record(episode_id, card_id, yt_id, payload)
        audit_log.record("VIDEO_UPLOADED",subject=episode_id,payload={"youtube_id":yt_id,"title":title})
        return result
    except Exception as e:
        audit_log.record("VIDEO_REJECTED",subject=episode_id,payload={"reason":str(e)})
        return _fail(card_id,f"Upload error: {e}")

def _record(episode_id, card_id, yt_id, payload, dry_run=False) -> dict:
    now    = datetime.utcnow().isoformat()
    record = {"episode_id":episode_id,"youtube_id":yt_id,"card_id":card_id,
              "title":payload.get("title",""),"url":f"https://youtube.com/watch?v={yt_id}",
              "published_at":now,"dry_run":dry_run}
    (PUBLISH_DIR/f"{episode_id}_published.json").write_text(json.dumps(record,indent=2))

    # GAP 3 FIX: auto-register for analytics after every upload
    if not dry_run:
        try:
            import analytics as _an
            _an.register_video(yt_id, episode_id, payload.get("title",""), now)
        except Exception as _e:
            audit_log.record("RESEARCH_DONE", subject="analytics_register",
                             payload={"error": str(_e), "youtube_id": yt_id})

    return {"ok":True,"youtube_id":yt_id,"url":record["url"],"dry_run":dry_run}

def _fail(card_id, reason) -> dict:
    audit_log.record("VIDEO_REJECTED",subject=card_id,payload={"reason":reason})
    return {"ok":False,"reason":reason}

def draft_community_post(episode_id: str, youtube_id: str, title: str, hook: str) -> dict:
    post_text = (f"🎬 NEW EPISODE: {title}\n\n{hook}\n\n"
                 f"Watch now 👇\nhttps://youtube.com/watch?v={youtube_id}\n\n"
                 f"#SunridgeTown #Trishul #Sandy #Libhu #cartoon #comedy #kids")
    card_payload = {"type":"community_post","episode_id":episode_id,"youtube_id":youtube_id,"text":post_text}
    card_id = approval.issue("COMMUNITY_POST", card_payload, ttl_hours=48)
    draft   = {"type":"community_post","episode_id":episode_id,"youtube_id":youtube_id,
               "text":post_text,"status":"draft","created_at":datetime.utcnow().isoformat(),"card_id":card_id}
    (PUBLISH_DIR/f"{episode_id}_community_draft.json").write_text(json.dumps(draft,indent=2))
    audit_log.record("APPROVAL_ISSUED",subject=episode_id,payload={"type":"community_post","card_id":card_id})
    return {"ok":True,"draft":draft,"card_id":card_id}

def list_published() -> list:
    return [json.loads(p.read_text()) for p in sorted(PUBLISH_DIR.glob("*_published.json"),reverse=True) if p.exists()]

def list_community_drafts() -> list:
    return [json.loads(p.read_text()) for p in sorted(PUBLISH_DIR.glob("*_community_draft.json"),reverse=True) if p.exists()]

def get_publish_record(episode_id: str) -> dict | None:
    path = PUBLISH_DIR/f"{episode_id}_published.json"
    return json.loads(path.read_text()) if path.exists() else None
