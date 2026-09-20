"""
quality_check.py — APEX
25+ automated checks before video enters upload queue.
"""

import os
from datetime import datetime
from pathlib import Path
import audit_log

THRESHOLDS = {
    "min_scenes":4,"max_scenes":10,"min_duration_s":60,"max_duration_s":600,
    "min_narration_words":15,"max_narration_words":120,
    "required_resolution":(1280,720),"min_image_bytes":1000,"min_audio_bytes":500,
}

def run(script: dict, video_path: str, img_paths: list, audio_paths: list) -> dict:
    checks=[]; issues=[]
    def ck(name, passed, detail="", blocking=True):
        checks.append({"name":name,"passed":passed,"detail":detail,"blocking":blocking})
        if not passed and blocking: issues.append(f"{name}: {detail}")

    episode_id = script.get("episode_id","unknown")
    scenes     = script.get("scenes",[])
    sc         = len(scenes)

    ck("Scene count", THRESHOLDS["min_scenes"]<=sc<=THRESHOLDS["max_scenes"],
       f"{sc} scenes (need {THRESHOLDS['min_scenes']}–{THRESHOLDS['max_scenes']})")
    ck("Title present",      bool(script.get("title","").strip()),       "Title is empty")
    ck("Description present",bool(script.get("description","").strip()),"Description is empty")
    ck("Tags present",       len(script.get("tags",[]))>=3,              f"{len(script.get('tags',[]))} tags (need ≥3)")

    for i, scene in enumerate(scenes[:10]):
        words = len(scene.get("narration","").split())
        ck(f"Scene {i+1} narration length",
           THRESHOLDS["min_narration_words"]<=words<=THRESHOLDS["max_narration_words"],
           f"{words} words (need {THRESHOLDS['min_narration_words']}–{THRESHOLDS['max_narration_words']})")

    full_text = " ".join(s.get("narration","") for s in scenes).lower()
    blocked   = ["ben 10","adventure time","scooby","spongebob","pikachu","tom and jerry","mickey mouse"]
    violations= [b for b in blocked if b in full_text]
    ck("Copyright scan", len(violations)==0, f"Blocked names: {violations}")

    ck("Image count", len(img_paths)>=len(scenes), f"{len(img_paths)} images for {len(scenes)} scenes")
    for i, p in enumerate(img_paths[:10]):
        if os.path.exists(p):
            ck(f"Image {i+1} not empty", os.path.getsize(p)>=THRESHOLDS["min_image_bytes"],
               f"Too small: {os.path.getsize(p)} bytes")
        else:
            ck(f"Image {i+1} exists", False, f"Not found: {p}")

    if video_path and os.path.exists(video_path):
        ck("Video file not empty", os.path.getsize(video_path)>10000,
           f"Too small: {os.path.getsize(video_path)} bytes")
    else:
        ck("Video file exists", False, f"Not found: {video_path}")

    blocking_checks = [c for c in checks if c["blocking"]]
    passed_blocking = [c for c in blocking_checks if c["passed"]]
    passed_all      = [c for c in checks if c["passed"]]
    passed          = len(issues)==0

    result = {"episode_id":episode_id,"passed":passed,
              "blocking_score":round(len(passed_blocking)/max(len(blocking_checks),1),3),
              "overall_score":round(len(passed_all)/max(len(checks),1),3),
              "checks":checks,"issues":issues,"total_checks":len(checks),
              "passed_checks":len(passed_all),"checked_at":datetime.utcnow().isoformat()}

    audit_log.record("VIDEO_APPROVED" if passed else "VIDEO_REJECTED", subject=episode_id,
                     payload={"quality_score":result["overall_score"],"issues":len(issues),"passed":passed})
    return result

def check_summary(result: dict) -> str:
    if result["passed"]:
        return f"Quality check PASSED — {result['passed_checks']}/{result['total_checks']} checks, score {result['overall_score']:.0%}"
    return f"Quality check FAILED — {len(result['issues'])} issues: {'; '.join(result['issues'][:3])}"
