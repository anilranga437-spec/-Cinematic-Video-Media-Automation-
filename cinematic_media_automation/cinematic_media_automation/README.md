# Cinematic Media Automation — 308 Group

A local Windows-friendly web app for batch MP4 video enhancement. Defaults are set for client **ANIL** and brand **308 GROUP**.

## Features

- Batch process multiple MP4 files in one request.
- Gold, dimensional/3D-style event title and subtitle overlay.
- Client name, brand name, event title, and subtitle are customizable.
- Optional watermark image (PNG/JPG/JPEG/WEBP) or text watermark.
- Adjustable fade-in duration, title size, and watermark opacity.
- OpenCV metadata analysis: width, height, FPS, frame count, duration, and first-frame read check.
- Separate `output_videos/<job-id>/` output folders.
- Optional AI promotional-caption generation. An API key is not required for video processing.

## Requirements

- Windows 10/11
- Python 3.10 or newer (Python 3.11/3.12 recommended)
- FFmpeg is required by MoviePy for encoding. MoviePy usually installs/uses an imageio FFmpeg binary automatically; if encoding fails, install FFmpeg and ensure it is on PATH.

## Install and run (PowerShell)

Open PowerShell in the extracted project folder:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Then open this address in your browser:

`http://127.0.0.1:5000`

If `py` is unavailable, try `python -m venv .venv`.

## How to use

1. Select one or more MP4 files.
2. Keep or change client name (default `ANIL`) and brand (default `308 GROUP`).
3. Edit event title and subtitle.
4. Enable/disable title and watermark.
5. Optionally upload a transparent PNG logo.
6. Set fade-in, title size, and watermark opacity.
7. Click **Process videos**. Download each finished video from the results page.

Output videos are stored under `output_videos/<job-id>/`. Uploaded temporary source videos are removed after processing. If processing fails, check the message on the results page or the terminal.

## Optional AI caption generation

Basic processing does not use an API key. To enable AI captions, set your key in the same PowerShell window before starting the app:

```powershell
$env:OPENAI_API_KEY = "YOUR_API_KEY_HERE"
$env:OPENAI_MODEL = "gpt-4o-mini"
python app.py
```

Keep API keys private; do not commit them to GitHub. The optional caption endpoint uses an OpenAI-compatible Chat Completions API. API availability and model access depend on your provider/account.

## Project layout

- `app.py` — Flask routes, upload validation, processing workflow, downloads, optional captions.
- `video_processor.py` — MoviePy compositing and OpenCV metadata inspection.
- `templates/` — web pages.
- `static/` — styling and UI behavior.
- `input_videos/` — temporary input storage, grouped by job.
- `output_videos/` — processed exports.
- `assets/` — optional watermark assets.

## Notes and limitations

- The title effect is a layered gold 3D-style treatment rendered into a transparent image; it is not a true 3D model.
- Large or high-resolution videos may take time and need substantial disk space.
- Use only videos and logos you have permission to process.
- The built-in Flask server is intended for local demos, not public production deployment.

# -Cinematic-Video-Media-Automation-
