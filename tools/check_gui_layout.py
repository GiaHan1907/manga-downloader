"""Windows GUI smoke test for Manga Downloader.

Run from the repository root on Windows:
    py tools/check_gui_layout.py --output .relcheck/gui-layout

The script opens every workspace view, records widget geometry, captures a
screen image when Pillow ImageGrab is available, and exits with code 1 when
any required view or control is missing. It never starts the system tray and
uses an isolated temporary data directory.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

# When executed as ``py tools\check_gui_layout.py``, Python puts only the
# tools directory on sys.path. Add the repository root so manga_gui.py and its
# sibling modules can be imported reliably from any working directory.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=".relcheck/gui-layout", help="report and screenshot directory")
    parser.add_argument("--wait", type=float, default=0.35, help="seconds to wait after each view")
    parser.add_argument("--keep-open", action="store_true", help="leave the final window open")
    args = parser.parse_args()

    # Import tkinter only on the target machine; this is intentionally a
    # Windows-side smoke test, not a headless CI test.
    import tkinter as tk
    import manga_gui

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    data_dir = Path(tempfile.mkdtemp(prefix="manga-gui-layout-"))
    manga_gui.MangaGui.get_history_file = classmethod(lambda cls: data_dir / "history.db")
    manga_gui.MangaGui.get_queue_file = classmethod(lambda cls: data_dir / "queue.json")
    manga_gui.MangaGui.get_settings_file = classmethod(lambda cls: data_dir / "settings.json")
    manga_gui.MangaGui.start_tray = lambda self: None

    root = tk.Tk()
    root.withdraw()
    app = manga_gui.MangaGui(root)
    root.update_idletasks()
    root.deiconify()
    root.update()

    required = {
        "downloader": ("queue_tree", "queue_progress", "queue_add"),
        "history": ("history_tree", "history_filter_combo", "history_search_entry"),
        "library": ("library_window",),
        "settings": ("settings_theme_combo", "settings_lang_combo", "settings_save", "settings_reset"),
    }
    report = {"window": {}, "views": {}, "screenshots": [], "errors": []}
    report["window"] = {"width": root.winfo_width(), "height": root.winfo_height(), "screen": (root.winfo_screenwidth(), root.winfo_screenheight())}

    try:
        from PIL import ImageGrab
    except Exception:
        ImageGrab = None

    for view, names in required.items():
        app.show_view(view)
        root.update_idletasks()
        root.update()
        time.sleep(max(args.wait, 0))
        missing = []
        geometries = {}
        for name in names:
            widget = getattr(app, name, None)
            if widget is None:
                missing.append(name)
                continue
            try:
                geometries[name] = {"x": widget.winfo_x(), "y": widget.winfo_y(), "width": widget.winfo_width(), "height": widget.winfo_height()}
            except Exception as exc:
                missing.append(f"{name}: {exc}")
        report["views"][view] = {"missing": missing, "geometry": geometries}
        if missing:
            report["errors"].append(f"{view}: missing {', '.join(missing)}")
        if ImageGrab is not None:
            try:
                shot = ImageGrab.grab(all_screens=True)
                path = output / f"{view}.png"
                shot.save(path)
                report["screenshots"].append(str(path))
            except Exception as exc:
                report["errors"].append(f"{view}: screenshot failed: {exc}")

    report_path = output / "layout-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Report: {report_path}")
    if not args.keep_open:
        app.closing = True
        root.destroy()
    else:
        root.mainloop()
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
