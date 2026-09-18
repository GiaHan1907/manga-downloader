#!/usr/bin/env python3
"""Simple Windows GUI for download_manga.py."""

from __future__ import annotations

import os
import queue
import re
import secrets
import shutil
import subprocess
import threading
import traceback
import time
import zipfile
import csv
import ctypes
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

import requests
from PIL import Image, ImageOps, ImageTk

import download_manga as downloader
from history_store import HistoryStore

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

try:
    import fcntl  # POSIX lock-file fallback for the single-instance guard
except ImportError:  # Windows uses the named mutex instead.
    fcntl = None

if sys.platform == "win32":
    # use_last_error=True preserves the Win32 error for ctypes.get_last_error().
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


def resource_path(filename: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / filename


UI_TEXT = {
    "en": {
        "window_title": "Manga Downloader",
        "tagline": "Reader & archive workspace",
        "nav_downloader": "▣   Downloader",
        "nav_archive": "▤   History",
        "nav_library": "▦   Library",
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
        "status_downloading_speed": "Downloading {chapter} — {speed} · {bytes} · ETA {eta}",
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
        "settings_note": "Changes apply immediately and are saved to settings.json.",
        "settings_section_download": "Download",
        "settings_timeout": "Request timeout (seconds)",
        "settings_retries": "Automatic retries per task",
        "settings_naming": "Chapter folder naming",
        "naming_none": "Original title",
        "naming_site": "Remove site name",
        "naming_slug": "Slug only",
        "naming_full": "Site name + slug cleanup",
        "settings_section_notify": "Notifications",
        "settings_sound": "Completion sound",
        "settings_notify": "Popups on completion / failure",
        "settings_section_window": "Window",
        "settings_tray": "Close button minimizes to tray",
        "settings_section_appearance": "Appearance",
        "settings_language": "Language",
        "settings_theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "System",
        "settings_density": "Density",
        "density_comfortable": "Comfortable",
        "density_compact": "Compact",
        "settings_saved": "Settings saved.",
        "settings_reset": "↺  Reset to defaults",
        "settings_save": "Save settings",
        "settings_invalid_number": "Timeout must be between 5 and 120 seconds and retries between 1 and 10.",
        "toast_download_complete": "Download complete",
        "toast_download_failed": "Download failed",
        "toast_queue_done": "Queue finished",
        "toast_queue_summary": "{done} succeeded · {failed} failed",
        "toast_queue_paused": "Queue paused",
        "toast_queue_paused_body": "Resume from the queue panel to continue.",
        "toast_download_stopped": "Download stopped",
        "toast_download_stopped_body": "The download was stopped by user request.",
        "toast_crash_title": "Unexpected error",
        "toast_crash_body": "A fatal error occurred: {error}. Details were written to the crash log.",
        "queue_progress": "Task {done}/{total} · {completed} completed · {failed} failed · {bytes}",
        "queue_progress_title": "Queue progress",
        "queue_progress_idle": "Queue idle",
        "settings_output": "Current output folder",
        "open_folder": "Open folder",
        "open_folder_action": "Open folder",
        "open_folder_missing_confirm": "The output folder does not exist yet. Create it?",
        "activity_log_hide": "Hide ▲",
        "activity_log_show": "Show ▼",
        "tip_url": "Full URL of the first chapter to download.",
        "tip_choose_folder": "Chapters and CBZ archives are saved here.",
        "tip_open_folder": "Open the output folder in File Explorer.",
        "tip_start": "Download the selected chapters.",
        "tip_stop": "Stop after the current page request.",
        "tip_delay": "Seconds to wait between image requests.",
        "tip_search_history": "Filter history by manga, URL, status, or details.",
        "tip_clear_log": "Remove all lines from the activity log.",
        "tip_webp": "Convert downloaded WebP pages to JPG.",
        "tip_cbz": "Create one CBZ archive per chapter.",
        "tip_redownload": "Download images again even if files already exist.",
        "queue": "DOWNLOAD QUEUE",
        "queue_start": "▶  Start queue",
        "queue_stop": "■  Stop queue",
        "queue_add": "+  Add task",
        "queue_remove": "−  Remove",
        "queue_up": "↑",
        "queue_down": "↓",
        "queue_retry": "↻  Retry failed",
        "queue_clear_completed": "✕  Clear completed",
        "queue_col_state": "State",
        "queue_col_source": "Source",
        "queue_col_progress": "Progress",
        "queue_col_output": "Output",
        "state_queued": "Queued",
        "state_active": "Active",
        "state_completed": "Completed",
        "state_stopped": "Stopped",
        "state_failed": "Failed",
        "state_preparing": "Preparing",
        "state_downloading": "Downloading",
        "speed_value": "{kbps} KB/s",
        "eta_value": "{time}",
        "eta_pending": "calculating",
        "state_converting": "Converting",
        "state_creating_cbz": "Creating CBZ",
        "queue_started": "Queue started: {count} task(s).",
        "queue_done": "Queue finished.",
        "queue_paused": "Queue paused. Remaining tasks stay queued.",
        "queue_busy": "A download or queue run is already active.",
        "queue_no_tasks": "There are no queued tasks to start.",
        "queue_removed": "Removed task: {url}",
        "task_log_title": "Task log",
        "task_log_empty": "No log entries for this task.",
        "task_state_changed": "[{state}] {url} {details}",
        "task_progress_chapters": "{count} chapter(s)",
        "history_transfer": "Pages {pages} · {bytes} · paused {paused} · attempts {attempts}",
        "history_finished_near": "Finished near expected size ({bytes})",
        "hint_queue": "The queue is empty — set a chapter URL above, then click “+ Add task”.",
        "hint_history": "No downloads yet — completed tasks will appear here.",
        "hint_library": "No chapters found in the output folders — download something first, then Scan.",
        "task_progress_bytes": "{chapters} chapter(s) · {bytes} · {speed}",
        "tip_queue_add": "Add the chapter URL above to the queue with the current settings.",
        "tip_queue_start": "Download all queued tasks one by one (or only the selected ones).",
        "queue_pause": "⏸  Pause",
        "queue_resume": "⏵  Resume",
        "state_paused": "Paused",
        "pause_requested": "Pause requested. Finishing the current page request...",
        "queue_resumed": "Queue resumed.",
        "pause_failed_first": "Cannot pause between retries: {error}",
        "attempt_failed": "Attempt {attempt} failed: {error}",
        "attempt_retry_in": "Retrying in {seconds}s (attempt {next_attempt}/{max_attempts})",
        "task_requeued": "Re-queued after {attempts} failed attempt(s): {url}",
        "task_permanently_failed": "Failed after {attempts} attempt(s): {url}",
        "history_filters": "Filters",
        "history_filter_all": "All statuses",
        "history_filter_done": "Completed",
        "history_filter_failed": "Failed",
        "history_filter_stopped": "Stopped",
        "history_sort": "Sort",
        "library_title": "Archive Library",
        "library_scan": "↻  Scan",
        "library_view": "View",
        "view_grid": "Grid",
        "view_list": "List",
        "library_search": "Search library",
        "library_filter": "All",
        "library_filter_cbz": "CBZ ready",
        "library_filter_pages": "Pages only",
        "library_count": "{count} item(s)",
        "library_empty": "No chapters found in the output folders yet — download something first, then Scan.",
        "library_pages": "{count} pages",
        "library_missing": "Item no longer exists on disk.",
        "library_open_cbz": "Open CBZ",
        "library_rename": "✎  Rename",
        "library_delete": "🗑  Delete",
        "library_confirm_delete": "Delete “{name}”?\nThis removes {pages} page file(s) from disk.",
        "library_confirm_delete_cbz": "Delete “{name}.cbz”?\nThe archive file will be removed from disk.",
        "library_deleted": "Deleted: {name}",
        "library_renamed": "Renamed “{old}” → “{new}”",
        "library_new_name": "New chapter name",
        "library_name_exists": "A chapter with that name already exists.",
        "library_name_invalid": "Invalid name (it must differ from the current one and cannot contain \\ / : * ? \" < > |).",
        "tip_settings_timeout": "Network timeout for each page request (5-120 s).",
        "tip_settings_retries": "How many times a queue task retries before failing (1-10).",
        "tip_library_scan": "Re-scan the output folders for chapters and CBZ archives.",
        "tip_library_view": "Switch between grid and list view.",
        "tip_library_search": "Filter the library by title.",
        "tip_library_filter": "Show everything, only CBZ-ready chapters, or chapters without a CBZ.",
        "history_copy": "⧉  Copy URL",
        "history_requeue": "↻  Re-queue",
        "filter_all": "All statuses",
        "filter_done": "Completed",
        "filter_failed": "Failed",
        "filter_stopped": "Stopped / Paused",
        "sort_newest": "Newest first",
        "sort_oldest": "Oldest first",
        "sort_source": "Source A→Z",
        "history_sort_newest": "Newest first",
        "history_sort_oldest": "Oldest first",
        "history_sort_source": "Source A→Z",
        "history_export": "⇩  Export CSV",
        "history_delete": "🗑  Delete",
        "history_retry": "↻  Re-download",
        "history_copy_url": "Copy URL",
        "history_open_folder": "Open folder",
        "history_events": "Events",
        "history_confirm_delete": "Delete {count} selected record(s)? This does not remove downloaded files.",
        "history_deleted": "Deleted {count} history record(s).",
        "history_exported": "History exported: {path}",
        "history_copied": "URL copied to clipboard.",
        "history_no_selection": "Select a history record first.",
        "history_records": "{count} record(s)",
        "history_requeued": "Added to queue from history: {url}",
        "tip_history_filter": "Show only records with the chosen status.",
        "tip_history_sort": "Change the list order.",
        "tip_history_export": "Export the filtered history to a CSV file.",
        "tip_history_delete": "Delete selected history records (downloaded files stay on disk).",
        "tip_history_retry": "Queue the selected download again with its saved settings.",
        "tip_history_copy_url": "Copy the source URL to the clipboard.",
        "tip_history_open_folder": "Open the output folder of the selected record.",
        "event_started": "Started",
        "event_finished": "Finished: {message}",
        "event_chapter": "Chapter {number} done ({count} pages).",
    },
    "vi": {
        "window_title": "Manga Downloader",
        "tagline": "Không gian tải và lưu trữ truyện",
        "nav_downloader": "▣   Trình tải truyện",
        "nav_archive": "▤   Lịch sử tải",
        "nav_library": "▦   Thư viện",
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
        "status_downloading_speed": "Đang tải {chapter} — {speed} · {bytes} · ETA {eta}",
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
        "settings_note": "Thay đổi được áp dụng ngay lập tức và lưu vào settings.json.",
        "settings_section_download": "Tải xuống",
        "settings_timeout": "Thời gian chờ request (giây)",
        "settings_retries": "Số lần tự động thử lại mỗi task",
        "settings_naming": "Cách đặt tên thư mục chương",
        "naming_none": "Giữ nguyên tiêu đề",
        "naming_site": "Bỏ tên trang web",
        "naming_slug": "Chỉ giữ slug",
        "naming_full": "Bỏ tên web + làm sạch slug",
        "settings_section_notify": "Thông báo",
        "settings_sound": "Âm thanh khi hoàn tất",
        "settings_notify": "Cửa sổ thông báo khi hoàn tất / lỗi",
        "settings_section_window": "Cửa sổ",
        "settings_tray": "Nút đóng thu nhỏ xuống khay hệ thống",
        "settings_section_appearance": "Giao diện",
        "settings_language": "Ngôn ngữ",
        "settings_theme": "Chủ đề",
        "theme_dark": "Tối",
        "theme_light": "Sáng",
        "theme_system": "Theo hệ thống",
        "settings_density": "Mật độ hiển thị",
        "density_comfortable": "Thoáng",
        "density_compact": "Gọn",
        "settings_saved": "Đã lưu cài đặt.",
        "settings_reset": "↺  Khôi phục mặc định",
        "settings_save": "Lưu cài đặt",
        "settings_invalid_number": "Timeout phải từ 5 đến 120 giây và số lần thử lại từ 1 đến 10.",
        "toast_download_complete": "Tải hoàn tất",
        "toast_download_failed": "Tải thất bại",
        "toast_queue_done": "Hàng đợi hoàn tất",
        "toast_queue_summary": "{done} thành công · {failed} thất bại",
        "toast_queue_paused": "Hàng đợi tạm dừng",
        "toast_queue_paused_body": "Bấm tiếp tục ở bảng hàng đợi để chạy tiếp.",
        "toast_download_stopped": "Đã dừng tải",
        "toast_download_stopped_body": "Tải xuống đã được dừng theo yêu cầu.",
        "toast_crash_title": "Lỗi bất thường",
        "toast_crash_body": "Đã xảy ra lỗi nghiêm trọng: {error}. Chi tiết đã được ghi vào tệp crash log.",
        "queue_progress": "Tác vụ {done}/{total} · {completed} hoàn tất · {failed} thất bại · {bytes}",
        "queue_progress_title": "Tiến độ hàng đợi",
        "queue_progress_idle": "Hàng đợi đang trống",
        "settings_output": "Thư mục lưu hiện tại",
        "open_folder": "Mở thư mục",
        "open_folder_action": "Mở thư mục",
        "open_folder_missing_confirm": "Thư mục lưu chưa tồn tại. Tạo mới?",
        "activity_log_hide": "Ẩn ▲",
        "activity_log_show": "Hiện ▼",
        "tip_url": "URL đầy đủ của chương đầu tiên cần tải.",
        "tip_choose_folder": "Nơi lưu các chương và tệp CBZ.",
        "tip_open_folder": "Mở thư mục lưu trong File Explorer.",
        "tip_start": "Tải các chương đã chọn.",
        "tip_stop": "Dừng sau yêu cầu trang hiện tại.",
        "tip_delay": "Số giây chờ giữa các yêu cầu ảnh.",
        "tip_search_history": "Lọc lịch sử theo manga, URL, trạng thái hoặc chi tiết.",
        "tip_clear_log": "Xóa toàn bộ dòng trong nhật ký.",
        "tip_webp": "Chuyển ảnh WebP đã tải sang JPG.",
        "tip_cbz": "Tạo một tệp CBZ cho mỗi chương.",
        "tip_redownload": "Tải lại ảnh ngay cả khi tệp đã có sẵn.",
        "queue": "HÀNG ĐỢI TẢI",
        "queue_start": "▶  Chạy hàng đợi",
        "queue_stop": "■  Dừng hàng đợi",
        "queue_add": "+  Thêm tác vụ",
        "queue_remove": "−  Xóa",
        "queue_up": "↑",
        "queue_down": "↓",
        "queue_retry": "↻  Thử lại lỗi",
        "queue_clear_completed": "✕  Xóa đã xong",
        "queue_col_state": "Trạng thái",
        "queue_col_source": "Nguồn",
        "queue_col_progress": "Tiến trình",
        "queue_col_output": "Nơi lưu",
        "state_queued": "Đang chờ",
        "state_active": "Đang tải",
        "state_completed": "Hoàn tất",
        "state_stopped": "Đã dừng",
        "state_failed": "Lỗi",
        "state_preparing": "Đang chuẩn bị",
        "state_downloading": "Đang tải",
        "speed_value": "{kbps} KB/s",
        "eta_value": "{time}",
        "eta_pending": "đang tính",
        "state_converting": "Đang chuyển đổi",
        "state_creating_cbz": "Đang tạo CBZ",
        "queue_started": "Hàng đợi bắt đầu: {count} tác vụ.",
        "queue_done": "Hàng đợi đã chạy xong.",
        "queue_paused": "Hàng đợi tạm dừng. Các tác vụ còn lại vẫn chờ.",
        "queue_busy": "Đang có tải xuống hoặc hàng đợi chạy.",
        "queue_no_tasks": "Không có tác vụ nào đang chờ để chạy.",
        "queue_removed": "Đã xóa tác vụ: {url}",
        "task_log_title": "Nhật ký tác vụ",
        "task_log_empty": "Tác vụ này chưa có nhật ký.",
        "task_state_changed": "[{state}] {url} {details}",
        "task_progress_chapters": "{count} chương",
        "history_transfer": "Trang {pages} · {bytes} · tạm dừng {paused} · lần thử {attempts}",
        "history_finished_near": "Hoàn tất gần đúng dung lượng mong đợi ({bytes})",
        "hint_queue": "Hàng đợi trống — dán URL chương ở khung phía trên rồi bấm “+ Thêm tác vụ”.",
        "hint_history": "Chưa có lượt tải nào — các tác vụ hoàn thành sẽ hiện ở đây.",
        "hint_library": "Chưa có chương nào trong thư mục output — hãy tải vài chương rồi bấm Quét lại.",
        "task_progress_bytes": "{chapters} chương · {bytes} · {speed}",
        "tip_queue_add": "Thêm URL chapter ở trên vào hàng đợi với thiết lập hiện tại.",
        "tip_queue_start": "Tải lần lượt các tác vụ đang chờ (hoặc chỉ những dòng đang chọn).",
        "queue_pause": "⏸  Tạm dừng",
        "queue_resume": "⏵  Tiếp tục",
        "state_paused": "Tạm dừng",
        "pause_requested": "Đã yêu cầu tạm dừng. Đang chờ yêu cầu trang hiện tại...",
        "queue_resumed": "Hàng đợi đã tiếp tục.",
        "pause_failed_first": "Không thể tạm dừng giữa các lần thử lại: {error}",
        "attempt_failed": "Lần thử {attempt} thất bại: {error}",
        "attempt_retry_in": "Thử lại sau {seconds}s (lần {next_attempt}/{max_attempts})",
        "task_requeued": "Đưa lại vào hàng đợi sau {attempts} lần thất bại: {url}",
        "task_permanently_failed": "Thất bại sau {attempts} lần thử: {url}",
        "history_filters": "Trạng thái",
        "history_filter_all": "Tất cả",
        "history_filter_done": "Hoàn tất",
        "history_filter_failed": "Lỗi",
        "history_filter_stopped": "Đã dừng",
        "history_sort": "Sắp xếp",
        "library_title": "Thư viện truyện",
        "library_scan": "↻  Quét lại",
        "library_view": "Kiểu xem",
        "view_grid": "Lưới",
        "view_list": "Danh sách",
        "library_search": "Tìm trong thư viện",
        "library_filter": "Tất cả",
        "library_filter_cbz": "Đã có CBZ",
        "library_filter_pages": "Chưa có CBZ",
        "library_count": "{count} mục",
        "library_empty": "Chưa tìm thấy chương nào trong thư mục output — hãy tải vài chương rồi bấm Quét lại.",
        "library_pages": "{count} trang",
        "library_missing": "Mục này không còn tồn tại trên đĩa.",
        "library_open_cbz": "Mở CBZ",
        "library_rename": "✎  Đổi tên",
        "library_delete": "🗑  Xóa",
        "library_confirm_delete": "Xóa “{name}”?\nThao tác này sẽ xóa {pages} file trang khỏi đĩa.",
        "library_confirm_delete_cbz": "Xóa “{name}.cbz”?\nFile archive sẽ bị xóa khỏi đĩa.",
        "library_deleted": "Đã xóa: {name}",
        "library_renamed": "Đã đổi tên “{old}” → “{new}”",
        "library_new_name": "Tên chương mới",
        "library_name_exists": "Đã tồn tại chương với tên này.",
        "library_name_invalid": "Tên không hợp lệ (phải khác tên hiện tại và không chứa \\ / : * ? \" < > |).",
        "tip_settings_timeout": "Thời gian chờ mạng cho mỗi request trang (5-120 s).",
        "tip_settings_retries": "Số lần một task trong hàng đợi được thử lại trước khi thất bại (1-10).",
        "tip_library_scan": "Quét lại các thư mục output để tìm chương và file CBZ.",
        "tip_library_view": "Chuyển giữa kiểu xem lưới và danh sách.",
        "tip_library_search": "Lọc thư viện theo tên chương.",
        "tip_library_filter": "Hiện tất cả, chỉ chương đã có CBZ, hoặc chương chưa có CBZ.",
        "history_copy": "⧉  Copy URL",
        "history_requeue": "↻  Thêm vào hàng đợi",
        "filter_all": "Tất cả",
        "filter_done": "Hoàn tất",
        "filter_failed": "Thất bại",
        "filter_stopped": "Đã dừng / Tạm dừng",
        "sort_newest": "Mới nhất",
        "sort_oldest": "Cũ nhất",
        "sort_source": "Nguồn A→Z",
        "history_sort_newest": "Mới nhất",
        "history_sort_oldest": "Cũ nhất",
        "history_sort_source": "Nguồn A→Z",
        "history_export": "⇩  Xuất CSV",
        "history_delete": "🗑  Xóa",
        "history_retry": "↻  Tải lại",
        "history_copy_url": "Copy URL",
        "history_open_folder": "Mở thư mục",
        "history_events": "Diễn biến",
        "history_confirm_delete": "Xóa {count} bản ghi đã chọn? Tệp đã tải vẫn còn trên đĩa.",
        "history_deleted": "Đã xóa {count} bản ghi lịch sử.",
        "history_exported": "Đã xuất lịch sử: {path}",
        "history_copied": "Đã copy URL vào clipboard.",
        "history_no_selection": "Hãy chọn một bản ghi lịch sử trước.",
        "history_records": "{count} bản ghi",
        "history_requeued": "Đã thêm vào hàng đợi từ lịch sử: {url}",
        "tip_history_filter": "Chỉ hiện bản ghi theo trạng thái đã chọn.",
        "tip_history_sort": "Đổi thứ tự danh sách.",
        "tip_history_export": "Xuất lịch sử (theo bộ lọc hiện tại) ra tệp CSV.",
        "tip_history_delete": "Xóa các bản ghi lịch sử đã chọn (tệp đã tải vẫn còn trên đĩa).",
        "tip_history_retry": "Thêm bản ghi đã chọn vào hàng đợi với thiết lập đã lưu.",
        "tip_history_copy_url": "Copy URL nguồn vào clipboard.",
        "tip_history_open_folder": "Mở thư mục lưu của bản ghi đã chọn.",
        "event_started": "Bắt đầu",
        "event_finished": "Kết thúc: {message}",
        "event_chapter": "Hoàn tất chương {number} ({count} ảnh).",
    },
}


class SingleInstanceGuard:
    """Phase 10.1: keep a second app instance from sharing the data files.

    Windows: a named mutex held for the process lifetime. Other platforms:
    an exclusive lock file in AppData. A second launch acquires nothing and
    relies on the existing instance to surface itself via the show event.
    """

    MUTEX_NAME = "MangaDownloader_SingleInstance_Mutex"
    ERROR_ALREADY_EXISTS = 183

    def __init__(self):
        self.handle = None
        self.is_owner = False
        if sys.platform == "win32":
            self.handle = _kernel32.CreateMutexW(None, False, self.MUTEX_NAME)
            self.is_owner = bool(self.handle) and ctypes.get_last_error() != self.ERROR_ALREADY_EXISTS
        else:
            lock_path = MangaGui._app_data_dir() / "app.lock"
            self.handle = open(lock_path, "w")
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.is_owner = True
            except OSError:
                self.is_owner = False

    def release(self):
        if self.handle is None:
            return
        try:
            if sys.platform == "win32":
                _kernel32.ReleaseMutex(self.handle)
                _kernel32.CloseHandle(self.handle)
            elif fcntl is not None:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
                self.handle.close()
        except OSError:
            pass
        self.handle = None
        self.is_owner = False

    def request_show(self, payload: str = "show"):
        """Signal the owning instance (best effort): show window, optional URL.

        The payload is always non-empty so the owner can tell a real request
        from a missing file: "show" means surface only, anything else is a
        URL to prefill (which also surfaces).
        """
        try:
            show_path = MangaGui._app_data_dir() / "show-instance.flag"
            show_path.write_text(payload or "show", encoding="utf-8")
        except OSError:
            pass

    def is_show_requested(self) -> str:
        """Consume the second-launch request; returns its payload ('' = none)."""
        show_path = MangaGui._app_data_dir() / "show-instance.flag"
        try:
            payload = show_path.read_text(encoding="utf-8")
            show_path.unlink()
            return payload
        except FileNotFoundError:
            return ""
        except OSError:
            return ""


def install_crash_logging(app: "MangaGui | None", log_tail_size: int = 50):
    """Phase 10.2: never die silently.

    Replaces sys.excepthook and threading.excepthook with handlers that write
    a crash-YYYYMMDD-HHMMSS.log (traceback, version, log tail) into AppData
    and push a crash_report event so the main thread can surface a fatal
    toast. Falls back to the previous default behavior when the app is
    absent or already closing.
    """
    default_sys_hook = sys.excepthook
    default_threading_hook = threading.excepthook

    def handle_error(exc_type, exc_value, exc_traceback, source_label: str):
        try:
            if app is None or app.closing:
                default_sys_hook(exc_type, exc_value, exc_traceback)
            else:
                crash_file = _write_crash_log(exc_type, exc_value, exc_traceback,
                                              source_label, app, log_tail_size)
                app.emit("crash_report", (str(exc_value), str(crash_file)))
        except Exception:
            default_sys_hook(exc_type, exc_value, exc_traceback)

    def sys_hook(exc_type, exc_value, exc_traceback):
        handle_error(exc_type, exc_value, exc_traceback, "main thread")

    def threading_hook(args: threading.ExceptHookArgs):
        handle_error(args.exc_type, args.exc_value, args.exc_traceback,
                     f"thread {args.thread.name if args.thread else 'unknown'}")

    sys.excepthook = sys_hook
    threading.excepthook = threading_hook


def _write_crash_log(exc_type, exc_value, exc_traceback, source_label: str,
                     app: "MangaGui", log_tail_size: int) -> Path:
    """Write the crash log synchronously; returns the file path."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    crash_file = app.get_settings_file().parent / f"crash-{stamp}.crash.log"
    try:
        tail = app.log.get("end-49l", "end").strip()
    except Exception:
        tail = "(activity log unavailable)"
    header = (
        "MangaDownloader crash log",
        f"time: {datetime.now().isoformat()}",
        f"version: {APP_VERSION}",
        f"source: {source_label}",
        f"python: {sys.version.split()[0]}",
        "",
    )
    body = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    content = "\n".join(header) + "\n" + body + "\n--- last activity ---\n" + tail + "\n"
    crash_file.write_text(content, encoding="utf-8")
    return crash_file


class QueueTask:
    """One queue entry. `state` stays a plain string so it persists to JSON.

    States: queued, active, completed, stopped, failed.
    """

    MAX_ATTEMPTS = 3  # fallback; the app overrides this from settings

    def __init__(self, url: str, output_root: str, chapter_count: int, delay: float,
                 overwrite: bool, convert_webp: bool, create_cbz: bool, *,
                 task_id: str | None = None, state: str = "queued", progress: str = "",
                 attempts: int = 0):
        now = datetime.now()
        self.id = task_id or _unique_id()
        self.url = url
        self.output_root = output_root
        self.chapter_count = chapter_count
        self.delay = delay
        self.overwrite = overwrite
        self.convert_webp = convert_webp
        self.create_cbz = create_cbz
        self.state = state
        self.progress = progress
        self.attempts = attempts
        self.log_lines: list[str] = []
        self.last_chapters = 0
        self.last_bytes = 0  # bytes received in this run (speed window)
        self.total_bytes = 0  # bytes received across the whole task (phase 10.4)
        self.bank_bytes = 0  # bytes banked when the task reached a final state (10.4)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "output": self.output_root,
            "chapter_count": self.chapter_count,
            "delay": self.delay,
            "overwrite": self.overwrite,
            "convert_webp": self.convert_webp,
            "create_cbz": self.create_cbz,
            "state": self.state,
            "progress": self.progress,
            "attempts": self.attempts,
            "total_bytes": getattr(self, "total_bytes", 0),
            "bank_bytes": getattr(self, "bank_bytes", 0),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueTask":
        task = cls(
            str(data.get("url", "")),
            str(data.get("output", "")),
            int(data.get("chapter_count", 1)),
            float(data.get("delay", 1.0)),
            bool(data.get("overwrite", False)),
            bool(data.get("convert_webp", True)),
            bool(data.get("create_cbz", True)),
            task_id=str(data.get("id")) if data.get("id") else None,
            state=str(data.get("state", "queued")),
            progress=str(data.get("progress", "")),
            attempts=int(data.get("attempts", 0)),
        )
        task.total_bytes = int(data.get("total_bytes", 0) or 0)
        task.bank_bytes = int(data.get("bank_bytes", 0) or 0)
        return task


class Tooltip:
    """Small hover tooltip. Text is resolved lazily so language switching works.

    Must only be used from the main thread (hover events are main-thread only).
    """

    def __init__(self, widget, get_text):
        self.widget = widget
        self.get_text = get_text
        self.tipwindow: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")

    def show(self, _event=None):
        if self.tipwindow is not None or not self.widget.winfo_exists():
            return
        text = self.get_text()
        if not text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=text, justify="left", bg="#111827", fg="#e5e7eb",
            relief="solid", borderwidth=1, font=("Segoe UI", 9), padx=8, pady=5,
        ).pack()

    def hide(self, _event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw is not None:
            tw.destroy()


def _unique_id() -> str:
    """Timestamp id plus a random suffix so two objects created within the
    same Windows timer tick (datetime.now() quantized ~15.6ms on older
    systems) never collide and crash ttk tree inserts."""
    return datetime.now().strftime("%Y%m%d%H%M%S%f") + secrets.token_hex(2)


def natural_key(path: Path):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def _fs_retry(func, *args, attempts: int = 6, delay: float = 0.15):
    """Run a filesystem op, retrying the transient Windows sharing locks.

    Antivirus scanners, search indexers and image viewers can hold a file
    for a moment, failing rename/rmtree with PermissionError. Retrying for
    about a second covers every realistic case without user-visible delay.
    """
    last_error: OSError | None = None
    for attempt in range(attempts):
        try:
            return func(*args)
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay * (attempt + 1))
    raise last_error if last_error else OSError("filesystem operation failed")


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


class ArchiveItem:
    """One scanned chapter folder (optionally with a sibling .cbz archive)."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.name = folder.name
        self.cbz = None
        self.page_count = 0
        self.cover_path = None
        self.rescan()

    def rescan(self):
        self.name = self.folder.name
        self.cbz = self.folder.with_name(self.folder.name + ".cbz")
        if not self.cbz.exists():
            self.cbz = None
        self.page_count = len(chapter_images(self.folder))
        self.cover_path = None
        for candidate in chapter_images(self.folder)[:1]:
            self.cover_path = candidate
            break

    @property
    def has_cbz(self) -> bool:
        return self.cbz is not None


class ArchiveLibrary:
    """Scans output roots for chapter folders and sibling .cbz archives."""

    def scan(self, roots: list[str]) -> dict[str, ArchiveItem]:
        items: dict[str, ArchiveItem] = {}
        for root_value in roots:
            root = Path(root_value).expanduser()
            if not root.is_dir():
                continue
            for entry in sorted(root.iterdir(), key=lambda p: natural_key(p)):
                if entry.name.lower().endswith(".cbz"):
                    continue
                if not entry.is_dir():
                    continue
                if not chapter_images(entry) and not (root / f"{entry.name}.cbz").exists():
                    continue
                item = items.setdefault(entry.name, ArchiveItem(entry))
                if item.has_cbz:
                    continue  # first root wins; later duplicates skipped
                item.rescan() if item.folder != entry else None
        return items


class ArchiveWindow(tk.Toplevel):
    """Archive library window with grid/list views, search, filter and actions."""

    THUMB = (132, 100)

    def __init__(self, app: "MangaGui"):
        super().__init__(app.root)
        self.app = app
        self.configure(bg=app.colors["bg"])
        self.geometry("980x640")
        self.minsize(760, 480)
        self.iconphoto(True, app.icon_photo)
        self.title(app.text("library_title"))
        self.archive = ArchiveLibrary()
        self.items: list[ArchiveItem] = []
        self.filtered: list[ArchiveItem] = []
        self.view_mode = "grid"
        self._thumbs: list[ImageTk.PhotoImage] = []
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_a: self.refresh_items())
        self._build()
        # Thumbnail workers never touch tkinter: they push results into a
        # queue drained by this after() loop on the main thread (ROADMAP #4).
        self.thumb_results: queue.Queue = queue.Queue()
        self.after(80, self._drain_thumbs)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.rescan()
        self.refresh_items()

    def destroy(self):
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass
        self.app.update_hints()
        super().destroy()

    def _drain_thumbs(self):
        try:
            while True:
                label, item, thumb = self.thumb_results.get_nowait()
                self._apply_thumb(label, item, thumb)
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(80, self._drain_thumbs)

    # ---------- UI ----------

    def _build(self):
        app = self.app
        shell = ttk.Frame(self, style="App.TFrame", padding=20)
        shell.pack(fill="both", expand=True)
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)
        header = ttk.Frame(shell, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(2, weight=1)
        app.register_text("library_title", ttk.Label(header, text="", style="Title.TLabel")).grid(row=0, column=0, sticky="w")
        # Not registered in text_widgets: its template needs a {count} value.
        # It is refreshed by relocalize()/refresh_items() on language change.
        self.count_label = ttk.Label(header, text="", style="Subtitle.TLabel")
        self.count_label.grid(row=0, column=1, sticky="w", padx=(14, 0))
        self.search_entry = ttk.Entry(header, textvariable=self.search_var, width=26)
        self.search_entry.grid(row=0, column=2, sticky="e")
        Tooltip(self.search_entry, lambda: app.text("tip_library_search"))
        self.scan_button = app.register_text("library_scan", ttk.Button(header, text="", command=self.rescan))
        self.scan_button.grid(row=0, column=3, sticky="e", padx=(10, 0))
        Tooltip(self.scan_button, lambda: app.text("tip_library_scan"))
        app.register_text("library_view", ttk.Label(header, text="", style="Subtitle.TLabel")).grid(row=0, column=4, sticky="e", padx=(18, 6))
        self.view_combo = ttk.Combobox(header, state="readonly", width=8, values=(app.text("view_grid"), app.text("view_list")))
        self.view_combo.current(0)
        self.view_combo.grid(row=0, column=5, sticky="e")
        self.view_combo.bind("<<ComboboxSelected>>", self._on_view_changed)
        Tooltip(self.view_combo, lambda: app.text("tip_library_view"))
        app.register_text("library_filter", ttk.Label(header, text="", style="Subtitle.TLabel")).grid(row=0, column=6, sticky="e", padx=(18, 6))
        self.filter_combo = ttk.Combobox(header, state="readonly", width=13, values=(app.text("library_filter"), app.text("library_filter_cbz"), app.text("library_filter_pages")))
        self.filter_combo.current(0)
        self.filter_combo.grid(row=0, column=7, sticky="e")
        self.filter_combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh_items())
        Tooltip(self.filter_combo, lambda: app.text("tip_library_filter"))

        self.canvas = tk.Canvas(shell, bg=app.colors["bg"], highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.vsb = ttk.Scrollbar(shell, orient="vertical", command=self.canvas.yview)
        self.vsb.grid(row=1, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.items_frame = ttk.Frame(self.canvas, style="App.TFrame")
        self.items_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), anchor="nw", window=self.items_frame)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.empty_label = None
        self.has_root = False  # Phase 10.7: any scanned output root yet?

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def _on_view_changed(self, _event=None):
        self.view_mode = "grid" if self.view_combo.current() == 0 else "list"
        self.refresh_items()

    def relocalize(self):
        """Refresh window title, combobox values and labels after a language switch."""
        self.title(self.app.text("library_title"))
        view = max(self.view_combo.current(), 0)
        self.view_combo.configure(values=(self.app.text("view_grid"), self.app.text("view_list")))
        self.view_combo.current(view)
        filter_index = max(self.filter_combo.current(), 0)
        self.filter_combo.configure(values=(
            self.app.text("library_filter"),
            self.app.text("library_filter_cbz"),
            self.app.text("library_filter_pages"),
        ))
        self.filter_combo.current(filter_index)
        self.refresh_items()

    # ---------- data ----------

    def rescan(self):
        """Scan the output folder plus recent history output folders."""
        roots = set()
        output = self.app.output_var.get().strip()
        if output:
            roots.add(output)
        for record in self.app.history.search()[:50]:
            output_value = record.get("output", "")
            if output_value:
                roots.add(output_value)
        scanned = self.archive.scan(list(roots))
        self.items = [scanned[key] for key in sorted(scanned, key=lambda name: natural_key(Path(name)))]
        self.has_root = bool(roots)

    def refresh_items(self):
        app = self.app
        query = self.search_var.get().strip().lower()
        filter_index = max(self.filter_combo.current(), 0)
        selected: list[ArchiveItem] = []
        for item in self.items:
            if query and query not in item.name.lower():
                continue
            if filter_index == 1 and not item.has_cbz:
                continue
            if filter_index == 2 and item.has_cbz:
                continue
            selected.append(item)
        self.filtered = selected
        self._render()

    # ---------- rendering ----------

    def _render(self):
        app = self.app
        self.count_label.configure(text=app.text("library_count", count=len(self.filtered)))
        for child in self.items_frame.winfo_children():
            child.destroy()
        self._thumbs = []
        self.empty_label = None
        if not self.filtered:
            self.empty_label = ttk.Label(self.items_frame, text=app.text("hint_library"), style="Muted.TLabel", wraplength=520)
            self.empty_label.pack(anchor="w", pady=24)
            return
        if self.view_mode == "grid":
            self._render_grid()
        else:
            self._render_list()

    def _render_grid(self):
        app = self.app
        columns = max(self.canvas.winfo_width() // 158, 1)
        for index, item in enumerate(self.filtered):
            cell = ttk.Frame(self.items_frame, style="Card.TFrame", padding=10)
            cell.grid(row=index // columns, column=index % columns, padx=6, pady=6, sticky="n")
            cover = tk.Label(cell, text="◌", bg=app.colors["input"], fg=app.colors["muted"],
                             width=15, height=6, font=("Segoe UI Symbol", 18))
            cover.pack()
            pages_label = ttk.Label(cell, text=app.text("library_pages", count=item.page_count), style="Muted.TLabel")
            pages_label.pack(anchor="w", pady=(6, 0))
            name_label = ttk.Label(cell, text=item.name, style="CardText.TLabel", wraplength=140)
            name_label.pack(anchor="w")
            cbz_label = ttk.Label(cell, text="CBZ" if item.has_cbz else "—", style="Muted.TLabel",
                                  foreground=app.colors["green"] if item.has_cbz else app.colors["muted"])
            cbz_label.pack(anchor="w")
            for widget in (cell, cover, pages_label, name_label, cbz_label):
                widget.bind("<Double-Button-1>", lambda _e, it=item: self.open_item(it))
                widget.bind("<Button-3>", lambda e, it=item: self.show_item_menu(e, it))
            self._thumbs.append(cover)
            self._load_cover(cover, item)

    def _render_list(self):
        app = self.app
        header = ttk.Frame(self.items_frame, style="App.TFrame")
        header.pack(fill="x", pady=(0, 4))
        for column, title, width in ((0, "Title", 380), (1, "Pages", 90), (2, "CBZ", 70), (3, "Folder", 320)):
            ttk.Label(header, text=title, style="Muted.TLabel", width=max(width // 8, 4)).grid(row=0, column=column, sticky="w")
        for index, item in enumerate(self.filtered):
            row = ttk.Frame(self.items_frame, style="Card.TFrame", padding=(10, 8))
            row.pack(fill="x", pady=2)
            cover = tk.Label(row, text="◌", bg=app.colors["input"], fg=app.colors["muted"], width=4, height=2)
            cover.grid(row=0, column=0, sticky="w", padx=(0, 10))
            ttk.Label(row, text=item.name, style="CardText.TLabel", width=46, anchor="w").grid(row=0, column=1, sticky="w")
            ttk.Label(row, text=app.text("library_pages", count=item.page_count), style="Muted.TLabel", width=12, anchor="w").grid(row=0, column=2, sticky="w")
            ttk.Label(row, text="CBZ" if item.has_cbz else "—", style="Muted.TLabel", width=6, anchor="w",
                      foreground=app.colors["green"] if item.has_cbz else app.colors["muted"]).grid(row=0, column=3, sticky="w")
            ttk.Label(row, text=str(item.folder.parent), style="Muted.TLabel", width=40, anchor="w").grid(row=0, column=4, sticky="w")
            for widget in (row, cover):
                widget.bind("<Double-Button-1>", lambda _e, it=item: self.open_item(it))
                widget.bind("<Button-3>", lambda e, it=item: self.show_item_menu(e, it))
            self._thumbs.append(cover)
            self._load_cover(cover, item)

    def _load_cover(self, label: tk.Label, item: ArchiveItem):
        if not item.cover_path:
            return
        def worker():
            try:
                with Image.open(item.cover_path) as image:
                    thumb = image.convert("RGB")
                    thumb.thumbnail(self.THUMB)
                self.thumb_results.put((label, item, thumb))
            except (OSError, ValueError):
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _apply_thumb(self, label: tk.Label, item: ArchiveItem, thumb: Image.Image):
        if not label.winfo_exists() or not item.folder.exists():
            return
        photo = ImageTk.PhotoImage(thumb, master=self)
        label.configure(image=photo, width=self.THUMB[0], height=self.THUMB[1], text="")
        label.image = photo
        self._thumbs.append(photo)

    # ---------- actions ----------

    def open_item(self, item: ArchiveItem):
        target = item.cbz if item.has_cbz else item.folder
        try:
            if sys.platform == "win32":
                os.startfile(target)  # noqa: S606 - intended Explorer/reader launch
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(target)])
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except OSError as exc:
            messagebox.showerror(self.app.text("generic_error"), str(exc))

    def open_item_folder(self, item: ArchiveItem):
        try:
            if sys.platform == "win32":
                os.startfile(item.folder.parent)  # noqa: S606 - intended Explorer launch
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(item.folder.parent)])
            else:
                subprocess.Popen(["xdg-open", str(item.folder.parent)])
        except OSError as exc:
            messagebox.showerror(self.app.text("generic_error"), str(exc))

    def show_item_menu(self, event, item: ArchiveItem):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=self.app.text("open_folder"), command=lambda: self.open_item_folder(item))
        menu.add_command(label=self.app.text("library_open_cbz"), state="normal" if item.has_cbz else "disabled",
                         command=lambda: self.open_item(item))
        menu.add_separator()
        menu.add_command(label=self.app.text("library_rename"), command=lambda: self.rename_item(item))
        menu.add_command(label=self.app.text("library_delete"), command=lambda: self.delete_item(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def rename_item(self, item: ArchiveItem):
        app = self.app
        if not item.folder.exists():
            messagebox.showerror(app.text("library_title"), app.text("library_missing"))
            return
        new_name = simpledialog.askstring(app.text("library_new_name"), app.text("library_new_name"),
                                          initialvalue=item.name, parent=self)
        if not new_name:
            return
        new_name = new_name.strip()
        invalid = (not new_name or new_name == item.name
                   or any(ch in new_name for ch in '\\/:*?"<>|'))
        target = item.folder.with_name(new_name)
        if invalid:
            messagebox.showerror(app.text("library_title"), app.text("library_name_invalid"))
            return
        if target.exists():
            messagebox.showerror(app.text("library_title"), app.text("library_name_exists"))
            return
        try:
            if item.cbz:
                _fs_retry(item.cbz.rename, target.with_name(target.name + ".cbz"))
            _fs_retry(item.folder.rename, target)
        except OSError as exc:
            messagebox.showerror(app.text("generic_error"), str(exc))
            return
        self.app.write_log(app.text("library_renamed", old=item.name, new=new_name))
        self.rescan()
        self.refresh_items()

    def delete_item(self, item: ArchiveItem):
        app = self.app
        if not item.folder.exists():
            messagebox.showerror(app.text("library_title"), app.text("library_missing"))
            return
        if item.has_cbz:
            prompt = app.text("library_confirm_delete", name=item.name, pages=item.page_count)
        else:
            prompt = app.text("library_confirm_delete_cbz", name=item.name)
        if not messagebox.askyesno(app.text("library_delete"), prompt, icon="warning"):
            return
        try:
            _fs_retry(shutil.rmtree, item.folder)
            if item.has_cbz:
                _fs_retry(item.cbz.unlink)
        except OSError as exc:
            messagebox.showerror(app.text("generic_error"), str(exc))
            return
        self.app.write_log(app.text("library_deleted", name=item.name))
        self.rescan()
        self.refresh_items()


# Persisted user preferences (Phase 7).
SETTING_DEFAULTS = {
    "timeout": 30,
    "retries": 3,
    "naming": "",
    "sound": True,
    "notify": True,
    "close_to_tray": True,
    "language": "en",
    "theme": "dark",
    "density": "comfortable",
}


class AppSettings:
    """Persisted user preferences, stored atomically next to the queue file."""

    def __init__(self, path: Path):
        self.path = path
        self.values = dict(SETTING_DEFAULTS)
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for key, default in SETTING_DEFAULTS.items():
            value = data.get(key, default)
            if isinstance(value, type(default)):
                self.values[key] = value

    def save(self):
        """Write via temp file + os.replace so a crash never corrupts settings."""
        temp = self.path.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.path)
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, key: str):
        return self.values.get(key, SETTING_DEFAULTS.get(key))

    def set(self, key: str, value):
        if key in SETTING_DEFAULTS and isinstance(value, type(SETTING_DEFAULTS[key])):
            self.values[key] = value

    def reset(self):
        self.values = dict(SETTING_DEFAULTS)
        self.save()


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
        # Phase 10.1: set by main() to enforce a single app instance.
        self.guard = None
        # Phase 10.2: allow tests to detach the process-wide crash hook.
        self._crash_hook_token = None
        self.tray_icon = None
        self.toasts: list[tk.Toplevel] = []
        self.settings = AppSettings(self.get_settings_file())
        self.history_file = self.get_history_file()
        self.history = HistoryStore(self.history_file)
        self.current_history_id: str | None = None
        self.history_status_filter = "all"
        self.history_sort = "newest"
        self.current_page = "downloader"
        self.page_frames: dict[str, tk.Widget] = {}
        self.queue_tasks: list[QueueTask] = []
        self.queue_file = self.get_queue_file()
        self.load_queue()
        self.queue_running = False
        self.queue_paused = False
        self.active_task: QueueTask | None = None
        self.viewed_task: QueueTask | None = None
        self.queue_stop_event = threading.Event()
        self.queue_pause_event = threading.Event()

        self.url_var = tk.StringVar(value="")
        self.output_var = tk.StringVar(value="")
        self.language_var = tk.StringVar(value="en")
        # Plain attribute mirrored from language_var on the main thread so
        # background threads (system tray) can resolve labels without
        # touching tkinter variables.
        self.current_language = self.settings.get("language")
        self.language_var.set(self.current_language)
        self.settings_timeout_var = tk.IntVar(value=int(self.settings.get("timeout")))
        self.settings_retries_var = tk.IntVar(value=int(self.settings.get("retries")))
        self.settings_naming_var = tk.StringVar(value="")
        self.settings_sound_var = tk.BooleanVar(value=bool(self.settings.get("sound")))
        self.settings_notify_var = tk.BooleanVar(value=bool(self.settings.get("notify")))
        self.settings_tray_var = tk.BooleanVar(value=bool(self.settings.get("close_to_tray")))
        self.settings_lang_var = tk.StringVar(value="English")
        self.settings_theme_var = tk.StringVar(value="")
        self.settings_density_var = tk.StringVar(value="")
        self.text_widgets = {}
        self.chapter_count = tk.IntVar(value=1)
        self.delay_var = tk.DoubleVar(value=1.0)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.convert_var = tk.BooleanVar(value=True)
        self.cbz_var = tk.BooleanVar(value=True)
        self.history_search_var = tk.StringVar(value="")
        self.log_collapsed = False
        self.page_progress_text = tk.StringVar(value=UI_TEXT["en"]["page_not_started"])
        self.overall_progress_text = tk.StringVar(value=UI_TEXT["en"]["overall_not_started"])
        self.status_text = tk.StringVar(value=UI_TEXT["en"]["ready"])
        self.transfer_bytes = 0
        self.transfer_samples: list[tuple[float, int]] = []
        self.transfer_eta_stable = False
        self.transfer_eta_stable_since = 0.0
        self.transfer_stable_rate = None
        self.eta_pages_done = 0
        self.eta_pages_total = 0
        # Phase 10.5: per-attempt transfer snapshot for history events.
        self._task_pages_total = 0
        self._task_bytes_delta = 0
        self._task_paused_seconds = 0.0
        self._last_transfer_snapshot: tuple[str, dict] | None = None
        self._task_log_dirty = False  # pump-level task-log coalescing
        self._log_editable = False    # mirror of the activity log's Tk state

        self.setup_theme()
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_tray()
        self.root.after(100, self.process_events)
        # Phase 10.2: fatal errors must leave a trace and surface a toast.
        install_crash_logging(self)
        # Phase 10.1: watch for show requests from a second launch.
        self.root.after(300, self._poll_show_requests)
        # Phase 10.4: seed the aggregate queue progress header.
        self.update_queue_progress()

    @staticmethod
    def _app_data_dir() -> Path:
        base = Path.home() / "AppData" / "Roaming" / "MangaDownloader"
        if sys.platform != "win32":
            base = Path.home() / ".manga-downloader"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @classmethod
    def get_history_file(cls) -> Path:
        return cls._app_data_dir() / "history.db"

    @classmethod
    def get_queue_file(cls) -> Path:
        return cls._app_data_dir() / "queue.json"

    @classmethod
    def get_settings_file(cls) -> Path:
        return cls._app_data_dir() / "settings.json"

    def load_queue(self):
        """Load queue.json; Phase 10.3 recovers from a backup on corruption."""
        try:
            data = json.loads(self.queue_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("tasks"), list):
                raise ValueError("queue.json schema mismatch")
            self.queue_tasks = [QueueTask.from_dict(item) for item in data["tasks"]
                                if isinstance(item, dict)]
        except (OSError, ValueError, TypeError, AttributeError):
            # Keep the damaged file for inspection, restore the newest .bak.
            try:
                if self.queue_file.exists():
                    self.queue_file.replace(self.queue_file.with_suffix(".json.corrupt"))
            except OSError:
                pass
            self.queue_tasks = []
            try:
                backups = sorted(self.queue_file.parent.glob(self.queue_file.name + ".*.bak"))
                if backups:
                    shutil.copy2(backups[-1], self.queue_file)
                    data = json.loads(self.queue_file.read_text(encoding="utf-8"))
                    self.queue_tasks = [QueueTask.from_dict(item) for item in data.get("tasks", [])
                                        if isinstance(item, dict)]
            except (OSError, ValueError, TypeError, AttributeError):
                self.queue_tasks = []
        # Crash recovery: a task left "active" by a previous session goes back to the queue.
        for task in self.queue_tasks:
            if task.state == "active":
                task.state = "queued"

    def save_queue(self):
        """Persist the queue via a temp file + os.replace for crash safety."""
        payload = {"tasks": [task.to_dict() for task in self.queue_tasks]}
        temp = self.queue_file.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temp, self.queue_file)
            self._backup_queue()
        except OSError:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass

    def _backup_queue(self):
        """Phase 10.3: timestamped queue.json backup; keep the newest 3."""
        try:
            stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            shutil.copy2(self.queue_file, self.queue_file.with_name(self.queue_file.name + f".{stamp}.bak"))
            for old in sorted(self.queue_file.parent.glob(self.queue_file.name + ".*.bak"))[:-3]:
                old.unlink(missing_ok=True)
        except OSError:
            pass

    def update_hints(self):
        """Phase 10.7: first-run hints shown while a section has no content."""
        if self.closing:
            return
        try:
            if hasattr(self, "hint_queue"):
                self.hint_queue.configure(
                    text="" if self.queue_tasks else self.text("hint_queue"))
            if hasattr(self, "hint_history"):
                self.hint_history.configure(
                    text="" if self.history.count() else self.text("hint_history"))
        except tk.TclError:
            pass  # widgets gone during shutdown

    def record_transfer_event(self, task):
        """Phase 10.5: persist the attempt's transfer totals as a history event.

        The worker pushes a snapshot through the pump (no shared state read
        here). Called after update_history_for_task so the record exists.
        """
        snapshot = getattr(self, "_last_transfer_snapshot", None)
        if snapshot is None or snapshot[0] != task.id or not snapshot[1]:
            return
        value = snapshot[1]
        record_id = f"{task.id}-q"
        self.history.add_event(
            record_id, "transfer",
            self.text("history_transfer", pages=value["pages"],
                      bytes=self.format_bytes(value["bytes"]),
                      paused=self.format_duration(value["paused"]),
                      attempts=task.attempts),
        )

    def update_queue_progress(self):
        """Phase 10.4: aggregate queue progress (main thread, no new state)."""
        total = len(self.queue_tasks)
        if hasattr(self, "queue_progress_label"):
            if not total:
                self.queue_progress_label.configure(text=self.text("queue_progress_idle"))
            else:
                states = [task.state for task in self.queue_tasks]
                done = sum(1 for s in states if s in {"completed", "failed", "stopped"})
                self.queue_progress_label.configure(text=self.text(
                    "queue_progress", done=done, total=total,
                    completed=states.count("completed"), failed=states.count("failed"),
                    bytes=self.format_bytes(self.queue_bytes_done())))
        if hasattr(self, "queue_progress"):
            self.queue_progress.configure(maximum=total or 1, value=done if total else 0)

    def queue_bytes_done(self) -> int:
        """Bytes banked by finalized tasks plus the live partial of the active task."""
        done = sum(getattr(task, "bank_bytes", 0) for task in self.queue_tasks)
        active = self.active_task
        if active is not None and active.state not in {"completed", "failed", "stopped"}:
            done += getattr(active, "total_bytes", 0)
        return done

    def text(self, key: str, language: str | None = None, **values) -> str:
        if language is None:
            language = self.current_language
        return UI_TEXT[language][key].format(**values)

    def register_text(self, key: str, widget):
        self.text_widgets[key] = widget
        return widget

    # ---------- transfer statistics (Phase 5) ----------

    @staticmethod
    def format_bytes(count: float) -> str:
        count = float(count)
        for unit in ("B", "KB", "MB", "GB"):
            if count < 1024 or unit == "GB":
                return f"{count:.0f} {unit}" if unit == "B" else f"{count:.1f} {unit}"
            count /= 1024
        return f"{count:.1f} GB"

    @staticmethod
    def format_duration(seconds: float) -> str:
        seconds = max(int(round(seconds)), 0)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:d}:{secs:02d}"

    def reset_transfer_stats(self):
        self.transfer_bytes = 0
        self.transfer_samples = []  # (timestamp, cumulative bytes)
        self.transfer_eta_stable = False
        self.transfer_eta_stable_since = 0.0
        self.transfer_stable_rate = None
        self.eta_pages_done = 0
        self.eta_pages_total = 0

    def note_transfer_bytes(self, bytes_received: int):
        """Track bytes/samples and compute the smoothed ETA (main thread only)."""
        now = time.monotonic()
        self.transfer_bytes = bytes_received
        if bytes_received <= 0:
            # New chapter: freeze the rate/ETA until fresh samples arrive.
            self.transfer_eta_stable = False
            return
        self.transfer_samples.append((now, bytes_received))
        self.transfer_samples[:] = [sample for sample in self.transfer_samples if now - sample[0] <= 10.0]
        if len(self.transfer_samples) < 3:
            self.transfer_eta_stable = False
            self.transfer_eta_stable_since = now
            return
        span = now - self.transfer_samples[0][0]
        if span < 1e-6:
            return
        rate = (self.transfer_samples[-1][1] - self.transfer_samples[0][1]) / span / 1024.0
        if self.transfer_stable_rate is not None:
            ratio = abs(rate - self.transfer_stable_rate) / max(self.transfer_stable_rate, 1e-6)
            stable = ratio <= 0.25
            self.transfer_stable_rate = self.transfer_stable_rate * 0.7 + rate * 0.3
        else:
            stable = False
            self.transfer_stable_rate = rate
        if stable and not self.transfer_eta_stable:
            self.transfer_eta_stable = True
            self.transfer_eta_stable_since = now
        elif not stable:
            self.transfer_eta_stable = False
            self.transfer_eta_stable_since = now

    def transfer_summary(self, rate_kbps: float) -> tuple[str, str]:
        """Return (speed_text, eta_text) for the given smoothed rate.

        The ETA covers the remaining pages of the current chapter, estimated
        from the average bytes per finished page divided by the smoothed
        rate. It only shows once the rate has been stable long enough.
        """
        speed = self.text("speed_value", kbps=f"{rate_kbps:.0f}")
        eta = self.text("eta_pending")
        if (not self.transfer_eta_stable or self.transfer_stable_rate is None
                or time.monotonic() - self.transfer_eta_stable_since < 3.0
                or self.eta_pages_done < 3 or self.eta_pages_total <= self.eta_pages_done):
            return speed, eta
        avg_page_bytes = self.transfer_bytes / self.eta_pages_done
        remaining_bytes = (self.eta_pages_total - self.eta_pages_done) * avg_page_bytes
        remaining_seconds = remaining_bytes / 1024.0 / max(self.transfer_stable_rate, 1e-6)
        return speed, self.text("eta_value", time=self.format_duration(remaining_seconds))
    # Status-bar state label -> indicator dot color (theme-aware instance
    # copy is rebuilt in setup_theme; this class dict is the fallback used
    # before setup_theme runs).
    STATE_COLORS = {
        "ready": "#49d69c",
        "state_paused": "#fbbf24",
        "state_preparing": "#fbbf24",
        "state_downloading": "#7c5cff",
        "status_downloading_speed": "#7c5cff",
        "downloading": "#7c5cff",
        "state_active": "#7c5cff",
        "state_converting": "#38bdf8",
        "state_creating_cbz": "#38bdf8",
        "stopping": "#fbbf24",
        "status_complete": "#49d69c",
        "queue_done": "#49d69c",
        "status_stopped": "#94a3b8",
        "queue_paused": "#94a3b8",
        "status_error": "#f87171",
    }

    def set_state(self, text_key: str, **values):
        """Single entry point for the status bar: label text + dot color."""
        self.status_text.set(self.text(text_key, **values))
        self.state_dot.configure(fg=self.STATE_COLORS.get(text_key, self.colors["muted"]))

    # Queue row state -> Treeview tag. Colors resolve from the theme at
    # refresh time (see refresh_queue_tree).
    STATE_TAGS = {
        "queued": "st-neutral",
        "active": "st-run",
        "paused": "st-warn",
        "completed": "st-ok",
        "stopped": "st-neutral",
        "failed": "st-err",
    }

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
        self.tray_icon = pystray.Icon("manga_downloader", self.tray_image(), f"Manga Downloader v{APP_VERSION}", menu)
        threading.Thread(target=self.tray_icon.run, name="system-tray", daemon=True).start()

    def show_window(self):
        self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        # Keep the title with version visible even without a terminal.
        self.root.title(self.text("window_title") + f"  ·  v{APP_VERSION}")

    def _poll_show_requests(self):
        """Phase 10.1/10.8: surface the window; prefill a second launch's URL."""
        if self.closing:
            return
        if self.guard is not None:
            payload = self.guard.is_show_requested()
            if payload and payload != "show":
                self.url_var.set(payload)
            if payload:
                self._show_window()
        self._poll_after_id = self.root.after(300, self._poll_show_requests)

    def log_history(self) -> list[str]:
        """Return up to 200 recent activity log lines (crash log tail)."""
        try:
            return self.log.get("end-199l", "end").splitlines()
        except Exception:
            return []

    def on_close(self):
        if self.closing:
            return
        if self.tray_icon is None or not self.settings.get("close_to_tray"):
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
        if self.queue_running:
            self.queue_stop_event.set()
        for task in self.queue_tasks:
            if task.state == "active":
                task.state = "queued"
        self.save_queue()
        self.closing = True
        # Cancel the pending pump tick so it cannot fire on a destroyed app.
        pending_tick = getattr(self, "_events_after_id", None)
        if pending_tick:
            try:
                self.root.after_cancel(pending_tick)
            except Exception:
                pass
        # Phase 10.1: cancel the guard poll tick too, same reasoning.
        poll_tick = getattr(self, "_poll_after_id", None)
        if poll_tick:
            try:
                self.root.after_cancel(poll_tick)
            except Exception:
                pass
        self.close_all_toasts()
        if self.tray_icon is not None:
            self.tray_icon.stop()
        self.root.destroy()

    def add_history(self, url: str, output_root: Path, selected_count: int):
        record_id = _unique_id()
        self.history.add_record(
            {
                "id": record_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": url,
                "output": str(output_root),
                "status": self.text("state_downloading"),
                "details": self.text("task_progress_chapters", count=0),
                "url": url,
                "chapters": 0,
                "pages": 0,
            }
        )
        self.history.add_event(record_id, "started", url)
        self.current_history_id = record_id
        self.refresh_history()

    def update_history(self, status: str, details: str):
        if not self.current_history_id:
            return
        self.history.update_record(self.current_history_id, status=status, details=details)
        self.history.add_event(self.current_history_id, "finished", details)
        self.history.backup()
        self.refresh_history()

    def update_history_for_task(self, task: QueueTask):
        """Write a finished queue task into the download history database.

        A retried task reuses its record id, so the entry is updated in place
        instead of duplicating rows in the history tree.
        """
        record_id = f"{task.id}-q"
        details = task.progress or task.state
        self.history.add_record(
            {
                "id": record_id,
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source": task.url,
                "output": task.output_root,
                "status": self.text(self._state_key(task.state)),
                "details": details,
                "url": task.url,
                "chapters": getattr(task, "last_chapters", 0) or 0,
                "pages": getattr(task, "last_pages", 0) or 0,
            }
        )
        self.history.add_event(record_id, "finished", details)
        self.history.backup()
        self.refresh_history()

    # History status labels written by older versions; a filter must match
    # records regardless of the UI language they were saved in.
    HISTORY_FILTER_MAP = {
        "done": {"Complete", "Completed", "Hoàn tất"},
        "failed": {"Error", "Failed", "Có lỗi", "Lỗi"},
        "stopped": {"Stopped", "Paused", "Đã dừng", "Tạm dừng"},
    }

    def _history_records(self) -> list[dict]:
        order = {
            "newest": ("created_at", True),
            "oldest": ("created_at", False),
            "source": ("source", False),
        }.get(self.history_sort, ("created_at", True))
        return self.history.search(
            query=self.history_search_var.get().strip().lower(),
            status_values=self.HISTORY_FILTER_MAP.get(self.history_status_filter),
            order_by=order[0],
            descending=order[1],
        )[:200]

    def refresh_history(self):
        if not hasattr(self, "history_tree"):
            return
        trees = [self.history_tree]
        if hasattr(self, "history_detail_tree"):
            trees.append(self.history_detail_tree)
        records = self._history_records()
        previous = {iid.split("-", 1)[1] for iid in self.history_tree.selection()}
        for tree in trees:
            for item in tree.get_children():
                tree.delete(item)
            for record in records[:30]:
                tree.insert(
                    "", "end", iid=f"{id(tree)}-{record.get('id')}",
                    values=(record.get("time", ""), record.get("source", ""), record.get("status", ""), record.get("details", "")),
                )
            if tree is not self.history_tree and previous:
                restored = [iid for iid in tree.get_children() if iid.split("-", 1)[1] in previous]
                if restored:
                    tree.selection_set(restored[0])
        if previous:
            restored = [iid for iid in self.history_tree.get_children() if iid.split("-", 1)[1] in previous]
            if restored:
                self.history_tree.selection_set(restored[0])
        if hasattr(self, "history_count_label"):
            self.history_count_label.configure(text=self.text("history_records", count=len(records)))
        self.update_hints()

    # ---------- history record actions (Phase 4) ----------

    def _selected_history_records(self) -> list[dict]:
        if not hasattr(self, "history_tree"):
            return []
        selection = set(self.history_tree.selection())
        wanted = {iid.split("-", 1)[1] for iid in selection}
        found = [record for record in self._history_records() if record.get("id") in wanted]
        return found

    def on_history_select(self, _event=None):
        if not hasattr(self, "history_events_tree"):
            return
        tree = self.history_events_tree
        tree.delete(*tree.get_children())
        records = self._selected_history_records()
        if not records:
            return
        for event in self.history.events(records[0].get("id", "")):
            message = event["message"]
            if event["kind"] == "finished":
                message = self.text("event_finished", message=message)
            elif event["kind"] == "started":
                message = self.text("event_started")
            tree.insert("", "end", values=(event["ts"], message))

    def export_history(self):
        records = self._history_records()
        if not records:
            messagebox.showinfo(self.text("history"), self.text("history_no_selection"))
            return
        default = f"history-{datetime.now():%Y%m%d-%H%M%S}.csv"
        target = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default,
            filetypes=(("CSV", "*.csv"), ("All files", "*.*")),
        )
        if not target:
            return
        try:
            with open(target, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(("time", "source", "output", "status", "details", "chapters", "pages"))
                for record in records:
                    writer.writerow(
                        (
                            record.get("time", ""), record.get("source", ""), record.get("output", ""),
                            record.get("status", ""), record.get("details", ""),
                            record.get("chapters", 0), record.get("pages", 0),
                        )
                    )
        except OSError as exc:
            messagebox.showerror(self.text("generic_error"), str(exc))
            return
        self.write_log(self.text("history_exported", path=target))

    def delete_history_records(self):
        records = self._selected_history_records()
        if not records:
            messagebox.showinfo(self.text("history"), self.text("history_no_selection"))
            return
        if not messagebox.askyesno(
            self.text("history_delete"),
            self.text("history_confirm_delete", count=len(records)),
        ):
            return
        removed = self.history.delete_records(record.get("id") for record in records)
        if removed:
            self.write_log(self.text("history_deleted", count=removed))
        self.refresh_history()

    def copy_history_url(self):
        records = self._selected_history_records()
        if not records:
            messagebox.showinfo(self.text("history"), self.text("history_no_selection"))
            return
        url = records[0].get("url") or records[0].get("source", "")
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        self.write_log(self.text("history_copied"))

    def open_history_folder(self):
        records = self._selected_history_records()
        if not records:
            messagebox.showinfo(self.text("history"), self.text("history_no_selection"))
            return
        folder = Path(records[0].get("output", "")).expanduser()
        if not folder.is_dir():
            messagebox.showerror(self.text("missing_folder"), str(folder))
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606 - intended Explorer launch
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc:
            messagebox.showerror(self.text("generic_error"), str(exc))

    def retry_history_records(self):
        records = self._selected_history_records()
        if not records:
            messagebox.showinfo(self.text("history"), self.text("history_no_selection"))
            return
        added = 0
        for record in records:
            url = record.get("url") or record.get("source", "")
            output = record.get("output", "")
            if not url or not output:
                continue
            try:
                url = downloader.normalize_url(url)
            except ValueError:
                continue
            task = QueueTask(
                url=url,
                output_root=output,
                chapter_count=1,
                delay=1.0,
                overwrite=False,
                convert_webp=True,
                create_cbz=True,
            )
            self.queue_tasks.append(task)
            self.write_log(self.text("task_state_changed", state=self.queue_state_text(task), url=url, details=""))
            added += 1
        if added:
            self.save_queue()
            self.refresh_queue_tree()

    def _on_history_filter_changed(self, _event=None):
        index = max(self.history_filter_combo.current(), 0)
        self.history_status_filter = ("all", "done", "failed", "stopped")[index]
        self.refresh_history()

    def _on_history_sort_changed(self, _event=None):
        index = max(self.history_sort_combo.current(), 0)
        self.history_sort = ("newest", "oldest", "source")[index]
        self.refresh_history()

    def _sync_history_combobox_values(self):
        self.history_filter_combo.configure(
            values=(self.text("filter_all"), self.text("filter_done"), self.text("filter_failed"), self.text("filter_stopped"))
        )
        self.history_filter_combo.current(("all", "done", "failed", "stopped").index(self.history_status_filter))
        self.history_sort_combo.configure(
            values=(self.text("sort_newest"), self.text("sort_oldest"), self.text("sort_source"))
        )
        self.history_sort_combo.current(("newest", "oldest", "source").index(self.history_sort))

    # ---------- download queue (Phase 2) ----------

    @staticmethod
    def _state_key(state: str) -> str:
        return {
            "queued": "state_queued",
            "active": "state_active",
            "paused": "state_paused",
            "completed": "state_completed",
            "stopped": "state_stopped",
            "failed": "state_failed",
        }.get(state, "state_queued")

    def queue_state_text(self, task: QueueTask) -> str:
        return self.text(self._state_key(task.state))

    def refresh_queue_tree(self):
        self.update_queue_progress()
        self.update_hints()
        if not hasattr(self, "queue_tree"):
            return
        tree = self.queue_tree
        tree.delete(*tree.get_children())
        for task in self.queue_tasks:
            tree.insert(
                "", "end", iid=task.id,
                values=(self.queue_state_text(task), task.url, task.progress or "—", task.output_root),
                tags=(self.STATE_TAGS.get(task.state, "st-neutral"),),
            )

    def refresh_task_log(self):
        """Redraw the per-task log, appending only lines rendered before.

        log_lines is append-only while a task runs, so a full rebuild on every
        emitted line is O(N^2) over a long download. Keep the rendered line
        count and append only the delta; switch tasks or shrinking lines
        (rare: reload) fall back to one full redraw.
        """
        if not hasattr(self, "task_log"):
            return
        task = self.viewed_task or self.active_task
        cache = getattr(self, "_task_log_cache", None)
        # Incremental append is only valid for a live task whose log_lines is
        # the same list and has not shrunk; anything else falls back to one
        # full redraw (which also handles the empty placeholder).
        usable = (cache is not None and task is not None and cache[0] is task
                  and isinstance(task.log_lines, list)
                  and len(task.log_lines) >= cache[1])
        if usable:
            new_lines = task.log_lines[cache[1]:]
            if not new_lines:
                return
            self.task_log.configure(state="normal")
            for line in new_lines:
                self.task_log.insert("end", line.rstrip() + "\n")
            self.task_log.see("end")
            self.task_log.configure(state="disabled")
            self._task_log_cache = (task, cache[1] + len(new_lines))
            return
        self.task_log.configure(state="normal")
        self.task_log.delete("1.0", "end")
        if task is not None and task.log_lines:
            for line in task.log_lines:
                self.task_log.insert("end", line.rstrip() + "\n")
            self.task_log.see("end")
        else:
            self.task_log.insert("end", self.text("task_log_empty") + "\n")
        self.task_log.configure(state="disabled")
        self._task_log_cache = (task, len(task.log_lines) if task is not None else 0)

    def on_queue_select(self, _event=None):
        selected = self.selected_queue_tasks()
        self.viewed_task = selected[0] if selected else None
        self.refresh_task_log()

    def add_queue_task(self):
        try:
            url = downloader.normalize_url(self.url_var.get())
            delay = float(self.delay_var.get())
            if delay < 0:
                raise ValueError(self.text("delay_invalid"))
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror(self.text("invalid_settings"), str(exc))
            return
        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror(self.text("missing_folder"), self.text("choose_folder_first"))
            return
        task = QueueTask(
            url=url,
            output_root=str(Path(output).expanduser()),
            chapter_count=self.chapter_count.get(),
            delay=delay,
            overwrite=self.overwrite_var.get(),
            convert_webp=self.convert_var.get(),
            create_cbz=self.cbz_var.get(),
        )
        self.queue_tasks.append(task)
        self.save_queue()
        self.refresh_queue_tree()
        self.write_log(self.text("task_state_changed", state=self.queue_state_text(task), url=url, details=""))

    def selected_queue_tasks(self) -> list[QueueTask]:
        if not hasattr(self, "queue_tree"):
            return []
        by_id = {task.id: task for task in self.queue_tasks}
        return [by_id[iid] for iid in self.queue_tree.selection() if iid in by_id]

    def remove_queue_tasks(self):
        selected = self.selected_queue_tasks()
        removable = [task for task in selected if not (self.queue_running and task.state == "active")]
        for task in removable:
            self.write_log(self.text("queue_removed", url=task.url))
            self.queue_tasks.remove(task)
        if removable:
            self.save_queue()
            self.refresh_queue_tree()

    def move_queue_tasks(self, offset: int):
        selected = self.selected_queue_tasks()
        if not selected:
            return
        ids = [task.id for task in selected]
        if offset < 0:
            ordered = [t for t in self.queue_tasks if t.id in ids] + [t for t in self.queue_tasks if t.id not in ids]
        else:
            ordered = [t for t in self.queue_tasks if t.id not in ids] + [t for t in self.queue_tasks if t.id in ids]
        self.queue_tasks = ordered
        self.save_queue()
        self.refresh_queue_tree()

    def retry_failed_tasks(self):
        changed = False
        for task in self.queue_tasks:
            if task.state in {"failed", "stopped", "paused"}:
                task.state = "queued"
                task.progress = ""
                task.attempts = 0
                changed = True
        if changed:
            self.save_queue()
            self.refresh_queue_tree()

    def clear_completed_tasks(self):
        before = len(self.queue_tasks)
        self.queue_tasks = [task for task in self.queue_tasks if task.state != "completed"]
        if len(self.queue_tasks) != before:
            self.save_queue()
            self.refresh_queue_tree()

    def start_queue(self):
        if (self.worker and self.worker.is_alive()) or self.queue_running:
            messagebox.showinfo(self.text("queue"), self.text("queue_busy"))
            return
        runnable_states = {"queued", "failed", "stopped", "paused"}
        selected = [task for task in self.selected_queue_tasks() if task.state in runnable_states]
        pending = selected or [task for task in self.queue_tasks if task.state in runnable_states]
        if not pending:
            messagebox.showinfo(self.text("queue"), self.text("queue_no_tasks"))
            return
        for task in pending:
            task.state = "queued"
            task.progress = ""
        QueueTask.MAX_ATTEMPTS = max(1, int(self.settings.get("retries")))
        self.save_queue()
        self.refresh_queue_tree()
        self.queue_running = True
        self.queue_paused = False
        self.queue_stop_event.clear()
        self.queue_pause_event.clear()
        self.write_log(self.text("queue_started", count=len(pending)))
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.queue_start_button.configure(state="disabled")
        self.queue_stop_button.configure(state="normal")
        self.queue_pause_button.configure(state="normal")
        self.queue_resume_button.configure(state="disabled")
        self.worker = threading.Thread(target=self.queue_worker, args=(pending,), daemon=True)
        self.worker.start()

    def pause_queue(self):
        """Request a pause; takes effect after the current page request."""
        if not self.queue_running or self.queue_paused:
            return
        self.queue_paused = True
        self.queue_pause_event.set()
        self.set_state("state_paused")
        self.write_log(self.text("pause_requested"))
        self.queue_pause_button.configure(state="disabled")
        self.queue_resume_button.configure(state="normal")

    def resume_queue(self):
        if not self.queue_paused:
            return
        self.queue_paused = False
        self.queue_pause_event.clear()
        self.write_log(self.text("queue_resumed"))
        self.queue_resume_button.configure(state="disabled")
        self.queue_pause_button.configure(state="normal")
        self.set_state("state_active")

    def stop_queue(self):
        if self.queue_running:
            self.queue_stop_event.set()
            self.stop_event.set()
            self.set_state("stopping")
            self.write_log(self.text("stopping"))

    def queue_worker(self, pending: list[QueueTask]):
        """Run queue tasks one by one with bounded retries; background thread."""
        language = self.current_language
        queue_cancelled = False
        for task in pending:
            if self.queue_stop_event.is_set():
                task.state = "queued"
                self.emit("queue_state", (task, ""))
                continue
            if self.hold_for_pause(task):
                queue_cancelled = True
                break
            self.emit("active_task", task)
            task.state = "active"
            self.emit("queue_state", (task, ""))
            task.log_lines.append(f"[{datetime.now():%H:%M:%S}] {task.url}")
            self.emit("task_log", task)
            self.reset_transfer_stats()
            outcome, chapters = self.run_task_with_retries(task, language)
            if outcome == "completed":
                task.state = "completed"
                task.progress = self.text("task_progress_chapters", language, count=chapters)
                self.emit("queue_state", (task, task.progress))
                self.emit("queue_task_finished", (task, True))
            elif outcome == "stopped":
                task.state = "stopped"
                task.progress = self.text("stopped", language)
                self.emit("queue_state", (task, task.progress))
                self.emit("queue_task_finished", (task, False))
                queue_cancelled = True
                break
            else:
                self.emit("log", self.text("task_permanently_failed", language, attempts=task.attempts, url=task.url))
                self.emit("queue_task_finished", (task, False))
        if queue_cancelled:
            self.emit("queue_paused", None)
        else:
            self.emit("queue_done", None)

    def hold_for_pause(self, task: QueueTask) -> bool:
        """Park `task` while the queue is paused. True when stop was requested."""
        if not self.queue_pause_event.is_set():
            return False
        task.state = "paused"
        task.progress = ""
        self.emit("queue_state", (task, ""))
        while self.queue_pause_event.is_set() and not self.queue_stop_event.is_set():
            self.queue_pause_event.wait(0.2)
        task.state = "queued"
        self.emit("queue_state", (task, ""))
        return self.queue_stop_event.is_set()

    def run_task_with_retries(self, task: QueueTask, language: str):
        """Download a task with bounded exponential-backoff retries.

        Returns ("completed"|"stopped"|"failed", chapters_done).
        """
        chapters = 0
        for attempt in range(1, task.MAX_ATTEMPTS + 1):
            task.attempts = attempt
            self.emit("queue_state", (task, ""))
            try:
                chapters = self.download_worker(
                    task.url, task.delay, Path(task.output_root), task.chapter_count,
                    task.overwrite, task.convert_webp, task.create_cbz, language,
                    task=task, emit_terminal=False, pause_event=self.queue_pause_event,
                    timeout=self.settings.get("timeout"), naming=self.settings.get("naming"),
                )
                task.last_chapters = chapters
                task.last_pages = self._task_pages_total
                return "completed", chapters
            except downloader.DownloadCancelled:
                task.log_lines.append(self.text("stopped", language))
                self.emit("task_log", task)
                return "stopped", chapters
            except Exception as exc:
                task.state = "failed"
                task.progress = str(exc)
                self.emit("queue_state", (task, str(exc)))
                self.emit("task_log", task)
                if attempt >= task.MAX_ATTEMPTS:
                    break
                self.emit("log", self.text("attempt_failed", language, attempt=attempt, error=str(exc)))
                backoff = self.retry_backoff_seconds(attempt)
                self.emit("log", self.text("attempt_retry_in", language, seconds=backoff, next_attempt=attempt + 1, max_attempts=task.MAX_ATTEMPTS))
                # Bounded wait; only Stop can cut the backoff short.
                if self.queue_stop_event.wait(backoff):
                    return "stopped", chapters
        return "failed", chapters

    @staticmethod
    def retry_backoff_seconds(attempt: int) -> int:
        """Bounded exponential backoff: 2s, 4s, 8s... capped at 30s."""
        return min(2 ** attempt, 30)

    def change_language(self, _event=None):
        selected = self.language_combo.get()
        self.language_var.set("vi" if selected == "Tiếng Việt" else "en")
        self.current_language = "vi" if selected == "Tiếng Việt" else "en"
        self.settings.set("language", self.current_language)
        self.settings.save()
        language = self.current_language
        self.root.title(self.text("window_title", language) + f"  ·  v{APP_VERSION}")
        for key, widget in self.text_widgets.items():
            widget.configure(text=self.text(key, language))
        if not (self.worker and self.worker.is_alive()):
            self.page_progress_text.set(self.text("page_not_started", language))
            self.overall_progress_text.set(self.text("overall_not_started", language))
            self.set_state("ready")
        self.activity_toggle_button.configure(
            text=self.text("activity_log_show" if self.log_collapsed else "activity_log_hide", language)
        )
        if hasattr(self, "history_filter_combo"):
            self._sync_history_combobox_values()
        self._sync_settings_choices()
        if hasattr(self, "queue_progress_label"):
            self.update_queue_progress()
        # Registered hint labels got the raw template above; re-evaluate them
        # against the actual content state.
        self.update_hints()
        if getattr(self, "library_window", None) is not None and self.library_window.winfo_exists():
            self.library_window.relocalize()
        if hasattr(self, "history_events_tree"):
            self.history_events_tree.heading("ts", text=self.text("history_time"))
            self.history_events_tree.heading("message", text=self.text("history_events"))
        self.refresh_history()

    LIGHT_COLORS = {
        "bg": "#f4f6fb",
        "sidebar": "#ffffff",
        "card": "#ffffff",
        "input": "#eef1f7",
        "border": "#d4dbe7",
        "text": "#17233b",
        "muted": "#5f6b84",          # 5.3:1 on card (WCAG AA)
        "accent": "#6a48ff",
        "accent_hover": "#5b3fd6",
        "accent_press": "#4c33c4",
        "accent_strong": "#5b3fd6",  # primary fills that carry white text: 5.1:1
        "accent_text": "#5b3fd6",    # accent used AS TEXT on tint: 5.7:1
        "accent_disabled": "#ccd3ec",
        "green": "#0a7d54",          # 5.2:1 on white
        "danger": "#c2373b",         # 5.4:1 on white
        "warning": "#a16207",        # 4.9:1 on white
        "info": "#2563eb",
    }

    DARK_COLORS = {
        "bg": "#080b12",
        "sidebar": "#0b1019",
        "card": "#111823",
        "input": "#0c131d",
        "border": "#202c3b",
        "text": "#f1f5f9",
        "muted": "#7e89a6",          # 5.3:1 on card (WCAG AA)
        "accent": "#7c5cff",
        "accent_hover": "#9278ff",
        "accent_press": "#5f45d6",
        "accent_strong": "#6f52ee",  # primary fills that carry white text: 5.1:1
        "accent_text": "#b3a3ff",    # accent used AS TEXT on tint: 7.4:1
        "accent_disabled": "#40357c",
        "green": "#34d399",
        "danger": "#f87171",
        "warning": "#fbbf24",
        "info": "#38bdf8",
    }

    @staticmethod
    def _blend_hex(fg: str, bg: str, alpha: float) -> str:
        """Alpha-blend two #rrggbb colors (fg over bg) -> #rrggbb."""
        f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
        return "#" + "".join(f"{round(a * alpha + c * (1 - alpha)):02x}" for a, c in zip(f, b))

    def setup_theme(self):
        theme = "dark"
        density = "comfortable"
        if hasattr(self, "settings"):
            theme = self.settings.get("theme")
            density = self.settings.get("density")
        if theme == "system":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                theme = "light" if value else "dark"
            except (OSError, ImportError):
                theme = "dark"
        if theme == "light":
            self.colors = dict(self.LIGHT_COLORS)
        else:
            self.colors = dict(self.DARK_COLORS)
        self.density = density
        # Theme-aware semantic colors (ported from the audited redesign demo):
        # every text-bearing color passes WCAG AA on its theme's surfaces.
        # Instance dicts shadow the class-level dark defaults.
        self.STATE_COLORS = {
            "ready": self.colors["green"],
            "state_paused": self.colors["warning"],
            "state_preparing": self.colors["warning"],
            "state_downloading": self.colors["accent_text"],
            "status_downloading_speed": self.colors["accent_text"],
            "downloading": self.colors["accent_text"],
            "state_active": self.colors["accent_text"],
            "state_converting": self.colors["info"],
            "state_creating_cbz": self.colors["info"],
            "stopping": self.colors["warning"],
            "status_complete": self.colors["green"],
            "queue_done": self.colors["green"],
            "status_stopped": self.colors["muted"],
            "queue_paused": self.colors["muted"],
            "status_error": self.colors["danger"],
        }
        self.TOAST_COLORS = {
            "success": self.colors["green"],
            "error": self.colors["danger"],
            "info": self.colors["accent"],
            "warning": self.colors["warning"],
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["card"], borderwidth=1, relief="solid")
        style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 20 if self.density == "compact" else 24, "bold"))
        style.configure("Subtitle.TLabel", background=self.colors["bg"], foreground=self.colors["muted"], font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 10, "bold"))
        style.configure("CardText.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.colors["card"], foreground=self.colors["muted"], font=("Segoe UI", 9, "bold"))
        style.configure("TEntry", fieldbackground=self.colors["input"], foreground=self.colors["text"], insertcolor=self.colors["text"], bordercolor=self.colors["border"], lightcolor=self.colors["border"], darkcolor=self.colors["border"], padding=10)
        style.map("TEntry", bordercolor=[("focus", self.colors["accent"])], lightcolor=[("focus", self.colors["accent"])])
        style.configure("TSpinbox", fieldbackground=self.colors["input"], foreground=self.colors["text"], arrowcolor=self.colors["muted"], bordercolor=self.colors["border"], padding=7)
        style.configure("TButton", background=self._blend_hex(self.colors["text"], self.colors["card"], 0.06), foreground=self.colors["text"], bordercolor=self.colors["border"], padding=(14, 9), font=("Segoe UI", 9, "bold"))
        style.map("TButton", background=[("active", self._blend_hex(self.colors["text"], self.colors["card"], 0.12)), ("disabled", self.colors["input"])], foreground=[("disabled", self.colors["muted"])])
        style.configure("Accent.TButton", background=self.colors["accent_strong"], foreground="white", bordercolor=self.colors["accent_strong"], padding=(18, 10), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton", background=[("active", self.colors["accent_press"]), ("disabled", self.colors["accent_disabled"])])
        style.configure("TCheckbutton", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", self.colors["card"])], foreground=[("disabled", "#687586")])
        style.configure("TRadiobutton", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 9))
        style.map("TRadiobutton", background=[("active", self.colors["card"])], foreground=[("disabled", "#687586")])
        style.configure("Horizontal.TProgressbar", troughcolor=self.colors["input"], background=self.colors["accent_strong"], bordercolor=self.colors["input"], lightcolor=self.colors["accent_strong"], darkcolor=self.colors["accent_strong"], thickness=9)
        style.configure("Big.Horizontal.TProgressbar", troughcolor=self.colors["input"], background=self.colors["accent_strong"], bordercolor=self.colors["input"], lightcolor=self.colors["accent_strong"], darkcolor=self.colors["accent_strong"], thickness=14)
        # Queue state chips (ported from the audited redesign demo): the whole
        # row gets the state tint (13% blend over card, like the demo's
        # rgba-tint chips) and the state text uses the AA-safe theme color.
        style.configure("Treeview", background=self.colors["card"], fieldbackground=self.colors["card"], foreground=self.colors["text"])
        style.configure("Treeview.Heading", background=self.colors["card"], foreground=self.colors["muted"])
        blend = self._blend_hex
        card = self.colors["card"]
        self._queue_tags = {
            "st-run": (self.colors["accent_text"], blend(self.colors["accent"], card, 0.13)),
            "st-ok": (self.colors["green"], blend(self.colors["green"], card, 0.12)),
            "st-warn": (self.colors["warning"], blend(self.colors["warning"], card, 0.14)),
            "st-err": (self.colors["danger"], blend(self.colors["danger"], card, 0.12)),
            "st-neutral": (self.colors["muted"], card),
        }

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
            # Active nav = soft accent fill (demo's active-nav tint) instead of
            # a solid block; white text keeps AA contrast on accent_strong.
            return tk.Button(
                sidebar, text=text, anchor="w", relief="flat", bd=0, cursor="hand2",
                bg=self._blend_hex(self.colors["accent"], self.colors["sidebar"], 0.16) if active else self.colors["sidebar"],
                fg=self.colors["accent_text"] if active else self.colors["muted"],
                activebackground=self._blend_hex(self.colors["accent"], self.colors["sidebar"], 0.26) if active else self.colors["input"],
                activeforeground=self.colors["accent_text"] if active else self.colors["text"], font=("Segoe UI", 10, "bold" if active else "normal"),
                padx=22, pady=12, command=command,
            )

        self.register_text("nav_downloader", nav_button("", active=True)).pack(fill="x", padx=12, pady=2)
        history_nav = nav_button("", command=self.show_history_window)
        library_nav = nav_button("", command=self.open_library)
        settings_nav = nav_button("", command=self.show_settings_window)
        self.register_text("nav_archive", history_nav).pack(fill="x", padx=12, pady=2)
        self.register_text("nav_library", library_nav).pack(fill="x", padx=12, pady=2)
        self.register_text("nav_settings", settings_nav).pack(fill="x", padx=12, pady=2)

        sidebar_bottom = tk.Frame(sidebar, bg=self.colors["sidebar"])
        sidebar_bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        self.register_text("local_workspace", tk.Label(sidebar_bottom, text="", bg=self.colors["sidebar"], fg=self.colors["green"], font=("Segoe UI", 8, "bold"))).pack(anchor="w")
        self.register_text("local_description", tk.Label(sidebar_bottom, text="", bg=self.colors["sidebar"], fg=self.colors["muted"], font=("Segoe UI", 8))).pack(anchor="w", pady=(5, 0))
        self.version_label = tk.Label(sidebar_bottom, text=f"v{APP_VERSION}", bg=self.colors["sidebar"], fg=self.colors["muted"], font=("Segoe UI", 8))
        self.version_label.pack(anchor="w", pady=(3, 0))

        main = ttk.Frame(shell, style="App.TFrame", padding=(26 if self.density == "compact" else 34,
                                                          20 if self.density == "compact" else 28,
                                                          26 if self.density == "compact" else 34,
                                                          14 if self.density == "compact" else 20))
        main.pack(side="left", fill="both", expand=True)
        self.main_area = main
        main.columnconfigure(0, weight=1)
        main.rowconfigure(8, weight=1)

        header = ttk.Frame(main, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        header.columnconfigure(0, weight=1)
        header_left = ttk.Frame(header, style="App.TFrame")
        header_left.grid(row=0, column=0, sticky="w")
        self.register_text("header_title", ttk.Label(header_left, text="", style="Title.TLabel")).pack(anchor="w")
        self.register_text("header_subtitle", ttk.Label(header_left, text="", style="Subtitle.TLabel")).pack(anchor="w", pady=(5, 0))
        header_right = ttk.Frame(header, style="App.TFrame")
        header_right.grid(row=0, column=1, sticky="e", padx=(20, 0))
        badge = tk.Label(header_right, text="", bg=self.colors["accent_strong"], fg="white", font=("Segoe UI", 8, "bold"), padx=10, pady=5)
        self.register_text("ui_badge", badge).pack(side="left", padx=(0, 16))
        self.register_text("language", ttk.Label(header_right, text="", style="Subtitle.TLabel")).pack(side="left", padx=(0, 8))
        self.language_combo = ttk.Combobox(header_right, values=("English", "Tiếng Việt"), state="readonly", width=13)
        # Keep the active language across UI rebuilds (apply_appearance).
        self.language_combo.current(0 if self.current_language == "en" else 1)
        self.language_combo.bind("<<ComboboxSelected>>", self.change_language)
        self.language_combo.pack(side="left")

        source_card = ttk.Frame(main, style="Card.TFrame", padding=20)
        source_card.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        source_card.columnconfigure(0, weight=1)
        self.register_text("source", ttk.Label(source_card, text="", style="Muted.TLabel")).grid(row=0, column=0, sticky="w")
        self.register_text("chapter_url", ttk.Label(source_card, text="", style="CardTitle.TLabel")).grid(row=1, column=0, sticky="w", pady=(10, 6))
        url_entry = ttk.Entry(source_card, textvariable=self.url_var)
        url_entry.grid(row=2, column=0, sticky="ew")
        Tooltip(url_entry, lambda: self.text("tip_url"))

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
        webp_check = self.register_text("webp_jpg", ttk.Checkbutton(output_options, text="", variable=self.convert_var))
        webp_check.grid(row=0, column=0, sticky="w", padx=(0, 14))
        cbz_check = self.register_text("create_cbz", ttk.Checkbutton(output_options, text="", variable=self.cbz_var))
        cbz_check.grid(row=0, column=1, sticky="w")
        redownload_check = self.register_text("redownload", ttk.Checkbutton(output_card, text="", variable=self.overwrite_var))
        redownload_check.pack(anchor="w", pady=(8, 0))
        Tooltip(webp_check, lambda: self.text("tip_webp"))
        Tooltip(cbz_check, lambda: self.text("tip_cbz"))
        Tooltip(redownload_check, lambda: self.text("tip_redownload"))

        folder_card = ttk.Frame(main, style="Card.TFrame", padding=20)
        folder_card.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        folder_card.columnconfigure(0, weight=1)
        self.register_text("output_folder", ttk.Label(folder_card, text="", style="Muted.TLabel")).grid(row=0, column=0, columnspan=2, sticky="w")
        folder_card.columnconfigure(1, weight=1)
        folder_card.columnconfigure(2, weight=0)
        folder_entry = ttk.Entry(folder_card, textvariable=self.output_var)
        folder_entry.grid(row=1, column=1, sticky="ew", pady=(9, 0), padx=(0, 10))
        choose_button = self.register_text("choose_folder", ttk.Button(folder_card, text="", command=self.choose_output))
        choose_button.grid(row=1, column=2, pady=(9, 0), padx=(0, 8))
        open_button = self.register_text("open_folder", ttk.Button(folder_card, text="", command=self.open_output_folder))
        open_button.grid(row=1, column=3, pady=(9, 0))
        Tooltip(choose_button, lambda: self.text("tip_choose_folder"))
        Tooltip(open_button, lambda: self.text("tip_open_folder"))

        actions = ttk.Frame(main, style="App.TFrame")
        actions.grid(row=4, column=0, sticky="ew", pady=(0, 18))
        self.register_text("start", ttk.Button(actions, text="", style="Accent.TButton", command=self.start))
        self.start_button = self.text_widgets["start"]
        self.start_button.pack(side="left")
        self.register_text("stop", ttk.Button(actions, text="", command=self.stop, state="disabled"))
        self.stop_button = self.text_widgets["stop"]
        self.stop_button.pack(side="left", padx=(9, 0))
        open_folder_action = self.register_text("open_folder_action", ttk.Button(actions, text="", command=self.open_output_folder))
        open_folder_action.pack(side="left", padx=(9, 0))
        Tooltip(self.start_button, lambda: self.text("tip_start"))
        Tooltip(self.stop_button, lambda: self.text("tip_stop"))
        Tooltip(open_folder_action, lambda: self.text("tip_open_folder"))
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
        self.history_count_label = ttk.Label(history_header, text="", style="Muted.TLabel")
        self.history_count_label.grid(row=0, column=1, sticky="e", padx=(0, 10))
        self.history_search_entry = ttk.Entry(history_header, textvariable=self.history_search_var, width=34)
        self.history_search_entry.grid(row=0, column=2, sticky="e")
        Tooltip(self.history_search_entry, lambda: self.text("tip_search_history"))
        self.history_search_var.trace_add("write", lambda *_args: self.refresh_history())
        history_tools = ttk.Frame(history_card, style="Card.TFrame")
        history_tools.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.register_text("history_filters", ttk.Label(history_tools, text="", style="Subtitle.TLabel")).pack(side="left", padx=(0, 6))
        self.history_filter_combo = ttk.Combobox(history_tools, state="readonly", width=14, values=())
        self.history_filter_combo.pack(side="left")
        self.history_filter_combo.bind("<<ComboboxSelected>>", self._on_history_filter_changed)
        Tooltip(self.history_filter_combo, lambda: self.text("tip_history_filter"))
        self.register_text("history_sort", ttk.Label(history_tools, text="", style="Subtitle.TLabel")).pack(side="left", padx=(16, 6))
        self.history_sort_combo = ttk.Combobox(history_tools, state="readonly", width=13, values=())
        self.history_sort_combo.pack(side="left")
        self.history_sort_combo.bind("<<ComboboxSelected>>", self._on_history_sort_changed)
        Tooltip(self.history_sort_combo, lambda: self.text("tip_history_sort"))
        self.history_export_button = self.register_text("history_export", ttk.Button(history_tools, text="", command=self.export_history))
        self.history_export_button.pack(side="right")
        self.history_delete_button = self.register_text("history_delete", ttk.Button(history_tools, text="", command=self.delete_history_records))
        self.history_delete_button.pack(side="right", padx=(0, 8))
        Tooltip(self.history_delete_button, lambda: self.text("tip_history_delete"))
        Tooltip(self.history_export_button, lambda: self.text("tip_history_export"))
        self.history_tree = ttk.Treeview(history_card, columns=("time", "source", "status", "details"), show="headings", height=4)
        for column, width in (("time", 145), ("source", 360), ("status", 120), ("details", 260)):
            self.history_tree.heading(column, text=self.text(f"history_{column}"))
            self.history_tree.column(column, width=width, anchor="w", stretch=column in {"source", "details"})
        self.history_tree.grid(row=2, column=0, sticky="ew")
        self.history_tree.bind("<<TreeviewSelect>>", self.on_history_select)
        self.hint_history = self.register_text("hint_history", ttk.Label(history_card, text="", style="Muted.TLabel", wraplength=640, justify="left"))
        self.hint_history.grid(row=3, column=0, sticky="w", pady=(6, 0))
        self._sync_history_combobox_values()
        self.refresh_history()
        self.update_hints()

        queue_card = ttk.Frame(main, style="Card.TFrame", padding=14)
        queue_card.grid(row=6, column=0, sticky="ew", pady=(0, 16))
        queue_card.columnconfigure(0, weight=1)
        queue_header = ttk.Frame(queue_card, style="Card.TFrame")
        queue_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        queue_header.columnconfigure(0, weight=1)
        self.register_text("queue", ttk.Label(queue_header, text="", style="Muted.TLabel")).grid(row=0, column=0, sticky="w")
        self.queue_start_button = self.register_text("queue_start", ttk.Button(queue_header, text="", command=self.start_queue))
        self.queue_start_button.grid(row=0, column=1, padx=(8, 0))
        self.queue_stop_button = self.register_text("queue_stop", ttk.Button(queue_header, text="", command=self.stop_queue, state="disabled"))
        self.queue_stop_button.grid(row=0, column=2, padx=(8, 0))
        self.queue_pause_button = self.register_text("queue_pause", ttk.Button(queue_header, text="", command=self.pause_queue, state="disabled"))
        self.queue_pause_button.grid(row=0, column=3, padx=(8, 0))
        self.queue_resume_button = self.register_text("queue_resume", ttk.Button(queue_header, text="", command=self.resume_queue, state="disabled"))
        self.queue_resume_button.grid(row=0, column=4, padx=(8, 0))
        Tooltip(self.queue_start_button, lambda: self.text("tip_queue_start"))
        queue_tools = ttk.Frame(queue_card, style="Card.TFrame")
        queue_tools.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        add_task_button = self.register_text("queue_add", ttk.Button(queue_tools, text="", command=self.add_queue_task))
        add_task_button.pack(side="left")
        Tooltip(add_task_button, lambda: self.text("tip_queue_add"))
        self.register_text("queue_remove", ttk.Button(queue_tools, text="", command=self.remove_queue_tasks)).pack(side="left", padx=(8, 0))
        self.register_text("queue_up", ttk.Button(queue_tools, text="", width=3, command=lambda: self.move_queue_tasks(-1))).pack(side="left", padx=(8, 0))
        self.register_text("queue_down", ttk.Button(queue_tools, text="", width=3, command=lambda: self.move_queue_tasks(1))).pack(side="left", padx=(8, 0))
        self.register_text("queue_retry", ttk.Button(queue_tools, text="", command=self.retry_failed_tasks)).pack(side="left", padx=(8, 0))
        self.register_text("queue_clear_completed", ttk.Button(queue_tools, text="", command=self.clear_completed_tasks)).pack(side="left", padx=(8, 0))
        self.queue_tree = ttk.Treeview(queue_card, columns=("state", "source", "progress", "output"), show="headings", height=4)
        for column, width in (("state", 110), ("source", 340), ("progress", 150), ("output", 240)):
            self.queue_tree.heading(column, text=self.text(f"queue_col_{column}"))
            self.queue_tree.column(column, width=width, anchor="w", stretch=column in {"source", "output"})
        for tag, (fg, bg) in getattr(self, "_queue_tags", {}).items():
            self.queue_tree.tag_configure(tag, foreground=fg, background=bg)
        self.queue_progress_label = ttk.Label(queue_card, text="", style="Muted.TLabel")
        self.queue_progress_label.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.queue_progress = ttk.Progressbar(queue_card, style="Big.Horizontal.TProgressbar", maximum=1, value=0)
        Tooltip(self.queue_progress, lambda: self.text("queue_progress_title"))
        self.queue_progress.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        self.queue_tree.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.queue_tree.bind("<<TreeviewSelect>>", self.on_queue_select)
        self.refresh_queue_tree()
        self.register_text("task_log_title", ttk.Label(queue_card, text="", style="Muted.TLabel")).grid(row=5, column=0, sticky="w", pady=(10, 4))
        self.task_log = ScrolledText(queue_card, height=5, state="disabled", wrap="word", bg=self.colors["input"], fg=self.colors["muted"], insertbackground=self.colors["text"], selectbackground=self.colors["accent_disabled"], relief="flat", borderwidth=0, padx=12, pady=8, font=("Consolas", 9))
        self.task_log.grid(row=6, column=0, sticky="ew")
        self.hint_queue = self.register_text("hint_queue", ttk.Label(queue_card, text="", style="Muted.TLabel", wraplength=640, justify="left"))
        self.hint_queue.grid(row=7, column=0, sticky="w", pady=(6, 0))
        self.refresh_task_log()

        log_card = ttk.Frame(main, style="Card.TFrame", padding=16)
        log_card.grid(row=8, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        log_header = ttk.Frame(log_card, style="Card.TFrame")
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 9))
        self.register_text("activity_log", ttk.Label(log_header, text="", style="Muted.TLabel")).pack(side="left")
        self.activity_toggle_button = ttk.Button(log_header, text="", width=10, command=self.toggle_log)
        self.activity_toggle_button.pack(side="right")
        clear_log_button = self.register_text("clear_log", ttk.Button(log_header, text="", command=self.clear_log))
        clear_log_button.pack(side="right", padx=(0, 8))
        Tooltip(clear_log_button, lambda: self.text("tip_clear_log"))
        self.log = ScrolledText(log_card, height=7 if self.density == "compact" else 9, state="disabled", wrap="word", bg=self.colors["input"], fg=self.colors["muted"], insertbackground=self.colors["text"], selectbackground=self.colors["accent_disabled"], relief="flat", borderwidth=0, padx=12, pady=10, font=("Consolas", 9))
        self.log.grid(row=1, column=0, sticky="nsew")

        status = tk.Frame(main, bg=self.colors["bg"])
        status.grid(row=9, column=0, sticky="ew", pady=(11, 0))
        self.state_dot = tk.Label(status, text="●", bg=self.colors["bg"], fg=self.colors["green"], font=("Segoe UI", 9))
        self.state_dot.pack(side="left")
        tk.Label(status, textvariable=self.status_text, bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))
        self.register_text("privacy", tk.Label(status, text="", bg=self.colors["bg"], fg=self.colors["muted"], font=("Segoe UI", 8))).pack(side="right")
        self.change_language()

    def show_history_window(self):
        self._show_auxiliary_window("history")

    def open_library(self):
        if hasattr(self, "library_window") and self.library_window.winfo_exists():
            self.library_window.deiconify()
            self.library_window.lift()
            self.library_window.focus_set()
            return
        self.library_window = ArchiveWindow(self)
        return self.library_window

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
            shell.rowconfigure(2, weight=3)
            shell.rowconfigure(4, weight=1)
            ttk.Label(shell, text=self.text("history"), style="Title.TLabel").grid(row=0, column=0, sticky="w")
            search = ttk.Entry(shell, textvariable=self.history_search_var)
            search.grid(row=1, column=0, sticky="ew", pady=(16, 12))
            Tooltip(search, lambda: self.text("tip_search_history"))
            tree = ttk.Treeview(shell, columns=("time", "source", "status", "details"), show="headings")
            for column in ("time", "source", "status", "details"):
                tree.heading(column, text=self.text(f"history_{column}"))
                tree.column(column, width=150 if column != "source" else 330, anchor="w", stretch=True)
            tree.grid(row=2, column=0, sticky="nsew")
            self.history_detail_tree = tree
            self.history_events_tree = ttk.Treeview(shell, columns=("ts", "message"), show="headings", height=5)
            self.history_events_tree.heading("ts", text=self.text("history_time"))
            self.history_events_tree.heading("message", text=self.text("history_events"))
            self.history_events_tree.column("ts", width=150, anchor="w", stretch=False)
            self.history_events_tree.column("message", width=480, anchor="w", stretch=True)
            ttk.Label(shell, text=self.text("history_events"), style="Subtitle.TLabel").grid(row=3, column=0, sticky="w", pady=(10, 4))
            self.history_events_tree.grid(row=4, column=0, sticky="nsew")
            tree.bind("<<TreeviewSelect>>", self.on_history_select)
            self.refresh_history()
            self.on_history_select()
        else:
            window.title(self.text("settings_title"))
            self.sync_settings_form()
            shell = ttk.Frame(window, style="App.TFrame", padding=28)
            shell.pack(fill="both", expand=True)
            ttk.Label(shell, text=self.text("settings_title"), style="Title.TLabel").pack(anchor="w")
            ttk.Label(shell, text=self.text("settings_note"), style="Subtitle.TLabel", wraplength=540).pack(anchor="w", pady=(6, 14))

            def section_label(key):
                ttk.Label(shell, text=self.text(key), style="CardTitle.TLabel").pack(anchor="w", pady=(10, 4))

            # --- Download ---
            section_label("settings_section_download")
            row = ttk.Frame(shell, style="App.TFrame"); row.pack(fill="x")
            self.register_text("settings_timeout", ttk.Label(row, text="", style="CardText.TLabel")).pack(side="left")
            self.settings_timeout_spin = ttk.Spinbox(row, from_=5, to=120, width=6, textvariable=self.settings_timeout_var)
            self.settings_timeout_spin.pack(side="left", padx=(10, 26))
            Tooltip(self.settings_timeout_spin, lambda: self.text("tip_settings_timeout"))
            self.register_text("settings_retries", ttk.Label(row, text="", style="CardText.TLabel")).pack(side="left")
            self.settings_retries_spin = ttk.Spinbox(row, from_=1, to=10, width=4, textvariable=self.settings_retries_var)
            self.settings_retries_spin.pack(side="left", padx=(10, 0))
            Tooltip(self.settings_retries_spin, lambda: self.text("tip_settings_retries"))
            self.register_text("settings_naming", ttk.Label(shell, text="", style="CardText.TLabel")).pack(anchor="w", pady=(8, 0))
            self.settings_naming_combo = ttk.Combobox(shell, state="readonly", width=32, textvariable=self.settings_naming_var,
                                                      values=(self.text("naming_none"), self.text("naming_site"), self.text("naming_slug"), self.text("naming_full")))
            self.settings_naming_combo.pack(anchor="w", pady=(4, 0))

            # --- Notifications ---
            section_label("settings_section_notify")
            self.register_text("settings_sound", ttk.Checkbutton(shell, text="", variable=self.settings_sound_var)).pack(anchor="w")
            self.register_text("settings_notify", ttk.Checkbutton(shell, text="", variable=self.settings_notify_var)).pack(anchor="w", pady=(4, 0))

            # --- Window ---
            section_label("settings_section_window")
            self.register_text("settings_tray", ttk.Checkbutton(shell, text="", variable=self.settings_tray_var)).pack(anchor="w")

            # --- Appearance ---
            section_label("settings_section_appearance")
            row2 = ttk.Frame(shell, style="App.TFrame"); row2.pack(fill="x")
            self.register_text("settings_language", ttk.Label(row2, text="", style="CardText.TLabel")).pack(side="left")
            self.settings_lang_combo = ttk.Combobox(row2, state="readonly", width=12, values=("English", "Tiếng Việt"),
                                                    textvariable=self.settings_lang_var)
            self.settings_lang_combo.pack(side="left", padx=(10, 26))
            self.register_text("settings_theme", ttk.Label(row2, text="", style="CardText.TLabel")).pack(side="left")
            self.settings_theme_combo = ttk.Combobox(row2, state="readonly", width=12, textvariable=self.settings_theme_var,
                                                     values=(self.text("theme_dark"), self.text("theme_light"), self.text("theme_system")))
            self.settings_theme_combo.pack(side="left", padx=(10, 26))
            self.register_text("settings_density", ttk.Label(row2, text="", style="CardText.TLabel")).pack(side="left")
            self.settings_density_combo = ttk.Combobox(row2, state="readonly", width=13, textvariable=self.settings_density_var,
                                                       values=(self.text("density_comfortable"), self.text("density_compact")))
            self.settings_density_combo.pack(side="left", padx=(10, 0))

            ttk.Label(shell, text=self.text("settings_output"), style="CardText.TLabel").pack(anchor="w", pady=(12, 0))
            ttk.Label(shell, textvariable=self.output_var, style="Subtitle.TLabel").pack(anchor="w", pady=(4, 0))

            actions = ttk.Frame(shell, style="App.TFrame")
            actions.pack(anchor="w", pady=(18, 0))
            self.register_text("settings_save", ttk.Button(actions, text="", style="Accent.TButton", command=self.save_settings)).pack(side="left")
            self.register_text("settings_reset", ttk.Button(actions, text="", command=self.reset_settings)).pack(side="left", padx=(10, 0))
            self.settings_status_label = ttk.Label(shell, text="", style="Muted.TLabel")
            self.settings_status_label.pack(anchor="w", pady=(10, 0))

    def choose_output(self):
        selected = filedialog.askdirectory(title=self.text("choose_folder"))
        if selected:
            self.output_var.set(selected)

    def write_log(self, message: str):
        # Track editable state in a Python flag instead of a cget() round-trip:
        # steady state costs 3 Tk calls per line instead of 4-5.
        if not self._log_editable:
            self.log.configure(state="normal")
            self._log_editable = True
        self.log.insert("end", message.rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self._log_editable = False

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log_editable = False

    def open_output_folder(self):
        folder = Path(self.output_var.get()).expanduser()
        if not folder.is_dir():
            if not messagebox.askyesno(self.text("missing_folder"), self.text("open_folder_missing_confirm")):
                return
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                messagebox.showerror(self.text("generic_error"), str(exc))
                return
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606 - intended Explorer launch
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except OSError as exc:
            messagebox.showerror(self.text("generic_error"), str(exc))

    def toggle_log(self):
        self.log_collapsed = not self.log_collapsed
        if self.log_collapsed:
            self.log.grid_remove()
            self.main_area.rowconfigure(8, weight=0)
            new_height = max(self.root.winfo_height() - 180, self.root.minsize()[1])
            self.root.geometry(f"{self.root.winfo_width()}x{new_height}")
        else:
            self.log.grid()
            self.main_area.rowconfigure(8, weight=1)
            new_height = min(self.root.winfo_height() + 180, 900)
            self.root.geometry(f"{self.root.winfo_width()}x{new_height}")
        self.activity_toggle_button.configure(
            text=self.text("activity_log_show" if self.log_collapsed else "activity_log_hide")
        )

    # ---------- settings persistence (Phase 7) ----------

    NAMING_KEYS = ("", "site", "slug", "full")

    def _sync_settings_choices(self):
        """Fill combobox values from UI_TEXT; called from change_language()."""
        combo = getattr(self, "settings_naming_combo", None)
        if combo is None or not combo.winfo_exists():
            return
        naming_index = self.NAMING_KEYS.index(self.settings_naming_var.get()) if self.settings_naming_var.get() in self.NAMING_KEYS else 0
        combo.configure(values=tuple(self.text("naming_none") if key == "" else self.text(f"naming_{key}") for key in self.NAMING_KEYS))
        combo.current(naming_index)
        theme = self.settings_theme_var.get()
        if theme not in ("dark", "light", "system"):
            theme = self.settings.get("theme")
        self.settings_theme_combo.configure(values=(self.text("theme_dark"), self.text("theme_light"), self.text("theme_system")))
        self.settings_theme_combo.current(("dark", "light", "system").index(theme))
        density = self.settings_density_var.get()
        if density not in ("comfortable", "compact"):
            density = self.settings.get("density")
        self.settings_density_combo.configure(values=(self.text("density_comfortable"), self.text("density_compact")))
        self.settings_density_combo.current(("comfortable", "compact").index(density))

    def sync_settings_form(self):
        """Push current settings into the form widgets."""
        self.settings_timeout_var.set(int(self.settings.get("timeout")))
        self.settings_retries_var.set(int(self.settings.get("retries")))
        naming = self.settings.get("naming")
        self.settings_naming_var.set(naming if naming in self.NAMING_KEYS else "")
        self.settings_sound_var.set(bool(self.settings.get("sound")))
        self.settings_notify_var.set(bool(self.settings.get("notify")))
        self.settings_tray_var.set(bool(self.settings.get("close_to_tray")))
        self.settings_lang_var.set("Tiếng Việt" if self.settings.get("language") == "vi" else "English")
        self.settings_theme_var.set(self.settings.get("theme"))
        self.settings_density_var.set(self.settings.get("density"))

    def save_settings(self):
        try:
            timeout = int(self.settings_timeout_var.get())
            retries = int(self.settings_retries_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror(self.text("settings_title"), self.text("settings_invalid_number"))
            return
        if not (5 <= timeout <= 120 and 1 <= retries <= 10):
            messagebox.showerror(self.text("settings_title"), self.text("settings_invalid_number"))
            return
        previous_theme = self.settings.get("theme")
        previous_density = self.settings.get("density")
        naming_index = max(self.settings_naming_combo.current(), 0)
        self.settings.set("timeout", timeout)
        self.settings.set("retries", retries)
        self.settings.set("naming", self.NAMING_KEYS[naming_index])
        self.settings.set("sound", bool(self.settings_sound_var.get()))
        self.settings.set("notify", bool(self.settings_notify_var.get()))
        self.settings.set("close_to_tray", bool(self.settings_tray_var.get()))
        self.settings.set("language", "vi" if self.settings_lang_var.get() == "Tiếng Việt" else "en")
        theme_index = max(self.settings_theme_combo.current(), 0)
        self.settings.set("theme", ("dark", "light", "system")[theme_index])
        density_index = max(self.settings_density_combo.current(), 0)
        self.settings.set("density", ("comfortable", "compact")[density_index])
        self.settings.save()
        # Apply immediately.
        QueueTask.MAX_ATTEMPTS = max(1, retries)
        appearance_changed = (self.settings.get("theme") != previous_theme
                              or self.settings.get("density") != previous_density)
        self.language_combo.set(self.settings_lang_var.get())
        if appearance_changed:
            # Rebuild destroys auxiliary windows, so localize first.
            self.change_language()
            self.apply_appearance()
        else:
            self.change_language()
        self.write_log(self.text("settings_saved"))

    def apply_appearance(self):
        """Re-apply theme/density by rebuilding the main UI in place."""
        # The old widgets are destroyed below; drop the text registry first so
        # change_language() inside build_ui() never touches a dead widget.
        self.text_widgets.clear()
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel):
                child.destroy()
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_theme()
        self.build_ui()

    def reset_settings(self):
        self.settings.reset()
        self.sync_settings_form()
        QueueTask.MAX_ATTEMPTS = max(1, int(self.settings.get("retries")))
        self.language_combo.set("Tiếng Việt" if self.settings.get("language") == "vi" else "English")
        self.change_language()
        status = getattr(self, "settings_status_label", None)
        if status is not None and status.winfo_exists():
            status.configure(text=self.text("settings_saved"))
        self.write_log(self.text("settings_saved"))

    # ---------- Windows toast notifications (Phase 8) ----------

    TOAST_COLORS = {
        "success": "#49d69c",
        "error": "#f87171",
        "info": "#7c5cff",
        "warning": "#fbbf24",
    }

    def toasts_enabled(self) -> bool:
        """Toasts show only when the notifications preference is on."""
        return bool(self.settings.get("notify"))

    def show_toast(self, title: str, message: str, kind: str = "info", on_click=None):
        """Show a non-modal slide-in toast; safe while the window is hidden.

        A click on the toast restores the main window (unless ``on_click``
        overrides the action). Toasts self-dismiss after 6 seconds.
        """
        if not self.toasts_enabled() or self.closing:
            return None
        try:
            toast = tk.Toplevel(self.root)
        except tk.TclError:
            return None
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=self.colors["card"], highlightthickness=1,
                        highlightbackground=self.colors["border"], highlightcolor=self.colors["border"])
        accent = self.TOAST_COLORS.get(kind, self.colors["accent"])
        body = tk.Frame(toast, bg=self.colors["card"], padx=14, pady=10)
        body.pack(fill="both", expand=True)
        tk.Frame(body, bg=accent, width=4).pack(side="left", fill="y", padx=(0, 10))
        text_box = tk.Frame(body, bg=self.colors["card"])
        text_box.pack(side="left", fill="both", expand=True)
        tk.Label(text_box, text=title, bg=self.colors["card"], fg=self.colors["text"],
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(anchor="w")
        tk.Label(text_box, text=message, bg=self.colors["card"], fg=self.colors["muted"],
                 font=("Segoe UI", 9), anchor="w", wraplength=280, justify="left").pack(anchor="w")

        def clicked(_event=None):
            if toast.winfo_exists():
                toast.destroy()
            self.toasts = [t for t in self.toasts if t.winfo_exists()]
            if on_click is not None:
                on_click()
            else:
                self._show_window()

        for widget in (toast, body, text_box):
            widget.bind("<Button-1>", clicked)
        toast.protocol("WM_DELETE_WINDOW", lambda: None)
        toast.update_idletasks()
        width = max(toast.winfo_reqwidth(), 320)
        height = toast.winfo_reqheight()
        screen_w = toast.winfo_screenwidth()
        screen_h = toast.winfo_screenheight()
        # Stack above any toast already on screen (newest on top).
        offset = sum(t.winfo_height() + 8 for t in self.toasts if t.winfo_exists())
        x = screen_w - width - 20
        y = max(screen_h - height - 48 - offset, 0)
        toast.geometry(f"{width}x{height}+{x}+{y}")

        def dismiss():
            if toast.winfo_exists():
                toast.destroy()
            self.toasts = [t for t in self.toasts if t.winfo_exists()]

        self.root.after(6000, dismiss)
        self.toasts.append(toast)
        return toast

    def close_all_toasts(self):
        for toast in list(self.toasts):
            try:
                if toast.winfo_exists():
                    toast.destroy()
            except tk.TclError:
                pass
        self.toasts = []

    def play_completion_sound(self):
        """Play a short completion sound without blocking the GUI thread."""
        if not self.settings.get("sound"):
            return
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
        language = self.current_language

        self.stop_event.clear()
        self.reset_transfer_stats()
        self.set_state("state_preparing")
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
            kwargs={"timeout": self.settings.get("timeout"), "naming": self.settings.get("naming")},
            daemon=True,
        )
        self.worker.start()

    def stop(self):
        if self.worker and self.worker.is_alive():
            self.stop_event.set()
            self.set_state("stopping")
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
        *,
        task: QueueTask | None = None,
        emit_terminal: bool = True,
        pause_event: Event | None = None,
        timeout: float = 30,
        naming: str = "",
    ):
        session = downloader.make_session()
        output_root.mkdir(parents=True, exist_ok=True)
        chapters_done = 0
        visited: set[str] = set()
        page_state = {"chapter": "", "current": 0, "total": 0}
        # Phase 10.5: attempt-scoped transfer totals (worker thread only).
        self._task_pages_total = 0
        self._task_bytes_delta = 0
        self._task_paused_seconds = 0.0

        def report_pages(chapter, current, total):
            page_state.update(chapter=chapter, current=current, total=total)
            self._task_pages_total = max(self._task_pages_total, current)
            self.emit("page_progress", (chapter, current, total))

        def report_bytes(received, total_bytes, kbps):
            self._task_bytes_delta = received
            self.emit("bytes_progress", (received, kbps, page_state["current"], page_state["total"], page_state["chapter"]))

        def report(message: str):
            if task is not None:
                task.log_lines.append(message)
                self.emit("task_log", task)
            self.emit("log", message)

        try:
            while url and url not in visited and (selected_count == 0 or chapters_done < selected_count):
                if self.stop_event.is_set():
                    raise downloader.DownloadCancelled(self.text("stopped", language))
                visited.add(url)
                report(self.text("downloading_chapter", language, number=chapters_done + 1, url=url))
                title, image_count, chapter_bytes, paused_seconds = downloader.download_chapter(
                    session,
                    url,
                    output_root,
                    delay,
                    timeout,
                    overwrite,
                    self.stop_event,
                    report_pages,
                    report_bytes,
                    pause_event,
                    naming,
                )
                self._task_bytes_delta += chapter_bytes
                chapter_dir = output_root / title
                self._task_paused_seconds += paused_seconds
                if convert_webp or create_cbz_option:
                    self.emit("state", ("state_converting", {}))
                    converted = convert_webp_to_jpg(chapter_dir)
                    if converted:
                        report(self.text("converted", language, count=converted))
                if create_cbz_option:
                    self.emit("state", ("state_creating_cbz", {}))
                    cbz = create_cbz(chapter_dir)
                    report(self.text("created_cbz", language, path=cbz))
                chapters_done += 1
                if task is None:
                    self.emit("overall_progress", (chapters_done, selected_count))
                report(self.text("completed_chapter", language, title=title, count=image_count))
                self.emit("bytes_progress", (0, 0.0, 0, 0, title))

                if selected_count and chapters_done >= selected_count:
                    break
                if self.stop_event.wait(max(delay, 1.0)):
                    raise downloader.DownloadCancelled(self.text("stopped", language))
                page = session.get(url, timeout=30)
                page.raise_for_status()
                url = downloader.next_chapter(page.text, page.url)
                if not url:
                    report(self.text("no_next", language))
            if emit_terminal:
                self.emit("done", self.text("completed_all", language, count=chapters_done))
            if task is not None:
                self.emit("task_transfer", (task.id, {"pages": self._task_pages_total,
                                                     "bytes": self._task_bytes_delta,
                                                     "paused": self._task_paused_seconds}))
            return chapters_done
        except downloader.DownloadCancelled as exc:
            message = str(exc)
            if task is not None:
                task.log_lines.append(message)
                self.emit("task_log", task)
            if emit_terminal:
                self.emit("stopped", message)
            else:
                self.emit("task_transfer", (task.id, {"pages": self._task_pages_total,
                                                     "bytes": self._task_bytes_delta,
                                                     "paused": self._task_paused_seconds}))
                raise
        except requests.RequestException as exc:
            message = f"{self.text('network_error', language)}: {exc}"
            if task is not None:
                task.log_lines.append(message)
                self.emit("task_log", task)
            if emit_terminal:
                self.emit("error", message)
            else:
                self.emit("task_transfer", (task.id, {"pages": self._task_pages_total,
                                                     "bytes": self._task_bytes_delta,
                                                     "paused": self._task_paused_seconds}))
                raise
        except Exception as exc:  # Keep worker errors visible in the GUI.
            message = f"{self.text('generic_error', language)}: {exc}"
            if task is not None:
                task.log_lines.append(message)
                self.emit("task_log", task)
            if emit_terminal:
                self.emit("error", message)
            else:
                self.emit("task_transfer", (task.id, {"pages": self._task_pages_total,
                                                     "bytes": self._task_bytes_delta,
                                                     "paused": self._task_paused_seconds}))
                raise
        return chapters_done

    def process_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.write_log(str(value))
                elif kind == "state":
                    state_key, state_values = value
                    self.set_state(state_key, **state_values)
                elif kind == "page_progress":
                    chapter, current, total = value
                    if current == 0:
                        self.page_progress.configure(maximum=total, value=0)
                    else:
                        self.page_progress.configure(maximum=total, value=current)
                    self.eta_pages_done = current
                    self.eta_pages_total = total
                    self.page_progress_text.set(self.text("page_progress", chapter=chapter, current=current, total=total))
                elif kind == "active_task":
                    self.active_task = value
                    self.reset_transfer_stats()
                    value.total_bytes = 0
                    value.bank_bytes = 0
                    self.update_queue_progress()
                    self.refresh_task_log()
                elif kind == "bytes_progress":
                    received, kbps, page_current, page_total, chapter = value
                    self.note_transfer_bytes(received)
                    speed, eta = self.transfer_summary(kbps)
                    if page_total:
                        self.page_progress_text.set(self.text(
                            "page_progress", chapter=chapter, current=page_current, total=page_total))
                    self.set_state("status_downloading_speed", chapter=chapter, speed=speed,
                                   bytes=self.format_bytes(self.transfer_bytes), eta=eta)
                    active = self.active_task
                    if active is not None:
                        active.last_bytes = received
                        active.total_bytes = self.transfer_bytes
                        self.update_queue_progress()
                    if active is not None and hasattr(self, "queue_tree"):
                        active.progress = self.text(
                            "task_progress_bytes",
                            chapters=getattr(active, "last_chapters", 0),
                            bytes=self.format_bytes(self.transfer_bytes),
                            speed=speed,
                        )
                        try:
                            self.queue_tree.item(active.id, values=(
                                self.queue_state_text(active),
                                active.url,
                                active.progress,
                                active.output_root,
                            ))
                        except tk.TclError:
                            pass
                elif kind == "overall_progress":
                    current, total = value
                    if total:
                        self.overall_progress.configure(mode="determinate", maximum=total, value=current)
                        self.overall_progress_text.set(self.text("overall_progress", current=current, total=total))
                    else:
                        self.overall_progress_text.set(self.text("overall_all_progress", current=current))
                elif kind == "task_log":
                    # Coalesce: mark dirty, render once in finally after the
                    # whole queue drains (one render per pump tick instead of
                    # one per emitted line).
                    if value is self.active_task:
                        self._task_log_dirty = True
                elif kind == "queue_state":
                    task, details = value
                    if task.state in {"completed", "failed", "stopped"}:
                        task.bank_bytes = int(getattr(task, "total_bytes", 0) or 0)
                    self.save_queue()
                    self.refresh_queue_tree()
                    self.write_log(self.text("task_state_changed", state=self.queue_state_text(task), url=task.url, details=details))
                    if task.state == "active":
                        self.set_state("state_active")
                elif kind == "task_transfer":
                    task_id, snapshot = value
                    self._last_transfer_snapshot = (task_id, snapshot)
                elif kind == "queue_task_finished":
                    task, ok = value
                    try:
                        self.update_history_for_task(task)
                        self.record_transfer_event(task)
                    except Exception as exc:  # one bad event must not kill the pump
                        self.write_log(f"history event error: {exc}")
                elif kind == "queue_done":
                    self.queue_running = False
                    self.queue_paused = False
                    self.queue_pause_event.clear()
                    finished = [task for task in self.queue_tasks if task.state == "completed"]
                    failed = [task for task in self.queue_tasks if task.state in {"failed", "stopped"}]
                    self.active_task = None
                    self.overall_progress.stop()
                    self.set_state("queue_done")
                    self.write_log(self.text("queue_done"))
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.queue_start_button.configure(state="normal")
                    self.queue_stop_button.configure(state="disabled")
                    self.queue_pause_button.configure(state="disabled")
                    self.queue_resume_button.configure(state="disabled")
                    self.refresh_task_log()
                    self.play_completion_sound()
                    self.show_toast(
                        self.text("toast_queue_done"),
                        self.text("toast_queue_summary", done=len(finished), failed=len(failed)),
                        "success" if not failed else "warning",
                    )
                elif kind == "queue_paused":
                    self.queue_running = False
                    self.queue_paused = False
                    self.queue_pause_event.clear()
                    self.active_task = None
                    self.overall_progress.stop()
                    self.set_state("queue_paused")
                    self.write_log(self.text("queue_paused"))
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.queue_start_button.configure(state="normal")
                    self.queue_stop_button.configure(state="disabled")
                    self.queue_pause_button.configure(state="disabled")
                    self.queue_resume_button.configure(state="disabled")
                    self.refresh_task_log()
                    self.show_toast(
                        self.text("toast_queue_paused"),
                        self.text("toast_queue_paused_body"),
                        "info",
                    )
                elif kind == "done":
                    self.write_log(str(value))
                    self.update_history(self.text("status_complete"), str(value))
                    self.overall_progress.stop()
                    self.set_state("status_complete")
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.play_completion_sound()
                    self.show_toast(self.text("toast_download_complete"), str(value), "success")
                elif kind == "stopped":
                    self.write_log(str(value))
                    self.update_history(self.text("status_stopped"), str(value))
                    self.overall_progress.stop()
                    self.set_state("status_stopped")
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.show_toast(self.text("toast_download_stopped"), self.text("toast_download_stopped_body"), "info")
                elif kind == "crash_report":
                    # Phase 10.2: surface a fatal error without blocking.
                    error_text, crash_file = value
                    self.write_log(f"[crash] {error_text} -> {crash_file}")
                    self.show_toast(
                        self.text("toast_crash_title"),
                        self.text("toast_crash_body", error=error_text),
                        "error",
                    )
                elif kind == "error":
                    self.write_log(str(value))
                    self.update_history(self.text("status_error"), str(value))
                    self.overall_progress.stop()
                    self.set_state("status_error")
                    self.start_button.configure(state="normal")
                    self.stop_button.configure(state="disabled")
                    self.show_toast(self.text("toast_download_failed"), str(value), "error")
        except queue.Empty:
            pass
        finally:
            # One task-log render per tick, after all pending events drained.
            if self._task_log_dirty and not self.closing:
                self._task_log_dirty = False
                self.refresh_task_log()
            # Always reschedule: one failing handler must not kill the pump.
            if not self.closing:
                self._events_after_id = self.root.after(100, self.process_events)


APP_VERSION = "1.0.0"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--version" in argv:
        print(f"MangaDownloader {APP_VERSION}")
        return 0
    # Phase 10.8: `--url <chapter-url>` bridges a CLI call into the GUI.
    url = ""
    if "--url" in argv:
        idx = argv.index("--url")
        if idx + 1 < len(argv):
            url = argv[idx + 1].strip()
    # Phase 10.1: one app at a time over the shared data files.
    guard = SingleInstanceGuard()
    if not guard.is_owner:
        guard.request_show(url)
        return 0

    root = tk.Tk()
    app = MangaGui(root)
    app.guard = guard
    try:
        root.mainloop()
    finally:
        guard.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
