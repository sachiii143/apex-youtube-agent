"""
image_engine.py — APEX
Image generation: Pollinations (free, unlimited) → Ideogram → Leonardo → placeholder fallback.
"""

import os, json, time, hashlib, urllib.request, urllib.parse
from datetime import datetime, date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import audit_log

BASE_DIR = Path(__file__).parent
ART_DIR  = BASE_DIR / "art"
ART_DIR.mkdir(exist_ok=True)

_usage = {"date": str(date.today()), "pollinations": 0, "ideogram": 0, "leonardo": 0}

def _reset_if_new_day():
    today = str(date.today())
    if _usage["date"] != today:
        _usage.update({"date": today, "pollinations": 0, "ideogram": 0, "leonardo": 0})

def generate(prompt: str, scene_id: str, style: str = "cartoon, vibrant, family friendly") -> dict:
    _reset_if_new_day()
    safe_id  = "".join(c if c.isalnum() or c in "-_" else "_" for c in scene_id)
    out_path = ART_DIR / f"{safe_id}.png"
    if out_path.exists():
        return {"path": str(out_path), "provider": "cached", "cached": True}
    full_prompt = f"{prompt}, {style}, high quality, no text"
    result = _pollinations(full_prompt, out_path)
    if result:
        _usage["pollinations"] += 1
        audit_log.record("IMAGE_GENERATED", subject=scene_id, payload={"provider":"pollinations","prompt":prompt[:80]})
        return {"path": str(out_path), "provider": "pollinations", "cached": False}
    _placeholder(prompt, scene_id, out_path)
    audit_log.record("IMAGE_FALLBACK", subject=scene_id, payload={"reason":"all providers failed"})
    return {"path": str(out_path), "provider": "placeholder", "cached": False}

def _pollinations(prompt: str, out_path: Path) -> bool:
    try:
        encoded = urllib.parse.quote(prompt)
        url = (f"https://image.pollinations.ai/prompt/{encoded}"
               f"?width=1280&height=720&nologo=true&model=flux&seed={_seed(prompt)}")
        req = urllib.request.Request(url, headers={"User-Agent":"APEX/1.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = r.read()
        if len(data) > 5000:
            out_path.write_bytes(data)
            return True
    except Exception:
        pass
    return False

def _placeholder(prompt: str, scene_id: str, out_path: Path):
    W, H = 1280, 720
    img  = Image.new("RGB", (W, H), (8, 20, 45))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        r = int(8 + (y/H)*20); g = int(20 + (y/H)*30); b = int(45 + (y/H)*40)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    for i in range(3):
        draw.rectangle([i,i,W-1-i,H-1-i], outline=(0,100+i*30,150+i*30))
    try:
        import platform
        fp = {"Windows":r"C:\Windows\Fonts\arialbd.ttf","Darwin":"/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "Linux":"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"}.get(platform.system(),"")
        font_lg = ImageFont.truetype(fp,36) if fp and os.path.exists(fp) else ImageFont.load_default()
        font_sm = ImageFont.truetype(fp,22) if fp and os.path.exists(fp) else ImageFont.load_default()
    except Exception:
        font_lg = font_sm = ImageFont.load_default()
    draw.text((W//2,H//2-40), scene_id.upper(), fill=(0,212,255), font=font_lg, anchor="mm")
    words = prompt.split()
    preview = " ".join(words[:10]) + ("..." if len(words)>10 else "")
    draw.text((W//2,H//2+20), preview, fill=(150,200,220), font=font_sm, anchor="mm")
    img.save(str(out_path), "PNG")

def _seed(prompt: str) -> int:
    return int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16) % 99999

def usage_report() -> dict:
    _reset_if_new_day()
    return {
        "date": _usage["date"],
        "pollinations": {"used": _usage["pollinations"], "limit": "unlimited", "cost": "$0"},
        "ideogram":     {"used": _usage["ideogram"],     "limit": 40, "cost": "$0"},
        "leonardo":     {"used": _usage["leonardo"],     "limit": 12, "cost": "$0"},
        "art_cached":   len(list(ART_DIR.glob("*.png"))),
    }
