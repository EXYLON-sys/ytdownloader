import flet as ft
import requests
from threading import Thread
import os, json

BACKEND_URL = "http://127.0.0.1:8000"

SETTINGS_FILE = "settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"format": "MP3"}

settings = load_settings()

def main(page: ft.Page):
    page.title = "🎵 YouTube Downloader (Web)"
    page.theme_mode = "dark"
    page.scroll = "auto"

    url_box = ft.TextField(label="YouTube URL(s) comma-separated", expand=True)
    format_dropdown = ft.Dropdown(
        label="Format",
        options=[ft.dropdown.Option(fmt) for fmt in ["MP3","WAV","FLAC","OGG"]],
        value=settings.get("format", "MP3")
    )
    start_button = ft.ElevatedButton("▶️ Download", bgcolor="green", color="white")
    log_box = ft.TextField(value="", multiline=True, min_lines=10, expand=True, read_only=True)
    status_label = ft.Text("", size=16, color="green")
    download_buttons = ft.Column()

    # Developer console
    console_box = ft.TextField(label="Dev Console", multiline=True, min_lines=8, expand=True, read_only=True, visible=False)
    console_input = ft.TextField(hint_text="Commands (help, clear, status)...", visible=False)

    def log(msg):
        log_box.value += msg + "\n"
        page.update()

    def add_download_button(filename, title):
        btn = ft.ElevatedButton(f"Download: {title}", on_click=lambda e: download_file(filename))
        download_buttons.controls.append(btn)
        page.update()

    def download_file(filename):
        import webbrowser
        webbrowser.open(f"{BACKEND_URL}/files/{filename}")

    # --- Download logic ---
    def start_download(e):
        urls = [u.strip() for u in url_box.value.split(",") if u.strip()]
        fmt = format_dropdown.value
        if not urls:
            log("❌ No URLs provided!")
            return

        def worker():
            download_buttons.controls.clear()
            for url in urls:
                log(f"🔗 Sending to server: {url}")
                try:
                    resp = requests.post(f"{BACKEND_URL}/download", data={"url": url, "format": fmt})
                    data = resp.json()
                    if data["status"]=="ok":
                        log(f"✅ {data['title']} ready")
                        add_download_button(data["file"], data["title"])
                        status_label.value = "✅ Done!"
                    else:
                        log(f"❌ Error: {data['message']}")
                        status_label.value = "❌ Error occurred"
                except Exception as ex:
                    log(f"⚠️ Network error: {ex}")
                    status_label.value = "⚠️ Network error"
                page.update()
        Thread(target=worker, daemon=True).start()

    start_button.on_click = start_download

    # --- Developer console ---
    def handle_console(cmd: str):
        def worker():
            try:
                resp = requests.post(f"{BACKEND_URL}/command", data={"cmd": cmd})
                data = resp.json()
                if cmd=="clear":
                    console_box.value = ""
                else:
                    console_box.value += f"> {cmd}\n{data['response']}\n"
                console_input.value = ""
                page.update()
            except Exception as ex:
                console_box.value += f"⚠️ Error: {ex}\n"
                page.update()
        Thread(target=worker, daemon=True).start()

    console_input.on_submit = lambda e: handle_console(console_input.value.strip())

    dev_button = ft.ElevatedButton("🛠️ Dev Mode", bgcolor="blue", color="white")
    def open_dev(e):
        code_box = ft.TextField(password=True, hint_text="Enter code...")
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Developer Mode"),
            content=code_box,
            actions=[ft.TextButton("OK", on_click=lambda ev: unlock_console(code_box))]
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def unlock_console(code_box):
        if code_box.value.strip()=="qwertz112233":
            page.dialog.open=False
            console_box.visible=True
            console_input.visible=True
            console_box.value += "\n🔓 Developer Mode Enabled\n"
        else:
            code_box.value=""
            code_box.hint_text="❌ Wrong code"
        page.update()

    dev_button.on_click = open_dev

    page.add(ft.Column([
        ft.Row([url_box, format_dropdown]),
        ft.Row([start_button, dev_button]),
        ft.Divider(),
        log_box,
        status_label,
        download_buttons,
        ft.Divider(),
        ft.Text("🧑‍💻 Developer Console", size=14, weight="bold"),
        console_box,
        console_input,
        ft.Text("Version: 3.0 Web + Backend", size=12, italic=True),
    ]))

ft.app(target=main, view=ft.AppView.WEB_BROWSER)
