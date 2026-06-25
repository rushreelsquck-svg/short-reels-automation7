"""
build_video.py
Assembles the final 1080x1920 vertical video — one scene per fact (plus the
opening hook), each scene getting its OWN real Pexels stock clip matched to
that specific fact, played at its natural motion (no artificial zoom/pan —
the real footage's own camera movement does that job, and cutting often
between distinct real clips is what gives this genre its pace). Falls back
to the synthetic gradient only if Pexels isn't configured or a specific
clip can't be found.

Each fact scene gets a small number badge ("#1", "#2"...) in the corner plus
a caption of its narration text; the hook scene just gets its caption.
"""
import math
import random
import textwrap
from pathlib import Path
import os

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS  # Pillow >=10 compatibility shim for moviepy 1.0.3

from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
    afx,
)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "Anton-Regular.ttf"
MUSIC_DIR = ASSETS_DIR / "music"

W, H = 1080, 1920
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")


def _render_caption_png(text, font_size=68, max_width=950):
    font = ImageFont.truetype(str(FONT_PATH), font_size)
    wrapped = textwrap.fill(text, width=18)
    lines = wrapped.split("\n")

    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    line_h = max(d.textbbox((0, 0), line, font=font)[3] for line in lines) + 20
    img_h = line_h * len(lines) + 46

    img = Image.new("RGBA", (max_width, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, max_width, img_h], radius=26, fill=(0, 0, 0, 145))
    for idx, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (max_width - line_w) / 2
        y = 23 + idx * line_h
        draw.text((x, y), line, font=font, fill="white", stroke_width=5, stroke_fill="black")
    return np.array(img)


def _render_badge_png(number, size=160):
    font = ImageFont.truetype(str(FONT_PATH), int(size * 0.5))
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size, size], fill=(230, 60, 60, 235))
    text = f"#{number}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - bbox[1]), text, font=font, fill="white")
    return np.array(img)


def _fetch_pexels_clip(query, duration):
    if not PEXELS_API_KEY:
        return None
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "orientation": "portrait", "per_page": 5},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("videos", [])
        if not results:
            return None
        video = random.choice(results)
        files = sorted(video["video_files"], key=lambda f: f.get("width", 0))
        portrait = [f for f in files if f.get("height", 0) > f.get("width", 0)]
        pick = (portrait or files)[-1]

        local_path = f"/tmp/pexels_bg_{abs(hash(query))}.mp4"
        with requests.get(pick["link"], stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        clip = VideoFileClip(local_path)
        clip = clip.resize(height=H) if (clip.h / clip.w) > (H / W) else clip.resize(width=W)
        clip = clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=W, height=H)

        if clip.duration < duration:
            clip = concatenate_videoclips([clip] * math.ceil(duration / clip.duration))
        clip = clip.subclip(0, duration)
        clip = clip.fl_image(lambda frame: (frame * 0.6).astype("uint8"))  # darken for caption legibility
        return clip
    except Exception:
        return None


def _make_gradient_background(duration, color_a=(20, 20, 45), color_b=(95, 20, 110)):
    yy, xx = np.mgrid[0:H, 0:W]
    diag = (xx + yy) / (W + H)

    def make_frame(t):
        progress = (math.sin(t * 0.4) + 1) / 2
        mix = np.array(color_a) * (1 - progress) + np.array(color_b) * progress
        shift = 0.15 * math.sin(t * 0.6)
        frame = np.zeros((H, W, 3), dtype=np.uint8)
        for c in range(3):
            variation = 40 * np.sin(2 * math.pi * (diag + shift))
            frame[:, :, c] = np.clip(mix[c] + variation, 0, 255)
        return frame

    return VideoClip(make_frame, duration=duration)


def build_video(scenes, output_path):
    """
    scenes: list of dicts, each with keys: audio_path, visual_query (or None
    for the hook scene), caption_text, number (or None for the hook scene)
    """
    visual_clips = []
    overlay_clips = []
    audio_clips = []
    t_cursor = 0.0

    for scene in scenes:
        voice = AudioFileClip(scene["audio_path"])
        duration = voice.duration + 0.3
        audio_clips.append(voice.set_start(t_cursor))

        bg = _fetch_pexels_clip(scene["visual_query"], duration) if scene.get("visual_query") else None
        if bg is None:
            bg = _make_gradient_background(duration)
        bg = bg.set_duration(duration).resize((W, H)).set_start(t_cursor)
        visual_clips.append(bg)

        caption_png = _render_caption_png(scene["caption_text"])
        caption_clip = (
            ImageClip(caption_png)
            .set_start(t_cursor)
            .set_duration(duration)
            .set_position(("center", int(H * 0.66)))
        )
        overlay_clips.append(caption_clip)

        if scene.get("number"):
            badge_png = _render_badge_png(scene["number"])
            badge_clip = (
                ImageClip(badge_png)
                .set_start(t_cursor)
                .set_duration(duration)
                .set_position((40, 120))
            )
            overlay_clips.append(badge_clip)

        t_cursor += duration

    total_duration = t_cursor

    audio_tracks = list(audio_clips)
    music_files = list(MUSIC_DIR.glob("*.mp3"))
    if music_files:
        music = AudioFileClip(str(random.choice(music_files))).fx(afx.audio_loop, duration=total_duration)
        music = music.fx(afx.volumex, 0.10)
        audio_tracks.append(music)

    final_audio = CompositeAudioClip(audio_tracks).set_duration(total_duration)
    final_video = CompositeVideoClip([*visual_clips, *overlay_clips], size=(W, H)).set_duration(total_duration)
    final_video = final_video.set_audio(final_audio)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    final_video.write_videofile(
        output_path, fps=30, codec="libx264", audio_codec="aac", threads=4, preset="medium", logger=None
    )
    return output_path
