import os
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from video_processor import inspect_video, process_video

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input_videos"
OUTPUT_DIR = BASE_DIR / "output_videos"
ASSETS_DIR = BASE_DIR / "assets"
for folder in (INPUT_DIR, OUTPUT_DIR, ASSETS_DIR):
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1 GB request limit


def allowed_file(filename: str, extensions: set[str]) -> bool:
    return Path(filename).suffix.lower() in extensions


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/process")
def process():
    videos = request.files.getlist("videos")
    if not videos or all(not v.filename for v in videos):
        flash("Please select at least one MP4 video.", "error")
        return redirect(url_for("index"))

    client_name = (request.form.get("client_name") or "ANIL").strip()[:80] or "ANIL"
    brand_name = (request.form.get("brand_name") or "308 GROUP").strip()[:80] or "308 GROUP"
    event_title = (request.form.get("event_title") or "HAPPY BIRTHDAY").strip()[:100]
    subtitle = (request.form.get("subtitle") or "A CELEBRATION TO REMEMBER").strip()[:120]
    try:
        fade_duration = float(request.form.get("fade_duration", "2"))
        title_size = int(request.form.get("title_size", "64"))
        watermark_opacity = float(request.form.get("watermark_opacity", "0.45"))
        if not 0 <= fade_duration <= 10:
            raise ValueError("Fade-in must be between 0 and 10 seconds.")
        if not 20 <= title_size <= 160:
            raise ValueError("Title size must be between 20 and 160.")
        if not 0 <= watermark_opacity <= 1:
            raise ValueError("Watermark opacity must be between 0 and 1.")
    except ValueError as exc:
        flash(f"Invalid setting: {exc}", "error")
        return redirect(url_for("index"))

    show_title = request.form.get("show_title") == "on"
    show_watermark = request.form.get("show_watermark") == "on"
    watermark_image = request.files.get("watermark_image")
    watermark_path = None
    if watermark_image and watermark_image.filename:
        if not allowed_file(watermark_image.filename, ALLOWED_IMAGE_EXTENSIONS):
            flash("Watermark image must be PNG, JPG, JPEG, or WEBP.", "error")
            return redirect(url_for("index"))
        watermark_path = ASSETS_DIR / f"uploaded_watermark_{uuid.uuid4().hex[:8]}{Path(secure_filename(watermark_image.filename)).suffix.lower()}"
        watermark_image.save(watermark_path)

    job_id = uuid.uuid4().hex[:10]
    job_input = INPUT_DIR / job_id
    job_output = OUTPUT_DIR / job_id
    job_input.mkdir(parents=True, exist_ok=True)
    job_output.mkdir(parents=True, exist_ok=True)

    results = []
    errors = []
    for uploaded in videos:
        if not uploaded.filename:
            continue
        if not allowed_file(uploaded.filename, ALLOWED_VIDEO_EXTENSIONS):
            errors.append(f"{uploaded.filename}: only MP4 files are accepted.")
            continue
        safe_name = secure_filename(uploaded.filename) or f"video_{uuid.uuid4().hex}.mp4"
        source_path = job_input / safe_name
        uploaded.save(source_path)
        try:
            metadata = inspect_video(source_path)
            output_name = f"{source_path.stem}_cinematic.mp4"
            output_path = job_output / output_name
            process_video(
                source_path=source_path,
                output_path=output_path,
                client_name=client_name,
                brand_name=brand_name,
                event_title=event_title,
                subtitle=subtitle,
                fade_duration=fade_duration,
                title_size=title_size,
                watermark_opacity=watermark_opacity,
                show_title=show_title,
                show_watermark=show_watermark,
                watermark_image_path=watermark_path,
            )
            results.append({
                "name": output_name,
                "url": url_for("download_output", job_id=job_id, filename=output_name),
                "metadata": metadata,
            })
        except Exception as exc:
            errors.append(f"{uploaded.filename}: {exc}")
        finally:
            try:
                source_path.unlink(missing_ok=True)
            except OSError:
                pass

    if not results:
        flash("No videos were processed. " + " | ".join(errors[:3]), "error")
        return redirect(url_for("index"))
    return render_template("results.html", results=results, errors=errors, client_name=client_name, brand_name=brand_name)


@app.get("/download/<job_id>/<path:filename>")
def download_output(job_id, filename):
    folder = (OUTPUT_DIR / job_id).resolve()
    if OUTPUT_DIR.resolve() not in folder.parents:
        return "Invalid output path", 400
    return send_from_directory(folder, filename, as_attachment=True)


@app.post("/generate-caption")
def generate_caption():
    """Optional OpenAI-compatible API call. Basic video processing never needs an API key."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        flash("AI caption generation is optional. Set OPENAI_API_KEY in your terminal to enable it.", "error")
        return redirect(url_for("index"))
    try:
        import requests

        client_name = (request.form.get("client_name") or "ANIL").strip()[:80]
        event_title = (request.form.get("event_title") or "HAPPY BIRTHDAY").strip()[:100]
        prompt = f"Write 3 short, premium promotional captions for {event_title} for client {client_name}. Return plain text."
        response = requests.post(
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
            },
            timeout=30,
        )
        response.raise_for_status()
        caption = response.json()["choices"][0]["message"]["content"]
        return render_template("caption.html", caption=caption)
    except Exception as exc:
        flash(f"AI caption request failed: {exc}", "error")
        return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_error):
    flash("Upload is too large. Maximum request size is 1 GB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, debug=False)
 