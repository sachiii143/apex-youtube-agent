"""
preview.py — APEX
Human preview card — owner sees EXACT metadata before any upload.
Blocked if rights uncleared or copyright violation found.
"""

import json
from datetime import datetime
from pathlib import Path
import approval, rights_ledger, audit_log

PREVIEW_DIR = Path(__file__).parent / "previews"
PREVIEW_DIR.mkdir(exist_ok=True)

def build_preview_card(script: dict, video_path: str, thumbnail_path: str = "") -> dict:
    episode_id = script.get("episode_id","")
    rights = rights_ledger.check_episode_rights(episode_id)
    if rights["total_assets"] == 0:
        return {"ok":False,"reason":"No assets registered — run auto_register_episode_assets first","rights":rights}
    if not rights["ok"]:
        return {"ok":False,"reason":f"Rights check failed — {len(rights['uncleared'])} uncleared assets","rights":rights}

    full_text = " ".join(scene.get("narration","") for scene in script.get("scenes",[]))
    violations = rights_ledger.scan_script_for_violations(full_text)
    if violations:
        audit_log.record("VIDEO_REJECTED", subject=episode_id,
                         payload={"violations":[v["blocked_name"] for v in violations]})
        return {"ok":False,"reason":f"Copyright violations: {[v['blocked_name'] for v in violations]}",
                "violations":violations,"rights":rights}

    yt_metadata = {
        "title":         script.get("title","")[:100],
        "description":   _build_description(script),
        "tags":          script.get("tags",[])[:15],
        "category":      "22",
        "visibility":    "public",
        "made_for_kids": True,
        "language":      "en",
        "thumbnail":     thumbnail_path,
    }
    preview = {
        "episode_id":       episode_id,
        "created_at":       datetime.utcnow().isoformat(),
        "video_path":       video_path,
        "thumbnail_path":   thumbnail_path,
        "youtube_metadata": yt_metadata,
        "scenes_count":     len(script.get("scenes",[])),
        "script_version":   script.get("version",""),
        "rights_status":    rights,
        "disclaimer":       "Review every field. Once approved this card is payload-locked. Any change requires a new card.",
    }
    card_payload = {
        "episode_id":    episode_id,
        "title":         yt_metadata["title"],
        "description":   yt_metadata["description"],
        "tags":          yt_metadata["tags"],
        "video_path":    video_path,
        "thumbnail_path":thumbnail_path,
        "visibility":    yt_metadata["visibility"],
        "made_for_kids": yt_metadata["made_for_kids"],
    }
    card_id = approval.issue("YOUTUBE_UPLOAD", card_payload, ttl_hours=24)
    preview["card_id"] = card_id
    (PREVIEW_DIR/f"{episode_id}_preview.json").write_text(json.dumps(preview,indent=2))
    audit_log.record("APPROVAL_ISSUED",subject=episode_id,payload={"card_id":card_id,"title":yt_metadata["title"]})
    return {"ok":True,"preview":preview,"card_id":card_id}

def _build_description(script: dict) -> str:
    lines = [
        script.get("description",""),
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Meet the Sunridge Town crew:",
        "🦸 Trishul — always has a plan (always goes wrong)",
        "📓 Sandy — always right, nobody listens",
        "🍪 Libhu — wildcard genius",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "Original characters — 100% family safe comedy",
        "",
        "#cartoon #comedy #animation #kids #funny #original #sunridgetown",
        "#Trishul #Sandy #Libhu",
    ]
    return "\n".join(lines)[:5000]

def get_preview(episode_id: str) -> dict | None:
    path = PREVIEW_DIR/f"{episode_id}_preview.json"
    return json.loads(path.read_text()) if path.exists() else None
