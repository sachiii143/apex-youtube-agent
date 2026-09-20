"""
thumbnail_gen.py — APEX
Generates branded YouTube thumbnails 1280x720.
Sunridge Town colour palette. Bold text overlay.
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import image_engine, audit_log

BASE_DIR  = Path(__file__).parent
THUMB_DIR = BASE_DIR / "thumbnails"
THUMB_DIR.mkdir(exist_ok=True)

COLOURS = {
    "bg_top":   (8,20,60), "bg_bottom":(20,50,100),
    "accent":   (0,212,255),"gold":(255,200,50),
    "white":    (255,255,255),"shadow":(0,0,0),"red_band":(220,30,60),
}
W, H = 1280, 720

def _get_font(size: int, bold: bool = True):
    import platform
    paths = {
        "Windows": r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        "Darwin":  "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "Linux":   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    }
    fp = paths.get(platform.system(),"")
    try: return ImageFont.truetype(fp, size) if fp and os.path.exists(fp) else ImageFont.load_default()
    except Exception: return ImageFont.load_default()

def _text_width(text: str, font) -> int:
    try: bbox = font.getbbox(text); return bbox[2]-bbox[0]
    except Exception: return len(text)*20

def generate(episode_id: str, title: str, thumbnail_concept: str, thumbnail_text: str = "") -> dict:
    out_path = THUMB_DIR / f"{episode_id}_thumb.png"
    if out_path.exists():
        return {"path":str(out_path),"episode_id":episode_id,"cached":True}

    art = image_engine.generate(
        prompt   = thumbnail_concept + ", cartoon style, vibrant, dramatic expression",
        scene_id = f"{episode_id}_thumb_art",
        style    = "cartoon illustration, expressive, bold colors, thumbnail style",
    )

    canvas = Image.new("RGB",(W,H),COLOURS["bg_top"])
    draw   = ImageDraw.Draw(canvas)
    for y in range(H):
        t = y/H
        r = int(COLOURS["bg_top"][0]*(1-t)+COLOURS["bg_bottom"][0]*t)
        g = int(COLOURS["bg_top"][1]*(1-t)+COLOURS["bg_bottom"][1]*t)
        b = int(COLOURS["bg_top"][2]*(1-t)+COLOURS["bg_bottom"][2]*t)
        draw.line([(0,y),(W,y)],fill=(r,g,b))

    try:
        art_img = Image.open(art["path"]).convert("RGBA")
        art_img = art_img.resize((820,H),Image.LANCZOS)
        canvas.paste(art_img,(460,0),art_img if art_img.mode=="RGBA" else None)
    except Exception:
        pass

    fade = Image.new("RGBA",(520,H),(0,0,0,0))
    fdraw = ImageDraw.Draw(fade)
    for x in range(520):
        alpha = int(220*(1-x/520))
        fdraw.line([(x,0),(x,H)],fill=(8,20,60,alpha))
    canvas.paste(fade,(0,0),fade)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle([20,18,200,52],radius=12,fill=COLOURS["red_band"])
    draw.text((110,35),"SUNRIDGE TOWN",fill=COLOURS["white"],font=_get_font(18),anchor="mm")

    title_font = _get_font(68)
    words = title.split(); line1=""; line2=""
    for i,w in enumerate(words):
        test = (line1+" "+w).strip()
        if _text_width(test,title_font)<440: line1=test
        else: line2=" ".join(words[i:]); break

    y_title=120
    draw.text((44,y_title+4),line1,fill=COLOURS["shadow"],font=title_font)
    draw.text((44,y_title+4+78),line2,fill=COLOURS["shadow"],font=title_font)
    draw.text((40,y_title),line1,fill=COLOURS["white"],font=title_font)
    draw.text((40,y_title+74),line2,fill=COLOURS["white"],font=title_font)

    if thumbnail_text:
        ot_font = _get_font(44)
        tw = _text_width(thumbnail_text.upper(),ot_font); pad=16
        draw.rounded_rectangle([36,H-74,36+tw+pad*2,H-22],radius=8,fill=COLOURS["gold"])
        draw.text((36+pad,H-48),thumbnail_text.upper(),fill=COLOURS["shadow"],font=ot_font,anchor="lm")

    canvas.save(str(out_path),"JPEG",quality=95)
    audit_log.record("IMAGE_GENERATED",subject=episode_id,payload={"type":"thumbnail","path":str(out_path)})
    return {"path":str(out_path),"episode_id":episode_id,"cached":False}
