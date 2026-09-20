"""
manim_engine.py — APEX
Free 2D animation engine using Manim (same tool as 3Blue1Brown).
Converts APEX scripts into smooth animated scenes with:
- Moving characters (Trishul/Sandy/Libhu as coloured shapes + labels)
- Speech bubbles
- Scene transitions
- Animated text and captions
- Background scenes

Install: pip install manim
Also needs: apt install libcairo2-dev libpango1.0-dev (Linux)
            or: choco install miktex ffmpeg (Windows)

No GPU needed. Runs on any laptop. Completely free.
"""

import os, json, subprocess, sys, hashlib, tempfile
from datetime import datetime
from pathlib import Path
import audit_log

BASE_DIR   = Path(__file__).parent
MANIM_DIR  = BASE_DIR / "manim_scenes"
OUTPUT_DIR = BASE_DIR / "output"
MANIM_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Character visual definitions ──────────────────────────────────────────────
CHARACTER_STYLES = {
    "Trishul": {
        "color":      "#e74c3c",   # Red — bold, confident
        "body_color": "#c0392b",
        "label":      "TRISHUL",
        "shape":      "circle",
        "size":       0.55,
        "cape_color": "#8e44ad",
        "position":   [-3, -1, 0],
    },
    "Sandy": {
        "color":      "#3498db",   # Blue — calm, logical
        "body_color": "#2980b9",
        "label":      "SANDY",
        "shape":      "circle",
        "size":       0.48,
        "position":   [0, -1, 0],
    },
    "Libhu": {
        "color":      "#27ae60",   # Green — unpredictable, wild
        "body_color": "#229954",
        "label":      "LIBHU",
        "shape":      "circle",
        "size":       0.42,
        "position":   [3, -1, 0],
    },
}

LOCATION_COLORS = {
    "treehouse":   {"bg": "#1a0a00", "ground": "#4a2800", "sky": "#0d1a2e"},
    "school":      {"bg": "#0a0a1a", "ground": "#2c2c3e", "sky": "#1a1a2e"},
    "park":        {"bg": "#0a1a0a", "ground": "#1a3a1a", "sky": "#0a1a2e"},
    "kitchen":     {"bg": "#1a0d00", "ground": "#3a1a00", "sky": "#2a1a00"},
    "corner store":{"bg": "#0d0d0d", "ground": "#1a1a1a", "sky": "#0a0a1a"},
    "default":     {"bg": "#030810", "ground": "#0a1628", "sky": "#060d1a"},
}


def _get_location_colors(location: str) -> dict:
    location_lower = location.lower()
    for key in LOCATION_COLORS:
        if key in location_lower:
            return LOCATION_COLORS[key]
    return LOCATION_COLORS["default"]


# ── Manim scene code generator ────────────────────────────────────────────────

def generate_scene_code(scene: dict, episode_id: str, scene_index: int,
                        total_scenes: int) -> str:
    """
    Generate Manim Python code for one scene.
    Returns Python source code string.
    """
    characters = scene.get("characters_present", ["Trishul", "Sandy", "Libhu"])
    narration  = scene.get("narration", "")
    caption    = scene.get("caption", "")
    location   = scene.get("location", "Sunridge Town")
    beat       = scene.get("comedy_beat", "setup")
    scene_id   = scene.get("id", f"scene_{scene_index:02d}")
    colors     = _get_location_colors(location)

    # Wrap narration into lines max 45 chars
    words      = narration.split()
    lines      = []
    current    = ""
    for word in words:
        if len(current) + len(word) + 1 <= 45:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    narration_escaped = "\\n".join(lines[:4])  # max 4 lines
    caption_escaped   = caption.replace('"', '\\"').replace("'", "\\'")
    location_escaped  = location.replace('"', '\\"')

    class_name = f"Scene_{episode_id.replace('-','_')}_{scene_id.replace('-','_')}"

    # Build character positions based on who's in the scene
    char_positions = {
        1: [[0, -1.2, 0]],
        2: [[-2, -1.2, 0], [2, -1.2, 0]],
        3: [[-3, -1.2, 0], [0, -1.2, 0], [3, -1.2, 0]],
    }
    positions = char_positions.get(len(characters), char_positions[3])

    # Determine animation style based on comedy beat
    beat_animations = {
        "setup":       "FadeIn",
        "escalation":  "GrowFromCenter",
        "punchline":   "Flash",
        "reaction":    "Wiggle",
        "tag":         "FadeOut",
    }
    anim_type = beat_animations.get(beat, "FadeIn")

    code = f'''
class {class_name}(Scene):
    def construct(self):
        # ── Background ──────────────────────────────────────────
        bg = Rectangle(width=16, height=9, fill_color="{colors['bg']}", fill_opacity=1, stroke_width=0)
        ground = Rectangle(width=16, height=2, fill_color="{colors['ground']}", fill_opacity=1, stroke_width=0)
        ground.to_edge(DOWN, buff=0)
        sky_grad = Rectangle(width=16, height=4, fill_color="{colors['sky']}", fill_opacity=0.6, stroke_width=0)
        sky_grad.to_edge(UP, buff=0)
        self.add(bg, sky_grad, ground)

        # ── Location label ───────────────────────────────────────
        loc_label = Text("{location_escaped}", font_size=14, color=GREY)
        loc_label.to_corner(UL, buff=0.15)
        self.add(loc_label)

        # ── Scene counter ────────────────────────────────────────
        counter = Text("{scene_index}/{total_scenes}", font_size=12, color=GREY_D)
        counter.to_corner(UR, buff=0.15)
        self.add(counter)

        # ── Characters ───────────────────────────────────────────
        char_group = VGroup()
'''

    for i, char_name in enumerate(characters[:3]):
        style = CHARACTER_STYLES.get(char_name, CHARACTER_STYLES["Trishul"])
        pos   = positions[min(i, len(positions)-1)]
        code += f'''
        # {char_name}
        {char_name.lower()}_body = Circle(radius={style['size']}, color="{style['color']}", fill_color="{style['body_color']}", fill_opacity=0.95)
        {char_name.lower()}_body.move_to([{pos[0]}, {pos[1]}, 0])
        {char_name.lower()}_eyes_l = Dot(radius=0.07, color=WHITE).move_to([{pos[0]-0.15}, {pos[1]+0.1}, 0])
        {char_name.lower()}_eyes_r = Dot(radius=0.07, color=WHITE).move_to([{pos[0]+0.15}, {pos[1]+0.1}, 0])
        {char_name.lower()}_label = Text("{char_name}", font_size=16, color=WHITE, weight=BOLD)
        {char_name.lower()}_label.next_to({char_name.lower()}_body, DOWN, buff=0.1)
        {char_name.lower()}_grp = VGroup({char_name.lower()}_body, {char_name.lower()}_eyes_l, {char_name.lower()}_eyes_r, {char_name.lower()}_label)
        char_group.add({char_name.lower()}_grp)
'''

    code += f'''
        # Animate characters in
        self.play(AnimationGroup(*[FadeIn(c, shift=UP*0.3) for c in char_group], lag_ratio=0.2), run_time=0.8)

        # ── Narration text ───────────────────────────────────────
        narration_bg = RoundedRectangle(corner_radius=0.2, width=12, height=2.2,
                                         fill_color="#000000", fill_opacity=0.75, stroke_color="#00d4ff", stroke_width=1.5)
        narration_bg.to_edge(UP, buff=0.4)
        narration_txt = Text("{narration_escaped}", font_size=20, color=WHITE, line_spacing=1.3)
        narration_txt.move_to(narration_bg.get_center())
        narration_txt.set_max_width(11.5)
        self.play(FadeIn(narration_bg), Write(narration_txt), run_time=1.2)

'''

    # Add comedy beat specific animation
    if beat == "punchline" and characters:
        first_char = characters[0].lower()
        code += f'''
        # Punchline animation — bounce the speaker
        self.play(
            {first_char}_body.animate.scale(1.3).set_color(YELLOW),
            run_time=0.3
        )
        self.play(
            {first_char}_body.animate.scale(1/1.3).set_color("{CHARACTER_STYLES.get(characters[0], CHARACTER_STYLES['Trishul'])['color']}"),
            run_time=0.3
        )
'''
    elif beat == "reaction":
        code += f'''
        # Reaction animation — wobble all characters
        self.play(
            *[Wiggle(c, scale_value=1.15, n_wiggles=3) for c in char_group],
            run_time=0.8
        )
'''
    elif beat == "escalation":
        code += f'''
        # Escalation — zoom in slightly
        self.play(self.camera.frame.animate.scale(0.92), run_time=0.5)
        self.play(self.camera.frame.animate.scale(1/0.92), run_time=0.3)
'''

    if caption_escaped:
        code += f'''
        # ── Caption ──────────────────────────────────────────────
        caption_bg = RoundedRectangle(corner_radius=0.15, width=6, height=0.55,
                                       fill_color="#ffd700", fill_opacity=0.95, stroke_width=0)
        caption_bg.to_edge(DOWN, buff=0.6)
        caption_txt = Text("{caption_escaped}", font_size=22, color=BLACK, weight=BOLD)
        caption_txt.move_to(caption_bg.get_center())
        self.play(FadeIn(caption_bg), FadeIn(caption_txt), run_time=0.4)
'''

    # Hold duration based on narration length
    hold_time = max(2.0, len(narration.split()) * 0.35)

    code += f'''
        # Hold scene
        self.wait({hold_time:.1f})

        # Fade out
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.5)
'''

    return code


