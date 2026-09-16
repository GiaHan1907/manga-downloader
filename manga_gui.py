#!/usr/bin/env python3
"""Simple Windows GUI for download_manga.py."""

from __future__ import annotations

import queue
import re
import threading
import zipfile
import json
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import requests
from PIL import Image, ImageOps

import download_manga as downloader

try:
    import pystray
    from PIL import ImageDraw
except ImportError:  # Tray support is optional during source-based development.
    pystray = None
    ImageDraw = None

try:
    import winsound
except ImportError:  # Keep the GUI importable on non-Windows systems.
    winsound = None


def resource_path(filename: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / filename


UI_TEXT = {
    "en": {
        "window_title": "Manga Downloader",
        "tagline": "Reader & archive workspace",
        "nav_downloader": "▣   Downloader",
        "nav_archive": "▤   History",
        "nav_settings": "⚙   Settings",
        "local_workspace": "●  LOCAL WORKSPACE",
        "local_description": "Files stay on this computer",
        "header_title": "Download manga",
        "header_subtitle": "Download chapters, convert formats, and build a local CBZ library.",
        "source": "SOURCE",
        "chapter_url": "Chapter URL",
        "download_scope": "DOWNLOAD SCOPE",
        "chapter_count": "Number of chapters",
        "one_chapter": "1 chapter",
        "five_chapters": "5 chapters",
        "ten_chapters": "10 chapters",
        "all_chapters": "All chapters",
        "output": "OUTPUT",
        "archive_options": "Archive options",
        "webp_jpg": "WebP → JPG",
        "create_cbz": "Create CBZ",
        "redownload": "Re-download existing images",
        "output_folder": "OUTPUT FOLDER",
        "choose_folder": "Choose folder",
        "start": "▶  Start download",
        "stop": "■  Stop",
        "delay": "Delay between images",
        "activity_log": "ACTIVITY LOG",
        "clear_log": "Clear log",
        "privacy": "Only download content you are allowed to use.",
        "language": "Language",
        "page_not_started": "Chapter progress: not started",
        "overall_not_started": "Overall progress: not started",
        "ready": "Ready",
        "downloading": "Downloading...",
        "delay_invalid": "Delay must be greater than or equal to 0.",
        "preparing": "Chapter progress: preparing...",
        "overall_fixed": "Overall progress: 0/{count} chapters",
        "overall_all": "Overall progress: downloading all chapters",
        "started": "Started: {url}",
        "downloading_chapter": "Downloading chapter {number}: {url}",
        "converted": "Converted {count} WebP images to JPG.",
        "created_cbz": "Created CBZ: {path}",
        "completed_chapter": "Completed {title} ({count} images).",
        "no_next": "No next-chapter link was found.",
        "completed_all": "Completed {count} chapters.",
        "stopping": "Stopping after the current request...",
        "stopped": "Stopped by user request.",
        "network_error": "Network error",
        "generic_error": "Error",
        "invalid_settings": "Invalid settings",
        "missing_folder": "Missing folder",
        "choose_folder_first": "Choose an output folder first.",
        "download_failed": "Download failed",
        "download_complete": "Download complete",
        "page_progress": "Chapter progress: {chapter} — {current}/{total} pages",
        "status_downloading": "Downloading {chapter}",
        "overall_progress": "Overall progress: {current}/{total} chapters",
        "overall_all_progress": "Overall progress: {current} chapters completed",
        "status_stopped": "Stopped",
        "status_complete": "Complete",
        "status_error": "Error",
        "history": "DOWNLOAD HISTORY",
        "history_time": "Time",
        "history_source": "Source",
        "history_status": "Status",
        "history_details": "Details",
        "tray_show": "Show window",
        "tray_exit": "Exit",
        "tray_hint": "Manga Downloader is still running in the system tray.",
        "ui_badge": "MANUS WORKSPACE",
        "search_history": "Search manga, URL, or status",
        "settings_title": "Workspace settings",
        "settings_note": "Download defaults and appearance controls will be expanded in a later phase.",
        "settings_output": "Current output folder",
    },
    "vi": {
        "window_title": "Manga Downloader",
        "tagline": "Không gian tải và lưu trữ truyện",
        "nav_downloader": "▣   Trình tải truyện",
        "nav_archive": "▤   Lịch sử tải",
        "nav_settings": "⚙   Cài đặt",
        "local_workspace": "●  KHÔNG GIAN CỤC BỘ",
        "local_description": "Tệp được lưu trên máy này",
        "header_title": "Tải truyện",
        "header_subtitle": "Tải chương, chuyển đổi định dạng và xây dựng thư viện CBZ.",
        "source": "NGUỒN TRUYỆN",
        "chapter_url": "Link chapter",
        "download_scope": "PHẠM VI TẢI",
        "chapter_count": "Số chương muốn tải",
        "one_chapter": "1 chương",
        "five_chapters": "5 chương",
        "ten_chapters": "10 chương",
        "all_chapters": "Toàn bộ",
        "output": "ĐẦU RA",
        "archive_options": "Tùy chọn lưu trữ",
        "webp_jpg": "WebP → JPG",
        "create_cbz": "Tạo CBZ",
        "redownload": "Tải lại ảnh đã có",
        "output_folder": "THƯ MỤC LƯU",
        "choose_folder": "Chọn thư mục",
        "start": "▶  Bắt đầu tải",
        "stop": "■  Dừng",
        "delay": "Độ trễ giữa ảnh",
        "activity_log": "NHẬT KÝ HOẠT ĐỘNG",
        "clear_log": "Xóa nhật ký",
        "privacy": "Chỉ tải nội dung bạn được phép sử dụng.",
        "language": "Ngôn ngữ",
        "page_not_started": "Tiến trình chương: chưa bắt đầu",
        "overall_not_started": "Tổng tiến trình: chưa bắt đầu",
        "ready": "Sẵn sàng",
        "downloading": "Đang tải...",
        "delay_invalid": "Độ trễ phải lớn hơn hoặc bằng 0.",
        "preparing": "Tiến trình chương: đang chuẩn bị...",
        "overall_fixed": "Tổng tiến trình: 0/{count} chương",
        "overall_all": "Tổng tiến trình: đang tải toàn bộ",
        "started": "Bắt đầu: {url}",
        "downloading_chapter": "Đang tải chương {number}: {url}",
        "converted": "Đã chuyển {count} ảnh WebP sang JPG.",
        "created_cbz": "Đã tạo CBZ: {path}",
        "completed_chapter": "Hoàn tất {title} ({count} ảnh).",
        "no_next": "Không tìm thấy liên kết chương kế tiếp.",
        "completed_all": "Đã hoàn tất {count} chương.",
        "stopping": "Đang dừng sau yêu cầu hiện tại...",
        "stopped": "Đã dừng theo yêu cầu.",
        "network_error": "Lỗi mạng",
        "generic_error": "Lỗi",
        "invalid_settings": "Thiết lập chưa đúng",
        "missing_folder": "Thiếu thư mục",
        "choose_folder_first": "Hãy chọn thư mục lưu trước.",
        "download_failed": "Tải thất bại",
        "download_complete": "Tải hoàn tất",
        "page_progress": "Tiến trình chương: {chapter} — {current}/{total} trang",
        "status_downloading": "Đang tải {chapter}",
        "overall_progress": "Tổng tiến trình: {current}/{total} chương",
        "overall_all_progress": "Tổng tiến trình: đã xong {current} chương",
        "status_stopped": "Đã dừng",
        "status_complete": "Hoàn tất",
        "status_error": "Có lỗi",
        "history": "LỊCH SỬ TẢI XUỐNG",
        "history_time": "Thời gian",
        "history_source": "Nguồn",
        "history_status": "Trạng thái",
        "history_details": "Chi tiết",
        "tray_show": "Mở cửa sổ",
        "tray_exit": "Thoát",
        "tray_hint": "Manga Downloader vẫn đang chạy trong khay hệ thống.",
        "ui_badge": "MANUS WORKSPACE",
        "search_history": "Tìm manga, URL hoặc trạng thái",
        "settings_title": "Cài đặt không gian làm việc",
        "settings_note": "Các thiết lập tải xuống và giao diện sẽ được mở rộng ở phase tiếp theo.",
        "settings_output": "Thư mục lưu hiện tại",
    },
}


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def convert_webp_to_jpg(chapter_dir: Path) -> int:
    """Create JPG copies of WebP pages; preserve original WebP files."""
    converted = 0
    for source in sorted(chapter_dir.glob("*.webp"), key=natural_key):
        target = source.with_suffix(".jpg")
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.save(target, "JPEG", quality=95, optimize=True)
        converted += 1
    return converted


def chapter_images(chapter_dir: Path) -> list[Path]:
    extensions = {".jpg", ".jpeg", ".png", ".gif", ".avif", ".webp"}
    files = [p for p in chapter_dir.iterdir() if p.is_file() and p.suffix.lower() in extensions]
    # When a WebP was converted, do not put both copies into the CBZ archive.
    return sorted(
        [p for p in files if not (p.suffix.lower() == ".webp" and p.with_suffix(".jpg").exists())],
        key=natural_key,
    )


def create_cbz(chapter_dir: Path) -> Path:
    images = chapter_images(chapter_dir)
    if not images:
        raise RuntimeError(f"No images available to create CBZ: {chapter_dir.name}")
    cbz_path = chapter_dir.parent / f"{chapter_dir.name}.cbz"
    with zipfile.ZipFile(cbz_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for image in images:
            archive.write(image, arcname=image.name)
    return cbz_path


class MangaGui:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Manga Downloader · Manus Workspace")
        self.root.geometry("1180x800")
        self.root.minsize(1000, 700)
        self.icon_photo = tk.PhotoImage(file=str(resource_path("MangaDownloader.png")))
        self.root.iconphoto(True, self.icon_photo)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.closing = False
        self.tray_icon = None
        self.history_file = self.get_history_file()
        self.history_records: list[dict[str, str]] = []
        self.current_history_id: str | None = None
        self.load_history()
        self.current_page = "downloader"
        self.page_frames: dict[str, tk.Widget] = {}

        self.url_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.language_var = tk.StringVar(value="en")
        self.text_widgets = {}
        self.chapter_count = tk.IntVar(value=1)
        self.delay_var = tk.DoubleVar(value=1.0)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.convert_var = tk.BooleanVar(value=True)
        self.cbz_var = tk.BooleanVar(value=True)
        self.history_search_var = tk.StringVar(value="")
        self.page_progress_text = tk.StringVar(value=UI_TEXT["en"]["page_not_started"])
        self.overall_progress_text = tk.StringVar(value=UI_TEXT["en"]["overall_not_started"])
        self.status_text = tk.StringVar(value=UI_TEXT["en"]["ready"])

        self.setup_theme()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_tray()
        self.root.after(100, self.process_events)

    @staticmethod
    def get_history_file() -> Path:
        base = Path.home() / "AppData" / "Roaming" / "MangaDownloader"
        if sys.platform != "win32":
            base = Path.home() / ".manga-downloader"
        base.mkdir(parents=True, exist_ok=True)
        return base / "download_history.json"

    def load_history(self):
        try:
            self.history_records = json.loads(self.history_file.read_text(encoding="utf-8"))
            if not isinstance(self.history_records, list):
                self.history_records = []
        except (OSError, ValueError):
            self.history_records = []

    def save_history(self):
        try:
            self.history_file.write_text(json.dumps(self.history_records[-100:], ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def text(self, key: str, language: str | None = None, **values) -> str:
        language = language or self.language_var.get()
        return UI_TEXT[language][key].format(**values)

    def register_text(self, key: str, widget):
        self.text_widgets[key] = widget
        return widget

    def tray_image(self):
        try:
            with Image.open(resource_path("MangaDownloader.png")) as source:
                return source.convert("RGBA").resize((64, 64), Image.Resampling.LANCZOS)
        except (OSError, ValueError):
            image = Image.new("RGBA", (64, 64), (124, 92, 255, 255))
            if ImageDraw is not None:
                draw = ImageDraw.Draw(image)
                draw.ellipse((10, 10, 54, 54), fill=(17, 24, 35, 255), outline=(241, 245, 249, 255), width=3)
            return image

    def start_tray(self):
        if pystray is None:
            return
        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: self.text("tray_show"), lambda _icon, _item: self.show_window()),
            pystray.MenuItem(lambda _item: self.text("tray_exit"), lambda _icon, _item: self.exit_application()),
        )
        self.tray_icon = pystray.Icon("manga_downloader", self.tray_image(), "Manga Downloader", menu)
        threading.Thread(target=self.tray_icon.run, name="system-tray", daemon=True).start()

    def show_window(self):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self):
        if self.closing:
            return
        if self.tray_icon is None:
            self._exit_application()
            return
        if self.worker and self.worker.is_alive():
            self.root.withdraw()
            return
        self.root.withdraw()

    def exit_application(self):
        self.root.after(0, self._exit_application)

    def _exit_application(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
        self.closing = True
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.root.destroy()

    def add_history(self, url: str, output_root: Path, selected_count: int):
        record = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": url,
            "output": str(output_root),
            "status": "Downloading",
            "details": "0 chapters completed",
        }
        self.current_history_id = record["id"]
        self.history_records.append(record)
        self.save_history()
        self.refresh_history()

    def update_history(self, status: str, details: str):
        if not self.current_history_id:
            return
        for record in reversed(self.history_records):
            if record.get("id") == self.current_history_id:
                record["status"] = status
                record["details"] = details
                break
        self.save_history()
        self.refresh_history()

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        trees = [self.history_tree]
        if hasattr(self, "history_detail_tree"):
            trees.append(self.history_detail_tree)
        query = self.history_search_var.get().strip().lower()
        records = []
        for record in reversed(self.history_records[-100:]):
            searchable = " ".join(str(record.get(key, "")) for key in ("source", "output", "status", "details")).lower()
            if not query or query in searchable:
                records.append(record)
        for tree in trees:
            for item in tree.get_children():
                tree.delete(item)
            for record in records[:30]:
                tree.insert("", "end", iid=f"{id(tree)}-{record.get('id')}", values=(record.get("time", ""), record.get("source", ""), record.get("status", ""), record.get("details", "")))

    def change_language(self, _event=None):
        selected = self.language_combo.get()
        self.language_var.set("vi" if selected == "Tiếng Việt" else "en")
        language = self.language_var.get()
        self.root.title(self.text("window_title", language))
        for key, widget in self.text_widgets.items():
            widget.configure(text=self.text(key, language))
        if not (self.worker and self.worker.is_alive()):
            self.page_progress_text.set(self.text("page_not_started", language))
            self.overall_progress_text.set(self.text("overall_not_started", language))
            self.status_text.set(self.text("ready", language))

    def setup_theme(self):
        self.colors = {
            "bg": "#080b12",
            "sidebar": "#0b1019",
            "card": "#111823",
            "input": "#0c131d",
            "border": "#202c3b",
            "text": "#f1f5f9",
            "muted": "#94a3b8",
            "accent": "#7c5cff",
            "accent_hover": "#9278ff",
            "green": "#49d69c",
            "danger": "#f87171",
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"], borderwidth=1, relief="solid")
        style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["bg"], foreground=self.colors["muted"], font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 10, "bold"))
        style.configure("CardText.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", fieldbackground=self.colors["input"], foreground=self.colors["text"], insertcolor=self.colors["text"], bordercolor=self.colors["border"], lightcolor=self.colors["border"], darkcolor=self.colors["border"], padding=10)
        style.map("TEntry", bordercolor=[("focus", self.colors["accent"])], lightcolor=[("focus", self.colors["accent"])])
        style.configure("TSpinbox", fieldbackground=self.colors["input"], foreground=self.colors["text"], arrowcolor=self.colors["muted"], bordercolor=self.colors["border"], padding=7)
        style.configure("TButton", background="#1a2432", foreground=self.colors["text"], bordercolor=self.colors["border"], padding=(14, 9), font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", "#253247"), ("disabled", "#141c27")], foreground=[("disabled", "#64748b")])
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="white", bordercolor=self.colors["accent"], padding=(18, 10), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", self.colors["accent_hover"]), ("disabled", "#40357c")])
        style.configure("TCheckbutton", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", self.colors["card"])], foreground=[("disabled", "#687586")])
        style.configure("TRadiobutton", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 9))
        style.map("TRadiobutton", background=[("active", self.colors["card"])], foreground=[("disabled", "#687586")])
        style.configure("Horizontal.TProgressbar", troughcolor="#1a2534", background=self.colors["accent"], bordercolor="#1a2534", lightcolor=self.colors["accent"], darkcolor=self.colors["accent"], thickness=9)

    def build_ui(self):
        shell = ttk.Frame(self.root, style="App.TFrame")
        shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(shell, bg=self.colors["sidebar"], width=238)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="✦", bg=self.colors["sidebar"], fg=self.colors["accent"], font=("Segoe UI Symbol", 30, "bold")).pack(anchor="w", padx=22, pady=(28, 0))
        tk.Label(sidebar, text="MANGA DOWNLOADER", bg=self.colors["sidebar"], fg=self.colors["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=23, pady=(0, 3))
        self.register_text("tagline", tk.Label(sidebar, text="", bg=self.colors["sidebar"], fg=self.colors["muted"], font=("Segoe UI", 9))).pack(anchor="w", padx=23, pady=(0, 30))
        tk.Frame(sidebar, bg=self.colors["border"], height=1).pack(fill="x", padx=20, pady=(0, 20))

        def nav_button(text, active=False, command=None):
            return tk.Button(
                sidebar, text=text, anchor="w", relief="flat", bd=0, cursor="hand2",
                bg=self.colors["accent"] if active else self.colors["sidebar"],
                fg="white" if active else self.colors["muted"],
                activebackground=self.colors["accent_hover"] if active else "#17212c",
                activeforeground="white", font=("Segoe UI", 10, "bold" if active else "normal"),
                padx=22, pady=12, command=command,
            )

        self.register_text("nav_downloader", nav_button("", active=True)).pack(fill="x", padx=12, pady=2)
        history_nav = nav_button("", command=self.show_history_window)
        settings_nav = nav_button("", command=self.show_settings_window)
        self.register_text("nav_archive", history_nav).pack(fill="x", padx=12, pady=2)
        self.register_text("nav_settings", settings_nav).pack(fill="x", padx=12, pady=2)

        sidebar_bottom = tk.Frame(sidebar, bg=self.colors["sidebar"])
        sidebar_bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self.register_text("local_workspace", tk.Label(sidebar_bottom, text="", bg=self.colors["sidebar"], fg=self.colors["green"], font=("Segoe UI", 8, "bold"))).pack(anchor="w")
        self.register_text("local_description", tk.Label(sidebar_bottom, text="", bg=self.colors["sidebar"], fg=self.colors["muted"], font=("Segoe UI", 8))).pack(anchor="w", pady=(5, 0))

        main = ttk.Frame(shell, style="App.TFrame", padding=(34, 28, 34, 20))
        main.pack(side="left", fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(7, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        header.columnconfigure(0, weight=1)
        header_left = ttk.Frame(header, style="App.TFrame")
        header_left.grid(row=0, column=0, sticky="w")
        self.register_text("header_title", ttk.Label(header_left, text="", style="Title.TLabel")).pack(anchor="w")
        self.register_text("header_subtitle", ttk.Label(header_left, text="", style="Subtitle.TLabel")).pack(anchor="w", pady=(5, 0))
        header_right = ttk.Frame(header, style="App.TFrame")
        header_right.grid(row=0, column=1, sticky="e", padx=(20, 0))
        badge = tk.Label(header_right, text="", bg=self.colors["accent"], fg="white", font=("Segoe UI", 8, "bold"), padx=10, pady=5)
        self.register_text("ui_badge", badge).pack(side="left", padx=(0, 16))
        self.register_text("language", ttk.Label(header_right, text="", style="Subtitle.TLabel")).pack(side="left", padx=(0, 8))
        self.language_combo = ttk.Combobox(header_right, values=("English", "Tiếng Việt"), state="readonly", width=13)
        self.language_combo.current(0)
        self.language_combo.bind("<<ComboboxSelected>>", self.change_language)
        self.language_combo.pack(side="left")

        source_card = ttk.Frame(main, style="Card.TFrame", padding=20)
        source_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        source_card.columnconfigure(0, weight=1)
        self.register_text("source", ttk.Label(source_card, text="", style="Muted.TLabel")).grid(row=0, column=0, sticky="w")
        self.register_text("chapter_url", ttk.Label(source_card, text="", style="CardTitle.TLabel")).grid(row=1, column=0, sticky="w", pady=(10, 6))
        url_entry = ttk.Entry(source_card, textvariable=self.url_var)
        url_entry.grid(row=2, column=0, sticky="ew")

        option_row = ttk.Frame(main, style="App.TFrame")
        option_row.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        option_row.columnconfigure(0, weight=1)
        option_row.columnconfigure(1, weight=1)

        scope_card = ttk.Frame(option_row, style="Card.TFrame", padding=20)
        scope_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.register_text("download_scope", ttk.Label(scope_card, text="", style="Muted.TLabel")).pack(anchor="w")
        self.register_text("chapter_count", ttk.Label(scope_card, text="", style="CardTitle.TLabel")).pack(anchor="w", pady=(10, 8))
        scope_choices = ttk.Frame(scope_card, style="Card.TFrame")
        scope_choices.pack(anchor="w")
        for key, value in (("one_chapter", 1), ("five_chapters", 5), ("ten_chapters", 10), ("all_chapters", 0)):
            self.register_text(key, ttk.Radiobutton(scope_choices, text="", value=value, variable=self.chapter_count)).pack(side="left", padx=(0, 12))

        output_card = ttk.Frame(option_row, style="Card.TFrame", padding=20)
        output_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        self.register_text("output", ttk.Label(output_card, text="", style="Muted.TLabel")).pack(anchor="w")
        self.register_text("archive_options", ttk.Label(output_card, text="", style="CardTitle.TLabel")).pack(anchor="w", pady=(10, 8))
        output_options = ttk.Frame(output_card, style="Card.TFrame")
        output_options.pack(anchor="w")
        self.register_text("webp_jpg", ttk.Checkbutton(output_options, text="", variable=self.convert_var)).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.register_text("create_cbz", ttk.Checkbutton(output_options, text="", variable=self.cbz_var)).grid(row=0, column=1, sticky="w")
        self.register_text("redownload", ttk.Checkbutton(output_card, text="", variable=self.overwrite_var)).pack(anchor="w", pady=(8, 0))

        folder_card = ttk.Frame(main, style="Card.TFrame", padding=20)
        folder_card.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        folder_card.columnconfigure(0, weight=1)
        self.register_text("output_folder", ttk.Label(folder_card, text="", style="Muted.TLabel")).grid(row=0, column=0, columnspan=2, sticky="w")
        folder_entry = ttk.Entry(folder_card, textvariable=self.output_var)
        folder_entry.grid(row=1, column=0, sticky="ew", pady=(9, 0), padx=(0, 10))
        self.register_text("choose_folder", ttk.Button(folder_card, text="", command=self.choose_output)).grid(row=1, column=1, pady=(9, 0))

        actions = ttk.Frame(main, style="App.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(0, 18))
        self.register_text("start", ttk.Button(actions, text="", style="Accent.TButton", command=self.start))
        self.start_button = self.text_widgets["start"]
        self.start_button.pack(side="left")
        self.register_text("stop", ttk.Button(actions, text="", command=self.stop, state="disabled"))
        self.stop_button = self.text_widgets["stop"]
        self.stop_button.pack(side="left", padx=(9, 0))
        self.register_text("delay", ttk.Label(actions, text="", style="Subtitle.TLabel")).pack(side="left", padx=(25, 8))
        ttk.Spinbox(actions, from_=0, to=60, increment=0.5, width=7, textvariable=self.delay_var).pack(side="left")

        progress_card = ttk.Frame(main, style="Card.TFrame", padding=20)
        progress_card.grid(row=5, column=0, sticky="ew", pady=(0, 16))
        progress_card.columnconfigure(0, weight=1)
        ttk.Label(progress_card, textvariable=self.page_progress_text, style="CardText.TLabel").grid(row=0, column=0, sticky="w")
        self.page_progress = ttk.Progressbar(progress_card, mode="determinate", maximum=1, value=0)
        self.page_progress.grid(row=1, column=0, sticky="ew", pady=(7, 12))
        ttk.Label(progress_card, textvariable=self.overall_progress_text, style="CardText.TLabel").grid(row=2, column=0, sticky="w")
        self.overall_progress = ttk.Progressbar(progress_card, mode="determinate", maximum=1, value=0)
        self.overall_progress.grid(row=3, column=0, sticky="ew", pady=(7, 0))

        history_card = ttk.Frame(main, style="Card.TFrame", padding=14)
        history_card.grid(row=6, column=0, sticky="ew", pady=(0, 16))
        history_card.columnconfigure(0, weight=1)
        history_header = ttk.Frame(history_card, style="Card.TFrame")
        history_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        history_header.columnconfigure(0, weight=1)
        self.register_text("history", ttk.Label(history_header, text="", style="Muted.TLabel")).grid(row=0, column=0, sticky="w")
        self.history_search_entry = ttk.Entry(history_header, textvariable=self.history_search_var, width=34)
        self.history_search_entry.grid(row=0, column=1, sticky="e")
        self.history_search_var.trace_add("write", lambda *_args: self.refresh_history())
        self.history_tree = ttk.Treeview(history_card, columns=("time", "source", "status", "details"), show="headings", height=4)
        for column, width in (("time", 145), ("source", 360), ("status", 120), ("details", 260)):
            self.history_tree.heading(column, text=self.text(f"history_{column}"))
            self.history_tree.column(column, width=width, anchor="w", stretch=column in {"source", "details"})
        self.history_tree.grid(row=1, column=0, sticky="ew")
        self.refresh_history()

        log_card = ttk.Frame(main, style="Card.TFrame", padding=16)
        log_card.grid(row=7, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        log_header = ttk.Frame(log_card, style="Card.TFrame")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self.register_text("activity_log", ttk.Label(log_header, text="", style="Muted.TLabel")).pack(side="left")
        self.register_text("clear_log", ttk.Button(log_header, text="", command=self.clear_log)).pack(side="right")
        self.log = ScrolledText(log_card, height=9, state="disabled", wrap="word", bg=self.colors["input"], fg="#b9c6d4", insertbackground=self.colors["text"], selectbackground="#264f78", relief="flat", borderwidth=0, padx=12, pady=10, font=("Consolas", 9))
        self.log.grid(row=1, column=0, sticky="nsew")

        status = tk.Frame(main, bg=self.colors["bg"])
        status.grid(row=8, column=0, sticky="ew", pady=(11, 0))
        tk.Label(status, text="●", bg=self.colors["bg"], fg=self.colors["green"], font=("Segoe UI", 9)).pack(side="left")
        tk.Label(status, textvariable=self.status_text, bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))
        self.register_text("privacy", tk.Label(status, text="", bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 8))).pack(side="right")
        self.change_language()

    def show_history_window(self):
        self._show_auxiliary_window("history")

    def show_settings_window(self):
        self._show_auxiliary_window("settings")

    def _show_auxiliary_window(self, kind: str):
        window = tk.Toplevel(self.root)
        window.configure(bg=self.colors["bg"])
        window.geometry("900x520" if kind == "history" else "620x360")
        window.minsize(560, 300)
        window.iconphoto(True, self.icon_photo)
        if kind == "history":
            window.title(self.text("history"))
            shell = ttk.Frame(window, style="App.TFrame", padding=24)
            shell.pack(fill="both", expand=True)
            shell.columnconfigure(0, weight=1)
            shell.rowconfigure(2, weight=1)
            ttk.Label(shell, text=self.text("history"), style="Title.TLabel").grid(row=0, column=0, sticky="w")
            search = ttk.Entry(shell, textvariable=self.history_search_var)
            search.grid(row=1, column=0, sticky="ew", pady=(16, 12))
            tree = ttk.Treeview(shell, columns=("time", "source", "status", "details"), show="headings")
            for column in ("time", "source", "status", "details"):
                tree.heading(column, text=self.text(f"history_{column}"))
                tree.column(column, width=150 if column != "source" else 330, anchor="w", stretch=True)
            tree.grid(row=2, column=0, sticky="nsew")
            self.history_detail_tree = tree
            self.refresh_history()
        else:
            window.title(self.text("settings_title"))
            shell = ttk.Frame(window, style="App.TFrame", padding=28)
            shell.pack(fill="both", expand=True)
            ttk.Label(shell, text=self.text("settings_title"), style="Title.TLabel").pack(anchor="w")
            ttk.Label(shell, text=self.text("settings_note"), style="Subtitle.TLabel", wraplength=540).pack(anchor="w", pady=(12, 24))
            ttk.Label(shell, text=self.text("settings_output"), style="CardText.TLabel").pack(anchor="w")
            ttk.Label(shell, textvariable=self.output_var, style="Subtitle.TLabel").pack(anchor="w", pady=(6, 0))

    def choose_output(self):
        selected = filedialog.askdirectory(title=self.text("choose_folder"))
        if selected:
            self.output_var.set(selected)

    def write_log(self, message: str):
        self.log.configure(state="normal")
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def play_completion_sound(self):
        """Play a short completion sound without blocking the GUI thread."""
        try:
            if winsound is not None:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            else:
                self.root.bell()
        except Exception:
            # Audio notifications must never prevent the completion popup.
            self.root.bell()

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            url = downloader.normalize_url(self.url_var.get())
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError(self.text("delay_invalid"))
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror(self.text("invalid_settings"), str(exc))
            return
        if not self.output_var.get().strip():
            messagebox.showerror(self.text("missing_folder"), self.text("choose_folder_first"))
            return

        output_root = Path(self.output_var.get()).expanduser()
        selected_count = self.chapter_count.get()
        overwrite = self.overwrite_var.get()
        convert_webp = self.convert_var.get()
        create_cbz_option = self.cbz_var.get()
        language = self.language_var.get()

        self.stop_event.clear()
        self.status_text.set(self.text("downloading", language))
        self.page_progress.configure(maximum=1, value=0)
        self.page_progress_text.set(self.text("preparing", language))
        self.overall_progress.stop()
        if selected_count:
            self.overall_progress.configure(mode="determinate", maximum=selected_count, value=0)
            self.overall_progress_text.set(self.text("overall_fixed", language, count=selected_count))
        else:
            self.overall_progress.configure(mode="indeterminate")
            self.overall_progress.start(12)
            self.overall_progress_text.set(self.text("overall_all", language))
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.write_log(self.text("started", language, url=url))
        self.add_history(url, output_root, selected_count)
        self.worker = threading.Thread(
            target=self.download_worker,
            args=(url, delay, output_root, selected_count, overwrite, convert_webp, create_cbz_option, language),
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.status_text.set(self.text("stopping"))
            self.write_log(self.text("stopping"))

    def emit(self, kind: str, value: object = ""):
        self.events.put((kind, value))

    def download_worker(
        self,
        url: str,
        delay: float,
        output_root: Path,
        selected_count: int,
        overwrite: bool,
        convert_webp: bool,
        create_cbz_option: bool,
        language: str,
    ):
        session = downloader.make_session()
        output_root.mkdir(parents=True, exist_ok=True)
        chapters_done = 0
        visited: set[str] = set()

        try:
            while url and url not in visited and (selected_count == 0 or chapters_done < selected_count):
                if self.stop_event.is_set():
                    raise downloader.DownloadCancelled(self.text("stopped", language))
                visited.add(url)
                self.emit("log", self.text("downloading_chapter", language, number=chapters_done + 1, url=url))
                title, image_count = downloader.download_chapter(
                    session,
                    url,
                    output_root,
                    delay,
                    30,
                    overwrite,
                    self.stop_event,
                    lambda chapter, current, total: self.emit("page_progress", (chapter, current, total)),
                )
                chapter_dir = output_root / title
                if convert_webp or create_cbz_option:
                    converted = convert_webp_to_jpg(chapter_dir)
                    if converted:
                        self.emit("log", self.text("converted", language, count=converted))
                if create_cbz_option:
                    cbz = create_cbz(chapter_dir)
                    self.emit("log", self.text("created_cbz", language, path=cbz))
                chapters_done += 1
                self.emit("overall_progress", (chapters_done, selected_count))
                self.emit("log", self.text("completed_chapter", language, title=title, count=image_count))

                if selected_count and chapters_done >= selected_count:
                    break
                if self.stop_event.wait(max(delay, 1.0)):
                    raise downloader.DownloadCancelled(self.text("stopped", language))
                page = session.get(url, timeout=30)
                page.raise_for_status()
                url = downloader.next_chapter(page.text, page.url)
                if not url:
                    self.emit("log", self.text("no_next", language))
            self.emit("done", self.text("completed_all", language, count=chapters_done))
        except downloader.DownloadCancelled as exc:
            self.emit("stopped", str(exc))
        except requests.RequestException as exc:
            self.emit("error", f"{self.text('network_error', language)}: {exc}")
        except Exception as exc:  # Keep worker errors visible in the GUI.
            self.emit("error", f"{self.text('generic_error', language)}: {exc}")

    def process_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.write_log(str(value))
                elif kind == "page_progress":
                    chapter, current, total = value
                    if current == 0:
                        self.page_progress.configure(maximum=total, value=0)
                    else:
                        self.page_progress.configure(maximum=total, value=current)
                    self.page_progress_text.set(self.text("page_progress", chapter=chapter, current=current, total=total))
                    self.status_text.set(self.text("status_downloading", chapter=chapter))
                elif kind == "overall_progress":
                    current, total = value
                    if total:
                        self.overall_progress.configure(mode="determinate", maximum=total, value=current)
                        self.overall_progress_text.set(self.text("overall_progress", current=current, total=total))
                    else:
                        self.overall_progress_text.set(self.text("overall_all_progress", current=current))
                elif kind == "done":
                    self.write_log(str(value))
                    self.update_history(self.text("status_complete"), str(value))
                    self.overall_progress.stop()
                    self.status_text.set(self.text("status_complete"))
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.play_completion_sound()
                    messagebox.showinfo(self.text("download_complete"), str(value))
                elif kind == "stopped":
                    self.write_log(str(value))
                    self.update_history(self.text("status_stopped"), str(value))
                    self.overall_progress.stop()
                    self.status_text.set(self.text("status_stopped"))
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                elif kind == "error":
                    self.write_log(str(value))
                    self.update_history(self.text("status_error"), str(value))
                    self.overall_progress.stop()
                    self.status_text.set(self.text("status_error"))
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    messagebox.showerror(self.text("download_failed"), str(value))
        except queue.Empty:
            pass
        self.root.after(100, self.process_events)


def main():
    root = tk.Tk()
    MangaGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
