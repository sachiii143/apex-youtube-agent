"""
apex_agent.py — APEX
Comedy sketch script writer for Trishul, Sandy, Libhu.
Original IP. Versioned. SEO-optimised. Copyright-safe.
"""

import os, json, re, hashlib
from datetime import datetime
from pathlib import Path
import audit_log
from character_bible import get_prompt_context, CHARACTERS, WORLD, is_locked, lock_bible

BASE_DIR    = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)

SCRIPT_SYSTEM = """You are APEX Script Engine — elite comedy sketch writer.
You write original, family-safe cartoon comedy scripts.
You NEVER reference real cartoon shows, real characters, or copyrighted content.
You output ONLY valid JSON. No markdown fences. No commentary before or after."""

SEO_SYSTEM = """You are an expert YouTube SEO strategist.
Output ONLY valid JSON. No markdown. No commentary."""

def _llm(prompt: str, system: str, max_tokens: int = 2000) -> str:
    try:
        import llm_provider
        return llm_provider.generate(system, [{"role":"user","content":prompt}], max_tokens)
    except Exception as e:
        raise RuntimeError(f"LLM unavailable: {e}")

def _script_prompt(topic: str, episode_number: int, enhancement_hints: str = "") -> str:
    bible = get_prompt_context()
    return f"""Write episode {episode_number} of a comedy sketch YouTube video.

{bible}

{enhancement_hints}

Episode topic: {topic}

Return ONLY this exact JSON (no markdown, no extra fields):
{{
  "episode_id": "ep_{episode_number:04d}",
  "episode_number": {episode_number},
  "title": "Catchy YouTube title under 60 chars — make it funny",
  "description": "SEO YouTube description 150-200 chars",
  "tags": ["comedy","animation","cartoon","kids","funny","original","sketch"],
  "thumbnail_concept": "What the thumbnail should show — max 20 words",
  "thumbnail_text": "3-5 bold words for thumbnail overlay",
  "content_warnings": [],
  "scenes": [
    {{
      "id": "scene_01",
      "characters_present": ["Trishul","Sandy"],
      "location": "Sunridge Town location",
      "narration": "Spoken narration — 2-4 natural sentences, funny tone",
      "caption": "Short on-screen text max 7 words",
      "image_prompt": "Detailed image description for AI art — include characters, scene, mood, cartoon style",
      "duration_pad": 1.5,
      "comedy_beat": "setup"
    }}
  ]
}}

Rules:
- 6-7 scenes following setup→escalation→crisis→resolution→tag structure
- Trishul starts chaos, Sandy objects logically, Libhu says unexpected thing
- End with Trishul saying his catchphrase
- Family safe — no violence, no adult themes
- Original setting only — Sunridge Town locations
- Do NOT reference any real cartoon show or character"""

def write_script(topic: str, episode_number: int, enhancement_hints: str = "") -> dict:
    prompt = _script_prompt(topic, episode_number, enhancement_hints)
    raw    = _llm(prompt, SCRIPT_SYSTEM, 2500)
    raw    = raw.strip()
    if "```" in raw:
        raw = re.sub(r"```json?\s*", "", raw).replace("```", "").strip()
    start = raw.find("{"); end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON in script output: {raw[:200]}")
    script = json.loads(raw[start:end])
    script = _validate(script, episode_number)

    # SEO pass
    try:
        seo_prompt = f"""Improve YouTube SEO:
Title: {script['title']}
Description: {script['description']}
Tags: {script.get('tags',[])}
Return ONLY JSON: {{"title":"improved title under 60 chars","description":"improved 150-200 chars","tags":["tag1","tag2"],"thumbnail_text":"3-5 bold words"}}"""
        seo_raw = _llm(seo_prompt, SEO_SYSTEM, 400).strip()
        if "```" in seo_raw:
            seo_raw = re.sub(r"```json?\s*","",seo_raw).replace("```","").strip()
        seo = json.loads(seo_raw[seo_raw.find("{"):seo_raw.rfind("}")+1])
        script["title"]          = seo.get("title", script["title"])[:60]
        script["description"]    = seo.get("description", script["description"])[:200]
        script["tags"]           = seo.get("tags", script["tags"])[:15]
        script["thumbnail_text"] = seo.get("thumbnail_text","")
    except Exception:
        pass

    script["version"]    = _version(script)
    script["created_at"] = datetime.utcnow().isoformat()
    script["rights"]     = "Original IP — owned by channel creator"
    script["bible_lock"] = is_locked()

    out_path = SCRIPTS_DIR / f"{script['episode_id']}_v1.json"
    out_path.write_text(json.dumps(script, indent=2, ensure_ascii=False))

    if episode_number == 1 and not is_locked():
        lock_bible()

    audit_log.record("VIDEO_SCRIPT_DONE", subject=script["episode_id"],
                     payload={"title":script["title"],"scenes":len(script["scenes"]),"version":script["version"]})
    return script

def _validate(script: dict, episode_number: int) -> dict:
    required = ["title","description","scenes"]
    for field in required:
        if field not in script:
            raise ValueError(f"Script missing field: {field}")
    if not script.get("scenes"):
        raise ValueError("Script has no scenes")
    script.setdefault("episode_id", f"ep_{episode_number:04d}")
    script.setdefault("tags", ["comedy","animation","cartoon","original"])
    script.setdefault("content_warnings", [])
    script.setdefault("thumbnail_concept", script["title"])
    script.setdefault("thumbnail_text", "")

    blocked = ["ben 10","ben10","adventure time","finn","jake","gumball",
               "steven universe","regular show","mordecai","rigby",
               "tom and jerry","scooby","batman","superman","pikachu","spongebob"]
    for i, scene in enumerate(script["scenes"]):
        scene.setdefault("id", f"scene_{i+1:02d}")
        scene.setdefault("narration", f"Scene {i+1}")
        scene.setdefault("caption", "")
        scene.setdefault("image_prompt",
            f"cartoon comedy scene with Trishul Sandy and Libhu, {WORLD['name']}, bright colors, family friendly")
        scene.setdefault("duration_pad", 1.5)
        scene.setdefault("comedy_beat", "escalation")
        scene.setdefault("characters_present", list(CHARACTERS.keys()))
        narration_lower = scene["narration"].lower()
        for name in blocked:
            if name in narration_lower:
                scene["narration"] = scene["narration"].replace(name,"[original-character]")
                audit_log.record("VIDEO_REJECTED", subject=scene["id"],
                                 payload={"reason":f"copyright name detected: {name}"})
    return script

def _version(script: dict) -> str:
    content = json.dumps({"title":script["title"],"scenes":len(script["scenes"])})
    return f"1.0.{hashlib.md5(content.encode()).hexdigest()[:8]}"

def get_episode_count() -> int:
    return len(list(SCRIPTS_DIR.glob("ep_*_v1.json")))

def load_script(episode_id: str) -> dict | None:
    path = SCRIPTS_DIR / f"{episode_id}_v1.json"
    return json.loads(path.read_text()) if path.exists() else None

def list_scripts() -> list:
    scripts = []
    for path in sorted(SCRIPTS_DIR.glob("ep_*_v1.json")):
        try:
            data = json.loads(path.read_text())
            scripts.append({"episode_id":data.get("episode_id"),"title":data.get("title"),
                            "scenes":len(data.get("scenes",[])),"created_at":data.get("created_at"),
                            "version":data.get("version")})
        except Exception:
            pass
    return scripts