def generate_episode_code(script: dict) -> str:
    """
    Generate complete Manim Python file for an entire episode.
    """
    episode_id = script.get("episode_id", "ep_0001")
    title      = script.get("title", "Sunridge Town")
    scenes     = script.get("scenes", [])

    # Imports and config
    header = f'''#!/usr/bin/env python3
"""
APEX Generated Manim Animation
Episode: {episode_id}
Title: {title}
Generated: {datetime.utcnow().isoformat()}
Characters: Trishul, Sandy, Libhu — Original IP, owned by channel creator
"""

from manim import *

config.background_color = "#030810"
config.pixel_width  = 1280
config.pixel_height = 720
config.frame_rate   = 24

'''

    # Title scene
    title_escaped = title.replace('"', '\\"')
    header += f'''
class TitleScene(Scene):
    def construct(self):
        bg = Rectangle(width=16, height=9, fill_color="#030810", fill_opacity=1, stroke_width=0)
        self.add(bg)

        # Sunridge Town brand
        brand = Text("SUNRIDGE TOWN", font_size=22, color="#00d4ff", weight=BOLD)
        brand.to_edge(UP, buff=0.5)
        self.play(FadeIn(brand), run_time=0.5)

        # Episode title
        title_text = Text("{title_escaped}", font_size=38, color=WHITE, weight=BOLD)
        title_text.set_max_width(10)
        title_text.move_to(ORIGIN)

        title_bg = RoundedRectangle(corner_radius=0.3, width=title_text.width + 0.8,
                                     height=title_text.height + 0.4,
                                     fill_color="#0a1628", fill_opacity=0.9,
                                     stroke_color="#ffd700", stroke_width=2)
        title_bg.move_to(ORIGIN)

        self.play(FadeIn(title_bg), Write(title_text), run_time=1.0)

        # Character intro
        chars = VGroup(
            Circle(radius=0.35, fill_color="#e74c3c", fill_opacity=1, color="#e74c3c"),
            Circle(radius=0.30, fill_color="#3498db", fill_opacity=1, color="#3498db"),
            Circle(radius=0.26, fill_color="#27ae60", fill_opacity=1, color="#27ae60"),
        ).arrange(RIGHT, buff=0.3).to_edge(DOWN, buff=0.8)

        labels = VGroup(
            Text("Trishul", font_size=16, color="#e74c3c"),
            Text("Sandy",   font_size=16, color="#3498db"),
            Text("Libhu",   font_size=16, color="#27ae60"),
        )
        for label, char in zip(labels, chars):
            label.next_to(char, DOWN, buff=0.1)

        self.play(
            AnimationGroup(*[GrowFromCenter(c) for c in chars], lag_ratio=0.3),
            AnimationGroup(*[FadeIn(l) for l in labels], lag_ratio=0.3),
            run_time=0.8
        )
        self.wait(1.5)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.6)

'''

    # Individual scenes
    total = len(scenes)
    for i, scene in enumerate(scenes):
        header += generate_scene_code(scene, episode_id, i + 1, total)

    # End card
    header += f'''
class EndCard(Scene):
    def construct(self):
        bg = Rectangle(width=16, height=9, fill_color="#030810", fill_opacity=1, stroke_width=0)
        self.add(bg)

        end_text = Text("Thanks for watching!", font_size=40, color="#ffd700", weight=BOLD)
        sub_text = Text("Subscribe for more Sunridge Town adventures", font_size=22, color="#00d4ff")
        sub_text.next_to(end_text, DOWN, buff=0.4)

        chars_label = Text("Trishul · Sandy · Libhu", font_size=18, color=GREY)
        chars_label.next_to(sub_text, DOWN, buff=0.3)

        self.play(Write(end_text), run_time=0.8)
        self.play(FadeIn(sub_text), run_time=0.5)
        self.play(FadeIn(chars_label), run_time=0.4)
        self.wait(2.0)
        self.play(*[FadeOut(mob) for mob in self.mobjects], run_time=0.8)

'''

    return header


