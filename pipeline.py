"""
pipeline.py — APEX
End-to-end pipeline: script → images → voice → video → thumbnail → quality check → preview → approve → publish.
"""

import os, json
from datetime import datetime
from pathlib import Path
import job_queue, audit_log, approval, quality_check
import apex_agent, image_engine, video_builder, thumbnail_gen, rights_ledger, preview as pv, publisher

BASE_DIR = Path(__file__).parent

@job_queue.register("generate_episode")
def handle_generate_episode(payload: dict) -> dict:
    topic             = payload.get("topic","Trishul has a plan")
    ep_num            = payload.get("episode_num",1)
    enhancement_hints = payload.get("enhancement_hints","")

    print(f"\n[PIPELINE] Episode {ep_num}: {topic}")

    script = apex_agent.write_script(topic, ep_num, enhancement_hints)
    episode_id = script["episode_id"]
    print(f"[PIPELINE] Script: {script['title']}")

    img_paths = []
    for scene in script["scenes"]:
        r = image_engine.generate(scene["image_prompt"], f"{episode_id}_{scene['id']}")
        img_paths.append(r["path"])

    try:
        from thumbnail_gen import generate as gen_thumb
        thumb = gen_thumb(episode_id, script["title"],
                          script.get("thumbnail_concept","cartoon comedy scene"),
                          script.get("thumbnail_text",""))
        thumb_path = thumb["path"]
    except Exception:
        thumb_path = ""

    audio_paths = [str(BASE_DIR/"audio_cache"/f"{episode_id}_{s['id']}.mp3") for s in script["scenes"]]
    rights_ledger.auto_register_episode_assets(script, img_paths, audio_paths)

    render_result = video_builder.render(script)
    if not render_result["ok"]:
        raise RuntimeError(f"Render failed: {render_result.get('error','unknown')}")

    video_path  = render_result["path"]
    img_paths   = render_result.get("img_paths", [])
    audio_paths = render_result.get("audio_paths", [])

    # ── GAP 2 FIX: Quality gate in pipeline ───────────────────
    qc_result = quality_check.run(script, video_path, img_paths, audio_paths)
    if not qc_result["passed"]:
        issues = "; ".join(qc_result.get("issues", [])[:3])
        raise RuntimeError(f"Quality check failed ({qc_result['overall_score']:.0%}): {issues}")

    preview_result = pv.build_preview_card(script, video_path, thumb_path)
    if not preview_result["ok"]:
        raise RuntimeError(f"Preview blocked: {preview_result.get('reason','unknown')}")

    card_id = preview_result["card_id"]
    print(f"[PIPELINE] Ready — approval card: {card_id}")
    return {"episode_id":episode_id,"title":script["title"],"video_path":video_path,
            "thumb_path":thumb_path,"card_id":card_id,"status":"awaiting_approval"}

@job_queue.register("publish_episode")
def handle_publish_episode(payload: dict) -> dict:
    card_id = payload.get("card_id","")
    dry_run = payload.get("dry_run",False)
    if not card_id: raise ValueError("card_id required")
    result = publisher.upload(card_id, dry_run=dry_run)
    if result["ok"] and not dry_run:
        card = approval.get_card(card_id)
        if card:
            p = card["payload"]
            publisher.draft_community_post(
                p.get("episode_id",""), result["youtube_id"],
                p.get("title",""), "Watch what happens when Trishul's plan goes wrong! 😂")
    return result


@job_queue.register("publish_community_post")
def handle_community_post_pipeline(payload: dict) -> dict:
    """Community post publish — forwarded from approval."""
    post_payload = payload.get("payload", {})
    youtube_id   = post_payload.get("youtube_id", "")
    text         = post_payload.get("text", "")
    episode_id   = post_payload.get("episode_id", "")
    if not text: return {"ok": False, "reason": "No post text"}
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        token_path = BASE_DIR / "youtube_token.json"
        if not token_path.exists():
            return {"ok": False, "reason": "YouTube OAuth not configured"}
        creds   = Credentials.from_authorized_user_file(str(token_path))
        youtube = build("youtube","v3",credentials=creds)
        youtube.commentThreads().insert(
            part="snippet",
            body={"snippet":{"videoId":youtube_id,
                  "topLevelComment":{"snippet":{"textOriginal":text[:9999]}}}}
        ).execute()
        audit_log.record("VIDEO_UPLOADED",subject=episode_id,
                         payload={"type":"community_post","youtube_id":youtube_id})
        return {"ok":True,"youtube_id":youtube_id}
    except Exception as e:
        return {"ok":False,"reason":str(e)}

def queue_episode(topic: str, episode_num: int, plan_id: str = "", enhancement_hints: str = "") -> str:
    return job_queue.enqueue("generate_episode",
        {"topic":topic,"episode_num":episode_num,"plan_id":plan_id,"enhancement_hints":enhancement_hints},
        job_id=f"ep-{episode_num}-{topic[:20].replace(' ','-')}")

def queue_publish(card_id: str, dry_run: bool = False) -> str:
    return job_queue.enqueue("publish_episode", {"card_id":card_id,"dry_run":dry_run})

def status() -> dict:
    return {
        "jobs": {
            "pending": len(job_queue.list_jobs(status="pending")),
            "running": len(job_queue.list_jobs(status="running")),
            "done":    len(job_queue.list_jobs(status="done")),
            "dead":    len(job_queue.list_dead_letter()),
        },
        "approval_cards_pending": len(approval.pending_cards()),
        "videos_published":       len(publisher.list_published()),
        "image_usage":            image_engine.usage_report(),
        "scripts_written":        apex_agent.get_episode_count(),
        "audit_summary":          audit_log.summary(),
        "as_of":                  datetime.utcnow().isoformat(),
    }

def start(poll_interval: float = 2.0):
    job_queue.start_worker(poll_interval=poll_interval)
    print("[PIPELINE] Worker started")

def stop():
    job_queue.stop_worker()
