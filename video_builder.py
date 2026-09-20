"""
video_builder.py — APEX
Renders .mp4 from script. WaveNet → gTTS → silent fallback.
Approval card required before any YouTube upload.
"""

import os, json, subprocess
from datetime import datetime
from pathlib import Path
import audit_log, approval, image_engine

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
AUDIO_DIR  = BASE_DIR / "audio_cache"
SHORTS_DIR = BASE_DIR / "shorts"
OUTPUT_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
SHORTS_DIR.mkdir(exist_ok=True)

def log(msg): print(msg)

def render(script: dict) -> dict:
    episode_id = script.get("episode_id","ep_unknown")
    out_path   = OUTPUT_DIR / f"{episode_id}.mp4"
    audit_log.record("VIDEO_QUEUED", subject=episode_id,
                     payload={"title":script.get("title",""),"scenes":len(script.get("scenes",[]))})

    log(f"  [APEX] Generating images for {episode_id}...")
    img_paths = []
    for scene in script.get("scenes", []):
        result = image_engine.generate(
            prompt   = scene.get("image_prompt","cartoon comedy scene"),
            scene_id = f"{episode_id}_{scene['id']}",
        )
        img_paths.append(result["path"])
        log(f"    {scene['id']} → {result['provider']}")

    log(f"  [APEX] Generating narration audio...")
    audio_paths = []
    for scene in script.get("scenes", []):
        audio_path = AUDIO_DIR / f"{episode_id}_{scene['id']}.mp3"
        if not audio_path.exists():
            _tts(scene.get("narration",""), str(audio_path))
        audio_paths.append(str(audio_path))

    log(f"  [APEX] Rendering video...")
    result = _render_moviepy(script, img_paths, audio_paths, str(out_path))
    if not result["ok"]:
        audit_log.record("VIDEO_REJECTED", subject=episode_id,
                         payload={"reason":result.get("error","render failed")})
        return result

    audit_log.record("VIDEO_RENDERED", subject=episode_id,
                     payload={"path":str(out_path),
                              "size_mb":round(out_path.stat().st_size/1024/1024,2)})

    card_payload = {
        "episode_id":  episode_id,
        "title":       script.get("title",""),
        "description": script.get("description",""),
        "tags":        script.get("tags",[]),
        "video_path":  str(out_path),
        "thumbnail_path": str(BASE_DIR/"thumbnails"/f"{episode_id}_thumb.png"),
        "visibility":  "public",
        "made_for_kids": True,
    }
    card_id = approval.issue("YOUTUBE_UPLOAD", card_payload, ttl_hours=24)
    log(f"\n  [APEX] Video ready: {out_path}")
    log(f"  [APEX] Approval card: {card_id}")
    log(f"  [APEX] Approve in the dashboard Approvals tab before uploading.")
    return {"ok":True, "path":str(out_path), "card_id":card_id, "error":None,
            "img_paths":img_paths, "audio_paths":audio_paths}

def _tts(text: str, out_path: str):
    # 1. Google Cloud WaveNet
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_TTS_API_KEY"):
        try:
            from google.cloud import texttospeech
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text[:4500])
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-IN", name="en-IN-Wavenet-A",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.05, pitch=1.5)
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config)
            Path(out_path).write_bytes(response.audio_content)
            return
        except Exception:
            pass

    # 2. gTTS
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", tld="co.uk", slow=False).save(out_path)
        return
    except Exception:
        pass

    # 3. Silent fallback
    try:
        dur = max(3, len(text.split()) * 0.4)
        subprocess.run(["ffmpeg","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
                        "-t",str(dur),"-q:a","9","-acodec","libmp3lame",out_path,"-y"],
                       capture_output=True, check=True)
    except Exception:
        Path(out_path).write_bytes(b"")

def _render_moviepy(script: dict, img_paths: list, audio_paths: list, out_path: str) -> dict:
    try:
        from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips
        import platform
        clips = []
        for i, scene in enumerate(script.get("scenes",[])):
            if i >= len(img_paths) or i >= len(audio_paths): break
            if not os.path.exists(img_paths[i]) or not os.path.exists(audio_paths[i]): continue
            try:
                narration = AudioFileClip(audio_paths[i])
                duration  = narration.duration + float(scene.get("duration_pad",1.5))
                img_clip  = ImageClip(img_paths[i]).with_duration(duration).resized(height=740)
                caption_text = scene.get("caption","")
                if caption_text:
                    fp = {
                        "Windows": r"C:\Windows\Fonts\arialbd.ttf",
                        "Darwin":  "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                        "Linux":   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                    }.get(platform.system(),"")
                    if fp and os.path.exists(fp):
                        caption = (TextClip(font=fp, text=caption_text, font_size=44,
                                            color="white", stroke_color="black", stroke_width=2,
                                            method="caption", size=(1100,None))
                                   .with_duration(duration).with_position(("center",620)))
                        scene_clip = CompositeVideoClip([img_clip,caption],size=(1280,720)).with_audio(narration)
                    else:
                        scene_clip = CompositeVideoClip([img_clip],size=(1280,720)).with_audio(narration)
                else:
                    scene_clip = CompositeVideoClip([img_clip],size=(1280,720)).with_audio(narration)
                clips.append(scene_clip)
            except Exception as e:
                log(f"    Warning: scene {i+1} failed: {e}")
        if not clips: return {"ok":False,"error":"No clips rendered"}
        concatenate_videoclips(clips, method="compose").write_videofile(
            out_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        return {"ok":True,"path":out_path}
    except ImportError as e:
        return {"ok":False,"error":f"Missing: {e}. Run: pip install moviepy"}
    except Exception as e:
        return {"ok":False,"error":str(e)}

def upload_with_approval(card_id: str) -> dict:
    card = approval.get_card(card_id)
    if not card: return {"ok":False,"reason":"Card not found"}
    payload = card["payload"]
    check   = approval.check(card_id, payload)
    if not check["ok"]: return {"ok":False,"reason":check["reason"]}
    try:
        import upload_to_youtube as yt
        result = yt.upload(video_path=payload["video_path"], title=payload["title"],
                           description=payload["description"], tags=payload.get("tags",[]))
        audit_log.record("VIDEO_UPLOADED", subject=payload["episode_id"],
                         payload={"youtube_id":result.get("id",""),"title":payload["title"]})
        return {"ok":True,"youtube_id":result.get("id")}
    except Exception as e:
        return {"ok":False,"reason":str(e)}