# ── Render pipeline ───────────────────────────────────────────────────────────

def render_episode(script: dict) -> dict:
    """
    Full Manim render pipeline for one episode.
    Returns {"ok": bool, "path": str, "error": str}
    """
    episode_id = script.get("episode_id", "ep_0001")
    scenes     = script.get("scenes", [])

    # Check manim available
    try:
        import manim
    except ImportError:
        return {
            "ok": False,
            "error": "Manim not installed. Run: pip install manim",
            "install_cmd": "pip install manim",
        }

    print(f"  [MANIM] Generating animation code for {episode_id}...")
    code = generate_episode_code(script)

    # Save scene file
    scene_file = MANIM_DIR / f"{episode_id}_scene.py"
    scene_file.write_text(code)
    print(f"  [MANIM] Scene file: {scene_file}")

    # Get all scene class names
    import re
    scene_classes = re.findall(r'^class (\w+)\(Scene\)', code, re.MULTILINE)
    print(f"  [MANIM] Scenes to render: {scene_classes}")

    rendered_clips = []
    for cls in scene_classes:
        out_dir = MANIM_DIR / "media" / "videos" / episode_id / "720p24"
        out_dir.mkdir(parents=True, exist_ok=True)
        clip_path = out_dir / f"{cls}.mp4"

        print(f"  [MANIM] Rendering {cls}...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "manim", str(scene_file), cls,
                 "-o", f"{cls}.mp4",
                 "--media_dir", str(MANIM_DIR / "media"),
                 "--resolution", "1280,720",
                 "--frame_rate", "24",
                 "-q", "m",   # medium quality — faster
                 "--disable_caching"],
                capture_output=True, text=True, timeout=300,
                cwd=str(MANIM_DIR)
            )
            if result.returncode == 0:
                # Find rendered file
                for p in (MANIM_DIR / "media").rglob(f"{cls}.mp4"):
                    rendered_clips.append(str(p))
                    print(f"  [MANIM] ✓ {cls} rendered")
                    break
            else:
                print(f"  [MANIM] ✗ {cls} failed: {result.stderr[-300:]}")
        except subprocess.TimeoutExpired:
            print(f"  [MANIM] ✗ {cls} timed out")
        except Exception as e:
            print(f"  [MANIM] ✗ {cls} error: {e}")

    if not rendered_clips:
        return {"ok": False, "error": "No scenes rendered. Check manim installation."}

    # Concatenate all clips
    final_path = OUTPUT_DIR / f"{episode_id}_manim.mp4"
    print(f"  [MANIM] Concatenating {len(rendered_clips)} clips...")

    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        clips = []
        for cp in rendered_clips:
            try:
                clips.append(VideoFileClip(cp))
            except Exception as e:
                print(f"  [MANIM] Warning: could not load {cp}: {e}")

        if clips:
            final = concatenate_videoclips(clips, method="compose")
            final.write_videofile(str(final_path), fps=24, codec="libx264",
                                   audio_codec="aac", verbose=False, logger=None)
            for c in clips:
                try: c.close()
                except: pass

            audit_log.record("VIDEO_RENDERED", subject=episode_id,
                             payload={"type": "manim", "path": str(final_path),
                                      "scenes": len(rendered_clips)})
            print(f"  [MANIM] ✓ Final video: {final_path}")
            return {"ok": True, "path": str(final_path), "scenes": len(rendered_clips)}
        else:
            return {"ok": False, "error": "Could not load rendered clips"}

    except ImportError:
        # moviepy not available — return first clip
        return {"ok": True, "path": rendered_clips[0], "scenes": len(rendered_clips),
                "note": "Install moviepy to concatenate: pip install moviepy"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def is_available() -> bool:
    try:
        import manim
        return True
    except ImportError:
        return False


def install_instructions() -> str:
    return """
To enable Manim 2D animation (free, same as 3Blue1Brown):

Windows:
  1. pip install manim
  2. winget install MiKTeX.MiKTeX   (for LaTeX text rendering)
  3. winget install ffmpeg
  Then restart and run APEX again.

Mac:
  brew install cairo pango ffmpeg
  pip install manim

Linux:
  sudo apt install libcairo2-dev libpango1.0-dev ffmpeg
  pip install manim
"""
