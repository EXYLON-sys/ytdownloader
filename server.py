from fastapi import FastAPI, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import flet.fastapi as flet_fastapi
from app.main_flet import main as flet_main

import os, re, subprocess, json, shutil, uuid
import yt_dlp
import uvicorn

# -------------------------------
# CONFIG
# -------------------------------
app = FastAPI()
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
SETTINGS_FILE = "settings.json"
FFMPEG_PATH = "ffmpeg"  # assumes ffmpeg is in PATH

# -------------------------------
# HELPERS
# -------------------------------
def safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", name)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"format": "MP3", "threads": 3}

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()

# -------------------------------
# STATIC + FLET APP ROUTES
# -------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# Mount Flet app at /app (not as default)
flet_app = flet_fastapi.app(target=flet_main)
app.mount("/app", flet_app)

# -------------------------------
# DOWNLOAD ENDPOINT
# -------------------------------
@app.post("/download")
def download_youtube(url: str = Form(...), format: str = Form(None)):
    fmt = format if format else settings.get("format", "MP3")
    temp_folder = os.path.join(DOWNLOAD_DIR, str(uuid.uuid4()))
    os.makedirs(temp_folder, exist_ok=True)

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(temp_folder, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Playlist handling
            if "entries" in info:
                files = []
                for entry in info["entries"]:
                    filename = ydl.prepare_filename(entry)
                    base, _ = os.path.splitext(filename)
                    output_file = f"{base}.{fmt.lower()}"
                    subprocess.run(
                        [FFMPEG_PATH, "-y", "-i", filename, "-vn", "-ar", "44100", output_file],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    os.remove(filename)
                    files.append(output_file)

                zip_name = safe_filename(info["title"]) + ".zip"
                zip_path = os.path.join(DOWNLOAD_DIR, zip_name)
                shutil.make_archive(zip_path.replace(".zip", ""), "zip", temp_folder)
                shutil.rmtree(temp_folder)
                settings["format"] = fmt
                save_settings(settings)
                return JSONResponse({"status": "ok", "file": zip_name, "title": info["title"], "is_playlist": True})

            # Single video
            else:
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                output_file = f"{base}.{fmt.lower()}"
                subprocess.run(
                    [FFMPEG_PATH, "-y", "-i", filename, "-vn", "-ar", "44100", output_file],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                os.remove(filename)
                settings["format"] = fmt
                save_settings(settings)
                return JSONResponse({
                    "status": "ok",
                    "file": os.path.basename(output_file),
                    "title": info["title"],
                    "is_playlist": False
                })

    except Exception as e:
        shutil.rmtree(temp_folder, ignore_errors=True)
        return JSONResponse({"status": "error", "message": str(e)})

# -------------------------------
# SERVE FILES FOR DOWNLOAD
# -------------------------------
@app.get("/files/{filename}")
def serve_file(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
    return JSONResponse({"status": "error", "message": "File not found"})

# -------------------------------
# DEVELOPER COMMAND CONSOLE
# -------------------------------
@app.post("/command")
def developer_command(cmd: str = Form(...)):
    cmd = cmd.strip().lower()
    if cmd == "help":
        return {"response": "Available commands: help, clear, status"}
    elif cmd == "status":
        return {"response": "Backend online ✅"}
    elif cmd == "clear":
        return {"response": ""}
    else:
        return {"response": f"Unknown command: {cmd}"}


# -------------------------------
# ENTRY POINT (Render compatibility)
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
