"""
kling_engine.py — APEX
Paid animation engine: Kling AI + Pika Labs.
Each scene description → real animated cartoon clip.
Falls back gracefully if no key set.

Kling AI:  ~₹1,500/month — best quality cartoon animation
Pika Labs: ~₹1,200/month — good quality, faster
Runway ML: ~₹1,500/month — cinematic quality
"""

import os, json, time, urllib.request, urllib.parse, base64
from datetime import datetime
from pathlib import Path
import audit_log

BASE_DIR   = Path(__file__).parent
CLIPS_DIR  = BASE_DIR / "clips"
CLIPS_DIR.mkdir(exist_ok=True)


# ── Provider detection ────────────────────────────────────────────────────────

def best_available_provider() -> str | None:
    """Return the best available paid animation provider or None."""
    if os.environ.get("KLING_API_KEY"):   return "kling"
    if os.environ.get("PIKA_API_KEY"):    return "pika"
    if os.environ.get("RUNWAY_API_KEY"):  return "runway"
    return None


def is_available() -> bool:
    return best_available_provider() is not None


# ── Main entry ────────────────────────────────────────────────────────────────

def generate_clip(scene: dict, episode_id: str, scene_index: int,
                  style: str = "cartoon animation, vibrant colors, family friendly, 2D animated") -> dict:
    """
    Generate one animated clip for a scene.
    Returns {"ok": bool, "path": str, "provider": str, "duration": float}
    """
    scene_id   = scene.get("id", f"scene_{scene_index:02d}")
    out_path   = CLIPS_DIR / f"{episode_id}_{scene_id}.mp4"

    if out_path.exists():
        return {"ok": True, "path": str(out_path), "provider": "cached", "cached": True}

    # Build prompt from scene
    characters = scene.get("characters_present", [])
    location   = scene.get("location", "Sunridge Town")
    narration  = scene.get("narration", "")
    beat       = scene.get("comedy_beat", "setup")
    image_prompt = scene.get("image_prompt", "")

    # Compose animation prompt
    char_desc = ", ".join(characters) + " cartoon characters" if characters else "cartoon characters"
    motion_hint = {
        "setup":      "characters standing and talking, gentle movement",
        "escalation": "characters moving around with increasing energy",
        "punchline":  "dramatic reaction, character jumps or falls, comedic timing",
        "reaction":   "characters look at each other with surprise expressions",
        "tag":        "characters wave goodbye, zoom out",
    }.get(beat, "characters interacting naturally")

    full_prompt = (
        f"{image_prompt}, {char_desc}, {location} setting, "
        f"{motion_hint}, {style}, "
        f"smooth animation, bright colors, family friendly, no text overlay, "
        f"Sunridge Town original cartoon"
    )

    provider = best_available_provider()

    if provider == "kling":
        result = _kling(full_prompt, out_path)
    elif provider == "pika":
        result = _pika(full_prompt, out_path)
    elif provider == "runway":
        result = _runway(full_prompt, out_path)
    else:
        return {"ok": False, "error": "No animation API key set",
                "howto": "Add KLING_API_KEY or PIKA_API_KEY in Settings"}

    if result["ok"]:
        audit_log.record("IMAGE_GENERATED", subject=f"{episode_id}_{scene_id}",
                         payload={"type": "animated_clip", "provider": provider,
                                  "prompt": full_prompt[:80]})

    return result


# ── Kling AI ──────────────────────────────────────────────────────────────────

