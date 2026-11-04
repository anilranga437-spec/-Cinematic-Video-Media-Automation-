from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, vfx


def inspect_video(path: Path) -> dict:
    """Read basic video metadata with OpenCV."""
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("OpenCV could not open this video. Check that it is a valid MP4.")
    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        ok, frame = capture.read()
        first_frame_ok = bool(ok and frame is not None)
        return {
            "width": width, "height": height, "fps": round(fps, 2),
            "frame_count": frame_count, "duration": round(duration, 2),
            "first_frame_readable": first_frame_ok,
        }
    finally:
        capture.release()


def _font(size: int, bold: bool = True):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_font(draw, text, max_width, size, bold=True):
    size = max(12, size)
    while size > 12:
        font = _font(size, bold)
        box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
        if box[2] - box[0] <= max_width:
            return font
        size -= 2
    return _font(12, bold)


def _make_overlay(width, height, client_name, brand_name, event_title, subtitle,
                  title_size, show_title, show_watermark, watermark_opacity,
                  watermark_image_path=None):
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    max_width = int(width * 0.88)

    if show_title:
        main_text = f"{event_title} {client_name}".strip().upper()
        font = _fit_font(draw, main_text, max_width, title_size)
        box = draw.textbbox((0, 0), main_text, font=font, stroke_width=2)
        text_width, text_height = box[2] - box[0], box[3] - box[1]
        x = (width - text_width) // 2
        y = int(height * 0.68)

        # Layered shadow and highlights create a gold, dimensional 3D-style look.
        for offset, color in [(7, (30, 15, 0, 220)), (5, (95, 47, 0, 240)), (3, (155, 87, 12, 255))]:
            draw.text((x + offset, y + offset), main_text, font=font, fill=color,
                      stroke_width=2, stroke_fill=(35, 20, 0, 255))
        draw.text((x, y), main_text, font=font, fill=(255, 211, 92, 255),
                  stroke_width=2, stroke_fill=(255, 242, 180, 255))
        if subtitle:
            sub_font = _fit_font(draw, subtitle, max_width, max(18, title_size // 3), bold=False)
            sub_box = draw.textbbox((0, 0), subtitle, font=sub_font)
            sub_x = (width - (sub_box[2] - sub_box[0])) // 2
            draw.text((sub_x, y + text_height + 16), subtitle, font=sub_font,
                      fill=(255, 255, 255, 235), stroke_width=2, stroke_fill=(0, 0, 0, 160))

    if show_watermark:
        alpha = int(255 * watermark_opacity)
        if watermark_image_path and Path(watermark_image_path).is_file():
            try:
                logo = Image.open(watermark_image_path).convert("RGBA")
                max_logo_w = max(100, width // 5)
                scale = min(max_logo_w / logo.width, (height // 5) / logo.height, 1.0)
                logo = logo.resize((max(1, int(logo.width * scale)), max(1, int(logo.height * scale))))
                logo.putalpha(logo.getchannel("A").point(lambda value: int(value * watermark_opacity)))
                overlay.alpha_composite(logo, (width - logo.width - 24, 24))
            except Exception:
                pass
        else:
            wm_font = _fit_font(draw, brand_name.upper(), width // 3, max(20, width // 28))
            draw.text((width - width // 3 - 24, 24), brand_name.upper(), font=wm_font,
                      fill=(255, 220, 130, alpha), stroke_width=2, stroke_fill=(0, 0, 0, alpha // 2))
    return np.array(overlay)


def process_video(source_path: Path, output_path: Path, client_name: str, brand_name: str,
                  event_title: str, subtitle: str, fade_duration: float, title_size: int,
                  watermark_opacity: float, show_title: bool, show_watermark: bool,
                  watermark_image_path: Path | None = None):
    clip = None
    final_clip = None
    try:
        clip = VideoFileClip(str(source_path))
        width, height = clip.size
        if not clip.duration or clip.duration <= 0:
            raise ValueError("Video duration is zero or unreadable.")
        overlay_array = _make_overlay(
            width, height, client_name, brand_name, event_title, subtitle, title_size,
            show_title, show_watermark, watermark_opacity, watermark_image_path
        )
        overlay_clip = ImageClip(overlay_array).with_duration(clip.duration)
        final_clip = CompositeVideoClip([clip, overlay_clip], size=(width, height))
        if fade_duration > 0:
            final_clip = final_clip.with_effects([vfx.FadeIn(min(fade_duration, clip.duration))])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_clip.write_videofile(
            str(output_path), codec="libx264", audio_codec="aac",
            fps=clip.fps or 24, preset="medium", logger=None,
            threads=2, ffmpeg_params=["-pix_fmt", "yuv420p"]
        )
    finally:
        if final_clip is not None:
            try:
                final_clip.close()
            except Exception:
                pass
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass
