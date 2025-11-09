import flet as ft
import yt_dlp
import os, re, subprocess, json
from threading import Thread

FFMPEG_PATH = "ffmpeg"
CONFIG_FILE = "settings.json"

def safe_filename(name: str) -> str:
    return re.sub(r'[<>:\"/\\|?*]', "", name)

def save_settings(settings):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)

def load_settings():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"format": "MP3", "threads": 5, "output_folder": "downloads"}

def main(page: ft.Page):
    page.title = "🎵 YouTube Playlist Downloader (Web)"
    page.theme_mode = "dark"
    page.scroll = "auto"

    settings = load_settings()
    os.makedirs(settings["output_folder"], exist_ok=True)

    url_box = ft.TextField(label="YouTube URL or playlist", expand=True)
    format_dropdown = ft.Dropdown(
        label="Formátum",
        options=[ft.dropdown.Option(fmt) for fmt in ["MP3", "WAV", "FLAC", "OGG"]],
        value=settings.get("format", "MP3")
    )
    start_button = ft.ElevatedButton("▶️ Letöltés indítása", bgcolor="green", color="white")

    progress = ft.ProgressBar(width=600, value=0)
    log_box = ft.TextField(value="", multiline=True, min_lines=10, expand=True, read_only=True)
    status_label = ft.Text("", size=16, color="green")

    def log(msg):
        log_box.value += msg + "\n"
        page.update()

    def download_video(url, folder, file_format):
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
                "quiet": True,
                "no_warnings": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            base, _ = os.path.splitext(filename)
            output_file = base + f".{file_format.lower()}"
            cmd = [FFMPEG_PATH, "-y", "-i", filename, "-vn", "-ar", "44100", output_file]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            os.remove(filename)
            return {"status": "ok", "file": output_file, "title": info["title"]}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def start_download(e):
        url = url_box.value.strip()
        if not url:
            log("❌ Nincs megadva URL!")
            return

        save_settings({
            "format": format_dropdown.value,
            "threads": 3,
            "output_folder": settings["output_folder"],
        })

        def worker():
            log(f"🔗 Letöltés indul: {url}")
            result = download_video(url, settings["output_folder"], format_dropdown.value)
            if result["status"] == "ok":
                log(f"✅ {result['title']} kész")
                page.snack_bar = ft.SnackBar(ft.Text(f"{result['title']} letöltve!"))
                page.snack_bar.open = True
                page.update()
            else:
                log(f"❌ Hiba: {result['message']}")
            status_label.value = "✅ Kész!"
            page.update()

        Thread(target=worker, daemon=True).start()

    start_button.on_click = start_download

    page.add(
        ft.Column([
            ft.Row([url_box, format_dropdown]),
            start_button,
            ft.Divider(),
            progress,
            log_box,
            status_label,
            ft.Text("Verzió: Web 1.0", size=12, italic=True),
        ])
    )

ft.app(target=main, view=ft.WEB_BROWSER)