def _kling(prompt: str, out_path: Path) -> dict:
    """
    Kling AI video generation.
    API docs: https://klingai.com/api
    Free trial: 66 credits (~33 clips) on signup
    Paid: ~₹1,500/month for ~500 clips
    """
    key = os.environ.get("KLING_API_KEY", "")
    if not key:
        return {"ok": False, "error": "KLING_API_KEY not set"}

    try:
        # Step 1: Submit generation job
        payload = json.dumps({
            "prompt":        prompt[:500],
            "negative_prompt": "text, watermark, blurry, low quality, violence, adult content",
            "model":         "kling-v1",
            "duration":      5,       # 5 seconds per scene
            "aspect_ratio":  "16:9",
            "cfg_scale":     0.5,
        }).encode()

        req = urllib.request.Request(
            "https://api.klingai.com/v1/videos/text2video",
            data    = payload,
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {key}",
            },
            method = "POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data   = json.loads(r.read())

        task_id = data.get("data", {}).get("task_id", "")
        if not task_id:
            return {"ok": False, "error": f"No task_id returned: {data}"}

        # Step 2: Poll for completion
        for attempt in range(30):  # up to 5 minutes
            time.sleep(10)
            poll_url = f"https://api.klingai.com/v1/videos/text2video/{task_id}"
            poll_req = urllib.request.Request(
                poll_url,
                headers={"Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(poll_req, timeout=15) as r:
                status_data = json.loads(r.read())

            task_status = status_data.get("data", {}).get("task_status", "")
            if task_status == "succeed":
                # Download clip
                videos = status_data.get("data", {}).get("task_result", {}).get("videos", [])
                if videos:
                    video_url = videos[0].get("url", "")
                    with urllib.request.urlopen(video_url, timeout=60) as r:
                        out_path.write_bytes(r.read())
                    return {"ok": True, "path": str(out_path), "provider": "kling", "duration": 5}
                return {"ok": False, "error": "No video URL in response"}
            elif task_status == "failed":
                return {"ok": False, "error": "Kling generation failed"}
            # Still processing — continue polling

        return {"ok": False, "error": "Kling timed out after 5 minutes"}

    except Exception as e:
        return {"ok": False, "error": f"Kling error: {e}"}


# ── Pika Labs ─────────────────────────────────────────────────────────────────

def _pika(prompt: str, out_path: Path) -> dict:
    """
    Pika Labs video generation.
    API: https://pika.art/api
    Free trial available. Paid: ~₹1,200/month
    """
    key = os.environ.get("PIKA_API_KEY", "")
    if not key:
        return {"ok": False, "error": "PIKA_API_KEY not set"}

    try:
        payload = json.dumps({
            "promptText":  prompt[:400],
            "negativePrompt": "text, watermark, blurry, violence, adult",
            "options": {
                "aspectRatio": "16:9",
                "frameRate":   24,
                "motion":      2,      # 1-4, higher = more motion
            }
        }).encode()

        req = urllib.request.Request(
            "https://api.pika.art/v1/generate",
            data    = payload,
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {key}",
            },
            method = "POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        job_id = data.get("job", {}).get("id", "")
        if not job_id:
            return {"ok": False, "error": f"No job ID: {data}"}

        # Poll for completion
        for attempt in range(20):
            time.sleep(15)
            poll_req = urllib.request.Request(
                f"https://api.pika.art/v1/jobs/{job_id}",
                headers={"Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(poll_req, timeout=15) as r:
                status_data = json.loads(r.read())

            status = status_data.get("job", {}).get("status", "")
            if status == "finished":
                video_url = status_data.get("job", {}).get("videos", [{}])[0].get("url", "")
                if video_url:
                    with urllib.request.urlopen(video_url, timeout=60) as r:
                        out_path.write_bytes(r.read())
                    return {"ok": True, "path": str(out_path), "provider": "pika", "duration": 4}
                return {"ok": False, "error": "No video URL"}
            elif status in ("failed", "error"):
                return {"ok": False, "error": "Pika generation failed"}

        return {"ok": False, "error": "Pika timed out"}

    except Exception as e:
        return {"ok": False, "error": f"Pika error: {e}"}


# ── Runway ML ─────────────────────────────────────────────────────────────────

def _runway(prompt: str, out_path: Path) -> dict:
    """
    Runway ML Gen-3 video generation.
    API: https://runwayml.com/api
    Paid: ~₹1,500/month
    """
    key = os.environ.get("RUNWAY_API_KEY", "")
    if not key:
        return {"ok": False, "error": "RUNWAY_API_KEY not set"}

    try:
        payload = json.dumps({
            "promptText":     prompt[:400],
            "model":          "gen3a_turbo",
            "duration":       5,
            "ratio":          "1280:720",
            "watermark":      False,
        }).encode()

        req = urllib.request.Request(
            "https://api.dev.runwayml.com/v1/image_to_video",
            data    = payload,
            headers = {
                "Content-Type":    "application/json",
                "Authorization":   f"Bearer {key}",
                "X-Runway-Version":"2024-11-06",
            },
            method = "POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        task_id = data.get("id", "")
        if not task_id:
            return {"ok": False, "error": f"No task ID: {data}"}

        for attempt in range(24):
            time.sleep(10)
            poll_req = urllib.request.Request(
                f"https://api.dev.runwayml.com/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {key}", "X-Runway-Version":"2024-11-06"}
            )
            with urllib.request.urlopen(poll_req, timeout=15) as r:
                status_data = json.loads(r.read())

            status = status_data.get("status", "")
            if status == "SUCCEEDED":
                video_url = status_data.get("output", [None])[0]
                if video_url:
                    with urllib.request.urlopen(video_url, timeout=60) as r:
                        out_path.write_bytes(r.read())
                    return {"ok": True, "path": str(out_path), "provider": "runway", "duration": 5}
                return {"ok": False, "error": "No output URL"}
            elif status == "FAILED":
                return {"ok": False, "error": "Runway generation failed"}

        return {"ok": False, "error": "Runway timed out"}

    except Exception as e:
        return {"ok": False, "error": f"Runway error: {e}"}


# ── Full episode render ───────────────────────────────────────────────────────

def render_episode(script: dict) -> dict:
    """
    Generate all animated clips for an episode and concatenate.
    Returns {"ok": bool, "path": str, "clips": int, "provider": str}
    """
    episode_id = script.get("episode_id", "ep_0001")
    scenes     = script.get("scenes", [])
    provider   = best_available_provider()

    if not provider:
        return {
            "ok":    False,
            "error": "No animation API key set. Add KLING_API_KEY or PIKA_API_KEY in Settings → API Keys.",
            "howto": {
                "kling":  "Sign up at klingai.com → API → get key → free 66 credits on signup",
                "pika":   "Sign up at pika.art → API → get key",
                "runway": "Sign up at runwayml.com → API → get key",
            }
        }

    print(f"  [KLING] Generating {len(scenes)} animated clips via {provider}...")
    clip_paths = []

    for i, scene in enumerate(scenes):
        print(f"  [KLING] Scene {i+1}/{len(scenes)}: {scene.get('id','')}")
        result = generate_clip(scene, episode_id, i + 1)
        if result["ok"]:
            clip_paths.append(result["path"])
            print(f"  [KLING] ✓ {scene.get('id','')} — {result.get('provider','')}")
        else:
            print(f"  [KLING] ✗ {scene.get('id','')} — {result.get('error','')}")

    if not clip_paths:
        return {"ok": False, "error": "No clips generated"}

    # Concatenate
    final_path = BASE_DIR / "output" / f"{episode_id}_animated.mp4"
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        clips = [VideoFileClip(p) for p in clip_paths]
        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(str(final_path), fps=24, codec="libx264",
                               audio_codec="aac", verbose=False, logger=None)
        for c in clips:
            try: c.close()
            except: pass

        audit_log.record("VIDEO_RENDERED", subject=episode_id,
                         payload={"type": "animated", "provider": provider,
                                  "clips": len(clip_paths), "path": str(final_path)})

        return {"ok": True, "path": str(final_path),
                "clips": len(clip_paths), "provider": provider}

    except Exception as e:
        return {"ok": False, "error": str(e), "clips_available": clip_paths}
