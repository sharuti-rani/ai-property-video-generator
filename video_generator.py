"""
Video Generator — Composites property images, text overlays, transitions,
optional narration (gTTS), and background music into an MP4 video.
"""
import os
import logging
import tempfile
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    concatenate_videoclips,
    TextClip,
    ColorClip,
    vfx,
)

from config import (
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    VIDEO_FPS,
    SCENE_DURATION,
    TRANSITION_DURATION,
    TITLE_DURATION,
    CTA_DURATION,
    FONTS_DIR,
    ASSETS_DIR,
    TTS_LANG,
    TTS_SLOW,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _get_font_path(bold=False):
    """Try to find a usable font."""
    # Check our assets dir first
    for name in (["Montserrat-Bold.ttf"] if bold else ["Montserrat-Regular.ttf", "Montserrat-Bold.ttf"]):
        p = os.path.join(FONTS_DIR, name)
        if os.path.isfile(p):
            return p
    # Fallback to system fonts
    for p in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Pillow-based text image rendering (avoids TextClip/ImageMagick dependency)
# ---------------------------------------------------------------------------

def _render_text_image(
    text: str,
    font_size: int = 48,
    color: str = "white",
    bg_color: Optional[tuple] = None,
    max_width: int = VIDEO_WIDTH - 200,
    bold: bool = False,
    padding: int = 30,
    align: str = "center",
    shadow: bool = True,
) -> np.ndarray:
    """Render text to a NumPy RGBA array using Pillow."""
    font_path = _get_font_path(bold)
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except (OSError, IOError):
        font = ImageFont.load_default()

    # Word-wrap
    words = text.split()
    lines = []
    current_line = ""
    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)

    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = dd.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    # Measure final size
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = dd.textbbox((0, 0), line, font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    max_lw = max(line_widths) if line_widths else 100
    total_h = sum(line_heights) + (len(lines) - 1) * int(font_size * 0.4)

    img_w = max_lw + padding * 2
    img_h = total_h + padding * 2

    # Parse colour
    color_map = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "gold": (255, 215, 0, 255),
        "yellow": (255, 255, 0, 255),
    }
    fill = color_map.get(color, (255, 255, 255, 255))
    if isinstance(color, tuple):
        fill = color

    bg = bg_color if bg_color else (0, 0, 0, 0)
    img = Image.new("RGBA", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    y_cursor = padding
    for i, line in enumerate(lines):
        lw = line_widths[i]
        if align == "center":
            x = (img_w - lw) // 2
        elif align == "right":
            x = img_w - lw - padding
        else:
            x = padding

        # Drop shadow
        if shadow:
            draw.text((x + 2, y_cursor + 2), line, font=font, fill=(0, 0, 0, 160))

        draw.text((x, y_cursor), line, font=font, fill=fill)
        y_cursor += line_heights[i] + int(font_size * 0.4)

    return np.array(img)


# ---------------------------------------------------------------------------
# Scene builders
# ---------------------------------------------------------------------------

def _load_and_resize_image(path: str) -> np.ndarray:
    """Load an image, resize/crop to VIDEO_WIDTH x VIDEO_HEIGHT."""
    img = Image.open(path).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT

    if img_ratio > target_ratio:
        # Image is wider — crop sides
        new_h = img.height
        new_w = int(new_h * target_ratio)
    else:
        # Image is taller — crop top/bottom
        new_w = img.width
        new_h = int(new_w / target_ratio)

    left = (img.width - new_w) // 2
    top = (img.height - new_h) // 2
    img = img.crop((left, top, left + new_w, top + new_h))
    img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
    return np.array(img)


def _create_gradient_bg(
    color1: tuple = (15, 23, 42),
    color2: tuple = (30, 58, 95),
) -> np.ndarray:
    """Create a vertical gradient background."""
    arr = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        arr[y, :] = [
            int(color1[c] * (1 - ratio) + color2[c] * ratio) for c in range(3)
        ]
    return arr


def _build_title_clip(script: dict, duration: float) -> CompositeVideoClip:
    """Build the opening title card."""
    bg = ImageClip(_create_gradient_bg((10, 15, 30), (25, 50, 90))).with_duration(duration)

    # Title text
    title_arr = _render_text_image(
        script["title_text"], font_size=72, bold=True, color="white", shadow=True
    )
    title_clip = (
        ImageClip(title_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2 - title_arr.shape[0]))
    )

    # Subtitle
    sub_arr = _render_text_image(
        script["title_subtitle"], font_size=36, color=(200, 220, 255, 255), shadow=True
    )
    sub_clip = (
        ImageClip(sub_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2 + 30))
    )

    # Decorative line
    line_arr = np.zeros((4, 120, 4), dtype=np.uint8)
    line_arr[:, :, :3] = [255, 215, 0]
    line_arr[:, :, 3] = 255
    line_clip = (
        ImageClip(line_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2 + 10))
    )

    comp = CompositeVideoClip(
        [bg, title_clip, line_clip, sub_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    ).with_duration(duration)

    # Fade in
    comp = comp.with_effects([vfx.FadeIn(0.8)])

    return comp


def _build_scene_clip(
    image_path: str,
    caption: str,
    duration: float,
) -> CompositeVideoClip:
    """Build a single image scene with caption overlay."""
    img_arr = _load_and_resize_image(image_path)
    bg_clip = ImageClip(img_arr).with_duration(duration)

    # Ken Burns effect — slow zoom
    bg_clip = bg_clip.resized(lambda t: 1 + 0.04 * (t / duration))

    # Darken bottom for caption readability
    gradient_h = 250
    gradient = np.zeros((gradient_h, VIDEO_WIDTH, 4), dtype=np.uint8)
    for y in range(gradient_h):
        alpha = int(180 * (y / gradient_h))
        gradient[y, :, 3] = alpha
    gradient_clip = (
        ImageClip(gradient)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT - gradient_h))
    )

    # Caption text
    caption_arr = _render_text_image(
        caption, font_size=42, bold=True, color="white", shadow=True
    )
    caption_clip = (
        ImageClip(caption_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT - caption_arr.shape[0] - 50))
    )

    return CompositeVideoClip(
        [bg_clip, gradient_clip, caption_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    ).with_duration(duration)


def _build_cta_clip(script: dict, duration: float) -> CompositeVideoClip:
    """Build the closing CTA card."""
    bg = ImageClip(_create_gradient_bg((20, 10, 35), (50, 20, 70))).with_duration(duration)

    # CTA headline
    headline_arr = _render_text_image(
        script["cta_headline"], font_size=64, bold=True, color="gold", shadow=True
    )
    headline_clip = (
        ImageClip(headline_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2 - headline_arr.shape[0] - 20))
    )

    # Decorative line
    line_arr = np.zeros((3, 200, 4), dtype=np.uint8)
    line_arr[:, :, :3] = [255, 255, 255]
    line_arr[:, :, 3] = 200
    line_clip = (
        ImageClip(line_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2))
    )

    # CTA body
    body_arr = _render_text_image(
        script["cta_body"], font_size=34, color="white", shadow=True
    )
    body_clip = (
        ImageClip(body_arr)
        .with_duration(duration)
        .with_position(("center", VIDEO_HEIGHT // 2 + 30))
    )

    comp = CompositeVideoClip(
        [bg, headline_clip, line_clip, body_clip],
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    ).with_duration(duration)

    comp = comp.with_effects([vfx.FadeIn(0.6), vfx.FadeOut(1.0)])
    return comp


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _generate_tts_audio(text: str, output_path: str) -> str:
    """Generate voiceover audio using gTTS."""
    from gtts import gTTS

    tts = gTTS(text=text, lang=TTS_LANG, slow=TTS_SLOW)
    tts.save(output_path)
    logger.info(f"TTS audio saved to {output_path}")
    return output_path


def _get_background_music() -> Optional[str]:
    """Check if background music exists in assets."""
    for name in ["background_music.mp3", "bgm.mp3", "music.mp3"]:
        p = os.path.join(ASSETS_DIR, name)
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Main video generation
# ---------------------------------------------------------------------------

def generate_video(
    image_paths: list[str],
    script: dict,
    output_path: str,
    include_narration: bool = True,
    progress_callback=None,
) -> str:
    """
    Generate the complete property video.

    Args:
        image_paths: List of file paths to property images
        script: Script dict from script_generator
        output_path: Where to save the MP4
        include_narration: Whether to generate TTS narration
        progress_callback: Optional callable(step, total, message)

    Returns:
        Path to the generated MP4 file
    """
    total_steps = 5
    step = 0

    def _progress(msg):
        nonlocal step
        step += 1
        logger.info(f"[{step}/{total_steps}] {msg}")
        if progress_callback:
            progress_callback(step, total_steps, msg)

    clips = []

    # Step 1: Title card
    _progress("Creating title card...")
    title_clip = _build_title_clip(script, TITLE_DURATION)
    clips.append(title_clip)

    # Step 2: Image scenes
    _progress("Building image scenes with captions...")
    scenes = script.get("scenes", [])
    for i, img_path in enumerate(image_paths):
        caption = scenes[i]["caption"] if i < len(scenes) else ""
        scene = _build_scene_clip(img_path, caption, SCENE_DURATION)
        clips.append(scene)

    # Step 3: CTA card
    _progress("Creating closing card...")
    cta_clip = _build_cta_clip(script, CTA_DURATION)
    clips.append(cta_clip)

    # Step 4: Concatenate with cross-fade transitions
    _progress("Compositing video with transitions...")

    # Apply crossfade between clips
    transition_clips = []
    for i, clip in enumerate(clips):
        if i == 0:
            transition_clips.append(clip)
        else:
            # Use crossfade transitions
            clip = clip.with_effects([vfx.FadeIn(TRANSITION_DURATION)])
            clip = clip.with_start(
                sum(c.duration for c in clips[:i]) - TRANSITION_DURATION * i
            )
            transition_clips.append(clip)

    total_duration = (
        sum(c.duration for c in clips) - TRANSITION_DURATION * (len(clips) - 1)
    )

    video = CompositeVideoClip(
        transition_clips,
        size=(VIDEO_WIDTH, VIDEO_HEIGHT),
    ).with_duration(total_duration)

    # Step 5: Audio
    _progress("Adding audio...")
    audio_clips = []

    # TTS narration
    if include_narration and script.get("full_voiceover"):
        try:
            tts_path = os.path.join(
                tempfile.gettempdir(), "property_video_narration.mp3"
            )
            _generate_tts_audio(script["full_voiceover"], tts_path)
            narration = AudioFileClip(tts_path)
            # Trim narration if longer than video
            if narration.duration > total_duration:
                narration = narration.subclipped(0, total_duration)
            audio_clips.append(narration)
        except Exception as e:
            logger.warning(f"TTS narration failed: {e}")

    # Background music
    bgm_path = _get_background_music()
    if bgm_path:
        try:
            bgm = AudioFileClip(bgm_path)
            # Loop if needed
            if bgm.duration < total_duration:
                repeats = int(total_duration / bgm.duration) + 1
                from moviepy import concatenate_audioclips

                bgm = concatenate_audioclips([bgm] * repeats)
            bgm = bgm.subclipped(0, total_duration)
            # Lower volume if narration present
            if audio_clips:
                bgm = bgm.with_effects([vfx.MultiplyVolume(0.15)])
            else:
                bgm = bgm.with_effects([vfx.MultiplyVolume(0.4)])
            audio_clips.append(bgm)
        except Exception as e:
            logger.warning(f"Background music failed: {e}")

    if audio_clips:
        final_audio = CompositeAudioClip(audio_clips)
        video = video.with_audio(final_audio)

    # Export
    logger.info(f"Exporting video to {output_path}...")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # video.write_videofile(
    #     output_path,
    #     fps=VIDEO_FPS,
    #     codec="libx264",
    #     audio_codec="aac",
    #     preset="medium",
    #     threads=4,
    #     logger="bar",
    # )

    
video.write_videofile(
    output_path,
    fps=VIDEO_FPS,
    codec="libx264",
    audio_codec="aac",
    preset="ultrafast",
    threads=1,
    logger=None,
)


    # Clean up clips
    video.close()
    for c in clips:
        c.close()

    logger.info(f"[OK] Video saved to {output_path}")
    return output_path
