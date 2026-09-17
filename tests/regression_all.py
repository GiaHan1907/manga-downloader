"""Composite regression suite: phases 0-9 in a single run.

Everything runs against temp AppData (no real user data touched) and a fake
downloader (no network). GUI checks go through the real tkinter event pump.

Run from the repo root (also used by .github/workflows/regression.yml):
    python -u tests/regression_all.py

Exit code 0 = all green. The frozen-exe checks (phase 9) SKIP automatically
when dist/MangaDownloader.exe has not been built in the environment.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import types
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

BASE = Path(tempfile.mkdtemp(prefix="md-regression-"))

import manga_gui
import download_manga as downloader

# ---- Deterministic environment -------------------------------------------
# All persistence goes to the temp dir; the tray is never started (CI has no
# tray session and secondary instances must not spawn extra icons).
manga_gui.MangaGui.get_history_file = classmethod(lambda cls: BASE / "history.db")
manga_gui.MangaGui.get_queue_file = classmethod(lambda cls: BASE / "queue.json")
manga_gui.MangaGui.get_settings_file = classmethod(lambda cls: BASE / "settings.json")
manga_gui.MangaGui.start_tray = lambda self: None

RESULT_PASS: list[str] = []
RESULT_FAIL: list[str] = []


def check(name: str, condition, detail: str = ""):
    if condition:
        RESULT_PASS.append(name)
        print(f"  PASS  {name}", flush=True)
    else:
        RESULT_FAIL.append(f"{name} {detail}".strip())
        print(f"  FAIL  {name}  {detail}", flush=True)


def pump(root, seconds: float):
    deadline = time.time() + seconds
    while time.time() < deadline:
        root.update()
        time.sleep(0.02)


def pump_until(root, predicate, timeout: float = 6.0, label: str = "") -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        root.update()
        if predicate():
            return True
        time.sleep(0.02)
    print(f"  (timeout waiting for {label})", flush=True)
    return False


def section(title: str):
    print(f"\n=== {title} ===", flush=True)


def make_image_bytes() -> bytes:
    return bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909"
        "080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30"
        "313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501"
        "010101010100000000000000000102030405060708090a0bffc400b5100002010303020403"
        "050504040000017d01020300041105122131410613516107227114328191a1082342b1c115"
        "52d1f02433627282090a161718191a25262728292a3435363738393a434445464748494a53"
        "5455565758595a636465666768696a737475767778797a838485868788898a929394959697"
        "98999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8"
        "d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008010100003f00fcaaf9ffd9")


# ===========================================================================
# PHASE 0 — packaging sanity: CLI contract of download_manga
# ===========================================================================
section("Phase 0: packaging / CLI contract")

check("version constant", manga_gui.APP_VERSION == "1.0.0", manga_gui.APP_VERSION)
buf = io.StringIO()
with redirect_stdout(buf):
    code = manga_gui.main(["--version"])
check("--version exit code", code == 0, str(code))
check("--version output", buf.getvalue().strip() == "MangaDownloader 1.0.0", buf.getvalue().strip())
check("parse_args defaults", downloader.parse_args().timeout == 30)
check("clean_name fallback", downloader.clean_name("///", "fallback") == "fallback")

# ===========================================================================
# PHASE 1 — tray-safe language resolution + history primitives
# ===========================================================================
section("Phase 1: tray-safe language + history primitives")

check("UI_TEXT EN/VI symmetric", set(manga_gui.UI_TEXT["en"]) == set(manga_gui.UI_TEXT["vi"]),
      f"EN {len(manga_gui.UI_TEXT['en'])} vs VI {len(manga_gui.UI_TEXT['vi'])}")

root = tk.Tk()
root.withdraw()
app = manga_gui.MangaGui(root)
pump(root, 0.3)

# Block every modal dialog for the WHOLE run: no suite hang, and every
# unexpected dialog is recorded as evidence instead.
modal_calls: list[str] = []
manga_gui.messagebox.showinfo = lambda *a, **k: modal_calls.append("info")
manga_gui.messagebox.showerror = lambda *a, **k: modal_calls.append("error")
manga_gui.messagebox.showwarning = lambda *a, **k: modal_calls.append("warning")
manga_gui.messagebox.askyesno = lambda *a, **k: True
manga_gui.simpledialog.askstring = lambda *a, **k: None

# change_language() resolves through the header combo and mirrors the choice
# into the plain attribute tray threads read (the Phase 1 fix under test).
app.language_combo.set("Tiếng Việt")
app.change_language()
pump(root, 0.2)
check("current_language mirrors combo", app.current_language == "vi", app.current_language)
check("text() honors language arg", app.text("ready", "en") != app.text("ready", "vi"))
check("natural_key ordering",
      manga_gui.natural_key(Path("t-2")) < manga_gui.natural_key(Path("t-10")))

# Back to English for the rest of the run.
app.language_combo.set("English")
app.change_language()
pump(root, 0.2)

# ===========================================================================
# PHASE 2 — persistent queue + worker through the real event pump
# ===========================================================================
section("Phase 2: persistent queue + worker")

calls = {"chapters": 0}


def fake_chapter(session, url, output_root, delay, timeout, overwrite,
                 cancel_event=None, progress_callback=None, bytes_callback=None,
                 pause_event=None, naming=""):
    calls["chapters"] += 1
    title = f"Chapter {calls['chapters']:02d}"
    (Path(output_root) / title).mkdir(parents=True, exist_ok=True)
    if progress_callback:
        progress_callback(title, 1, 2)
        progress_callback(title, 2, 2)
    if bytes_callback:
        bytes_callback(1_234_567, 2_500_000, 640.0)
    return title, 2, 1_234_567, 0.0


downloader.download_chapter = fake_chapter
downloader.make_session = lambda: types.SimpleNamespace(get=lambda *a, **k: None)

task1 = manga_gui.QueueTask("http://fake/manga/x/ch-1", str(BASE / "lib"), 1, 0.0,
                            False, False, False)
task2 = manga_gui.QueueTask("http://fake/manga/y/ch-1", str(BASE / "lib"), 1, 0.0,
                            False, False, False)
check("task ids unique under tight creation",
      len({manga_gui.QueueTask("http://u", str(BASE), 1, 0.0, False, False, False).id
           for _ in range(50)}) == 50)
app.queue_tasks = [task1, task2]
app.save_queue()
check("queue persisted", (BASE / "queue.json").exists())

pump(root, 0.5)          # flush stray events so the queue busy guard is clear
app.start_queue()
ok = pump_until(root, lambda: app.queue_tasks[0].state == "completed" and app.queue_tasks[1].state == "completed",
                label="queue completion")
check("both tasks completed", ok, str([(t.id, t.state) for t in app.queue_tasks]))
check("queue stopped running", not app.queue_running)
pump(root, 0.4)
check("task chapters recorded", task1.last_chapters == 1, str(task1.last_chapters))
check("task progress text", "chapter(s)" in task1.progress, task1.progress)
check("history written for tasks", app.history.count() >= 2, str(app.history.count()))

# Reload from disk in a fresh app (persistence across restart).
app2 = manga_gui.MangaGui(root)
check("queue reloads from disk", len(app2.queue_tasks) == 2, str(len(app2.queue_tasks)))
check("reloaded tasks completed", all(t.state == "completed" for t in app2.queue_tasks),
      str([t.state for t in app2.queue_tasks]))
app2.closing = True   # stop this secondary instance's event pump

# ===========================================================================
# PHASE 3 — pause/resume, bounded retry, queue continues past dead tasks
# ===========================================================================
section("Phase 3: pause/resume + bounded retry")

check("backoff schedule", [manga_gui.MangaGui.retry_backoff_seconds(i) for i in (1, 2, 3, 5)] == [2, 4, 8, 30])

# Page-level pause: the fake simulates an in-flight page request. It sleeps a
# moment (so the task is still running), then honors the pause gate the way
# download_chapter does between page fetches.
pause_gate_hit = threading.Event()


def pausable_chapter(session, url, output_root, delay, timeout, overwrite,
                     cancel_event=None, progress_callback=None, bytes_callback=None,
                     pause_event=None, naming=""):
    time.sleep(0.4)   # simulate an in-flight page so pause can engage mid-run
    if pause_event is not None and pause_event.is_set():
        pause_gate_hit.set()
        while pause_event.is_set() and not (cancel_event and cancel_event.is_set()):
            time.sleep(0.02)
    (Path(output_root) / "Paused Chapter").mkdir(parents=True, exist_ok=True)
    return "Paused Chapter", 3, 999, 0.0


downloader.download_chapter = pausable_chapter

tp = manga_gui.QueueTask("http://fake/pause/ch-1", str(BASE / "lib2"), 1, 0.0, False, False, False)
app.queue_tasks = [tp]
app.save_queue()
pump(root, 0.5)          # flush previous queue_done so the busy guard is clear
app.start_queue()
pump(root, 0.2)          # worker is now inside the in-flight page
app.pause_queue()        # engage the page-level gate while the task runs
ok = pump_until(root, lambda: pause_gate_hit.is_set(), timeout=4, label="worker entering pause gate")
check("worker honors pause_event", ok)
check("queue shows paused", app.queue_paused)
app.resume_queue()       # clears the gate -> download proceeds
ok = pump_until(root, lambda: tp.state == "completed", timeout=4, label="resume completes task")
check("resume completes paused task", ok, tp.state)
check("pause flag cleared", not app.queue_paused)

# Task-boundary pause: engage pause while the first task is held mid-download,
# BEFORE it may finish -> the next task must park at the boundary. Fully
# deterministic (no instant-task race).
park_started = threading.Event()
park_release = threading.Event()


def parkable_chapter(session, url, output_root, delay, timeout, overwrite,
                     cancel_event=None, progress_callback=None, bytes_callback=None,
                     pause_event=None, naming=""):
    park_started.set()
    park_release.wait(6)   # hold mid-download until the test lets go
    (Path(output_root) / "Park").mkdir(parents=True, exist_ok=True)
    return "Park", 1, 100, 0.0


downloader.download_chapter = parkable_chapter
tpa = manga_gui.QueueTask("http://fake/park/a", str(BASE / "lib2"), 1, 0.0, False, False, False)
tpb = manga_gui.QueueTask("http://fake/park/b", str(BASE / "lib2"), 1, 0.0, False, False, False)
app.queue_tasks = [tpa, tpb]
app.save_queue()
pump(root, 0.5)          # flush the previous queue_done so the busy guard is clear
modal_calls.clear()
app.start_queue()
if not park_started.is_set():
    pump(root, 1.0)
check("queue started (no busy dialog)", "info" not in modal_calls, str(modal_calls))
pump_until(root, lambda: park_started.is_set(), timeout=4, label="first task mid-download")
app.pause_queue()        # gate set BEFORE tpa may finish -> tpb must park
park_release.set()       # tpa may complete now; worker proceeds to the boundary
ok = pump_until(root, lambda: tpa.state == "completed" and tpb.state == "paused", timeout=5,
                label="task parked at boundary")
check("task parked at boundary", ok, f"a={tpa.state} b={tpb.state}")
app.resume_queue()
ok = pump_until(root, lambda: tpb.state == "completed", timeout=5, label="parked task finishes")
check("parked task finishes after resume", ok, tpb.state)


# Bounded retry: dead task exhausts attempts, the FOLLOWING task still completes.
def flaky_chapter(session, url, output_root, delay, timeout, overwrite,
                  cancel_event=None, progress_callback=None, bytes_callback=None,
                  pause_event=None, naming=""):
    if "dead" in url:
        raise RuntimeError("boom")
    (Path(output_root) / "After").mkdir(parents=True, exist_ok=True)
    return "After", 1, 100, 0.0


downloader.download_chapter = flaky_chapter
app.settings.set("retries", 2)
dead = manga_gui.QueueTask("http://fake/dead/ch-1", str(BASE / "lib3"), 1, 0.0, False, False, False)
after_dead = manga_gui.QueueTask("http://fake/after/ch-1", str(BASE / "lib3"), 1, 0.0, False, False, False)
app.queue_tasks = [dead, after_dead]
app.save_queue()
pump(root, 0.5)          # flush park-run queue_done
app.start_queue()
ok = pump_until(root, lambda: dead.state == "failed" and after_dead.state == "completed", timeout=12,
                label="dead task fails, queue continues")
check("dead task fails after bounded retries", ok, dead.state)
check("attempts = MAX_ATTEMPTS", dead.attempts == dead.MAX_ATTEMPTS, str(dead.attempts))
check("queue continues past failure", after_dead.state == "completed", after_dead.state)
app.settings.set("retries", 3)

# ===========================================================================
# PHASE 4 — SQLite history: CRUD, search/sort, events, migration
# ===========================================================================
section("Phase 4: SQLite history")

from history_store import HistoryStore

store = HistoryStore(BASE / "store_test.db")
store.add_record({"id": "r1", "time": "2026-01-01 10:00:00", "source": "Naruto ch 1",
                  "output": str(BASE / "a"), "status": "Completed", "details": "ok",
                  "url": "http://a/1", "chapters": 2, "pages": 24})
store.add_record({"id": "r2", "time": "2026-01-02 10:00:00", "source": "Có lỗi ch 9",
                  "output": str(BASE / "b"), "status": "Có lỗi", "details": "boom",
                  "url": "http://b/9", "chapters": 0, "pages": 3})
check("count", store.count() == 2, str(store.count()))
check("search status (legacy VI label)", len(store.search("", status_values=["Có lỗi"])) == 1)
check("search query", len(store.search("naruto")) == 1)
check("sort ascending", store.search(order_by="created_at", descending=False)[0]["id"] == "r1")
store.update_record("r1", status="Stopped", details="halted")
check("update_record", store.search("naruto")[0]["status"] == "Stopped")
store.add_event("r1", "started", "begin")
store.add_event("r1", "finished", "done")
check("events trail", len(store.events("r1")) == 2)
store.prune_events("r1", limit=1)
check("prune keeps latest", len(store.events("r1")) == 1 and store.events("r1")[0]["kind"] == "finished")
check("delete cascades", store.delete_records(["r1"]) == 1 and store.events("r1") == [])
store.close()

# One-time JSON -> SQLite migration.
legacy_dir = BASE / "legacy"
legacy_dir.mkdir(exist_ok=True)
manga_gui.MangaGui.get_history_file = classmethod(lambda cls: legacy_dir / "history.db")
(legacy_dir / "download_history.json").write_text(json.dumps([
    {"id": "old1", "time": "t", "source": "Old", "output": "o", "status": "Completed",
     "details": "d", "url": "http://old/1", "chapters": 4, "pages": 40},
]), encoding="utf-8")
legacy_app = manga_gui.MangaGui(root)
check("migration imports record", any(r["id"] == "old1" for r in legacy_app._history_records()))
check("migration keeps chapters/pages", any(r.get("chapters") == 4 and r.get("pages") == 40
                                            for r in legacy_app._history_records()))
check("json renamed to .migrated", (legacy_dir / "download_history.json.migrated").exists()
      and not (legacy_dir / "download_history.json").exists())
manga_gui.MangaGui.get_history_file = classmethod(lambda cls: BASE / "history.db")
legacy_app.closing = True   # stop this secondary instance's event pump

# ===========================================================================
# PHASE 5 — bytes progress: rolling speed, formatters, ETA
# ===========================================================================
section("Phase 5: transfer speed / ETA")

check("format_bytes", manga_gui.MangaGui.format_bytes(2048) == "2.0 KB")
check("format_duration", manga_gui.MangaGui.format_duration(95) == "1:35")

# Numeric ETA: rate must be stable for 3s -> arm the flags manually instead of
# waiting out the wall clock.
app.reset_transfer_stats()
now = time.time()
app.note_transfer_bytes(1_000_000)
app.transfer_samples = [(now - 10.0, 0), (now, 1_000_000)]
app.eta_pages_done, app.eta_pages_total = 3, 5   # ETA requires >=3 finished pages
app.transfer_eta_stable = True
app.transfer_stable_rate = 100.0                  # KB/s
app.transfer_eta_stable_since = time.monotonic() - 4.0
speed, eta = app.transfer_summary(100.0)
check("speed computed from window", "KB/s" in speed or "MB/s" in speed, speed)
check("eta numeric when stable", bool(re.match(r"^\d+:\d\d$", eta.strip())), eta)

app.reset_transfer_stats()
app.transfer_samples = [(now - 10.0, 0), (now - 5.0, 1_000_000), (now, 2_000_000)]
speed2, _ = app.transfer_summary(100.0)
check("stable window keeps speed", speed2 == speed, f"{speed} vs {speed2}")

app.reset_transfer_stats()
_, eta_few = app.transfer_summary(100.0)
check("eta withheld on too few samples", "calculating" in eta_few or "—" in eta_few, eta_few)


# A download that emits bytes and STAYS alive long enough for the pump to
# observe the speed state (and the live last_bytes assignment) mid-run.
def bytey_chapter(session, url, output_root, delay, timeout, overwrite,
                  cancel_event=None, progress_callback=None, bytes_callback=None,
                  pause_event=None, naming=""):
    (Path(output_root) / "Bytey").mkdir(parents=True, exist_ok=True)
    if progress_callback:
        progress_callback("Bytey", 1, 2)
    if bytes_callback:
        bytes_callback(1_234_567, 2_500_000, 640.0)
    time.sleep(0.8)   # keep the run alive across pump ticks
    return "Bytey", 2, 1_234_567, 0.0


downloader.download_chapter = bytey_chapter
t5 = manga_gui.QueueTask("http://fake/bytes/ch-1", str(BASE / "lib4"), 1, 0.0, False, False, False)
app.queue_tasks = [t5]
app.save_queue()
pump(root, 0.5)          # flush dead-run queue_done
modal_calls.clear()
app.start_queue()
check("speed run started (no busy dialog)", "info" not in modal_calls, str(modal_calls))
ok = pump_until(root, lambda: "KB/s" in app.status_text.get() or "MB/s" in app.status_text.get(),
                timeout=4, label="speed in status bar")
check("status bar shows speed", ok, app.status_text.get())
check("last_bytes live during run", t5.last_bytes == 1_234_567, str(t5.last_bytes))
pump(root, 0.6)

# ===========================================================================
# PHASE 6 — archive library: scan, views, rename/delete
# ===========================================================================
section("Phase 6: archive library")

lib_root = BASE / "lib4"
img_bytes = make_image_bytes()
(lib_root / "Bytey" / "001.jpg").write_bytes(img_bytes)
(lib_root / "Bytey.cbz").write_bytes(b"PK\x05\x06" + b"\x00" * 18)   # sibling of the folder
(lib_root / "Empty").mkdir(exist_ok=True)

archive = manga_gui.ArchiveLibrary()
items = archive.scan([str(lib_root)])
check("scan finds chapter dir", "Bytey" in items, str(list(items)))
check("scan skips empty dir", "Empty" not in items)
check("item page count", items["Bytey"].page_count == 1, str(items["Bytey"].page_count))
check("item cover found", items["Bytey"].cover_path is not None)
check("item sees sibling cbz", items["Bytey"].has_cbz)

win = app.open_library()
win.archive.scan = lambda roots: dict(items)   # pin the scanned library
win.rescan()
win.refresh_items()
pump(root, 0.3)
check("library window opens", win.winfo_exists())
check("items listed", len(win.filtered) == 1, str(len(win.filtered)))
win.view_mode = "list"
win._render()
pump(root, 0.1)
check("list view renders", win.view_mode == "list")

# rename: forbidden char rejected, valid rename moves dir + cbz together
manga_gui.simpledialog.askstring = lambda *a, **k: "Renamed:Bad"
win.rename_item(items["Bytey"])
check("forbidden rename rejected", (lib_root / "Bytey").exists() and not (lib_root / "RenamedBad").exists())
manga_gui.simpledialog.askstring = lambda *a, **k: "Renamed Good"
win.rename_item(items["Bytey"])
check("valid rename moves dir + cbz", (lib_root / "Renamed Good").exists()
      and (lib_root / "Renamed Good.cbz").exists()
      and not (lib_root / "Bytey").exists())

# Drop the pinned scan: from here on the window must see the real disk,
# including the renamed folder.
del win.archive.scan
win.rescan()
win.refresh_items()
pump(root, 0.2)
check("rescan sees renamed dir", len(win.filtered) == 1 and win.filtered[0].folder.exists(),
      str([str(i.folder) for i in win.filtered]))
renamed_item = win.filtered[0]

# delete: confirm honored, cancels when the user declines
manga_gui.messagebox.askyesno = lambda *a, **k: False
win.delete_item(renamed_item)
check("declined delete keeps files", (lib_root / "Renamed Good").exists())
manga_gui.messagebox.askyesno = lambda *a, **k: True
win.delete_item(renamed_item)
pump(root, 0.3)
gone_dir = not (lib_root / "Renamed Good").exists()
gone_cbz = not (lib_root / "Renamed Good.cbz").exists()
check("confirmed delete removes dir + cbz", gone_dir and gone_cbz,
      f"dir_gone={gone_dir} cbz_gone={gone_cbz}")
win.destroy()
pump(root, 0.1)

# ===========================================================================
# PHASE 7 — settings: persistence, type guard, reset, theme rebuild
# ===========================================================================
section("Phase 7: settings")

app.settings.set("timeout", 45)
app.settings.set("retries", 7)
app.settings.set("naming", "site")
app.settings.set("theme", "light")
app.settings.save()
roundtrip = manga_gui.AppSettings(BASE / "settings.json")
check("settings round-trip", (roundtrip.get("timeout"), roundtrip.get("retries"), roundtrip.get("naming")) == (45, 7, "site"),
      str((roundtrip.get("timeout"), roundtrip.get("retries"), roundtrip.get("naming"))))
check("settings type guard", (app.settings.set("timeout", "not-a-number") or app.settings.get("timeout")) == 45)

corrupt = BASE / "corrupt.json"
corrupt.write_text("{not json", encoding="utf-8")
check("corrupt settings fall back to defaults", manga_gui.AppSettings(corrupt).get("timeout") == 30)

app.apply_appearance()   # rebuild UI under light theme
pump(root, 0.3)
check("theme rebuild keeps language", app.current_language == "en", app.current_language)
check("text_widgets live after rebuild", any(w.winfo_exists() for w in app.text_widgets.values()))
app.settings.set("density", "compact")
app.apply_appearance()
pump(root, 0.3)
check("density rebuild survives", app.root.winfo_exists())

# ===========================================================================
# PHASE 8 — toasts: non-modal, notify suppression, no modal popups
# ===========================================================================
section("Phase 8: toasts")

app.settings.set("notify", True)
app.settings.save()
app.show_toast("Title EN", "Body", kind="success")
app.show_toast("Title VI", "Body", kind="error")
pump(root, 0.2)
live = [t for t in app.toasts if t.winfo_exists()]
check("toast created", len(live) == 2, str(len(live)))
check("toast non-modal (no grab)", all(not t.grab_current() for t in live))
app.close_all_toasts()
pump(root, 0.1)
check("close_all_toasts", not [t for t in app.toasts if t.winfo_exists()])

app.settings.set("notify", False)
app.settings.save()
app.show_toast("Suppressed", "Body", kind="info")
pump(root, 0.1)
check("notify=False suppresses toasts", not [t for t in app.toasts if t.winfo_exists()])
app.settings.set("notify", True)
app.settings.save()

# done/error events through the real pump toast instead of modal popups.
modal_calls.clear()
downloader.download_chapter = fake_chapter
calls["chapters"] = 500
t8 = manga_gui.QueueTask("http://fake/toast/ch-1", str(BASE / "lib5"), 1, 0.0, False, False, False)
app.queue_tasks = [t8]
app.save_queue()
pump(root, 0.5)          # flush speed-run queue_done
app.start_queue()
pump_until(root, lambda: t8.state == "completed", timeout=4, label="task for toast")
pump(root, 0.5)
check("no modal popup on success", "info" not in modal_calls, str(modal_calls))
check("success toast appeared", any(t.winfo_exists() for t in app.toasts), str(len(app.toasts)))
app.close_all_toasts()

# ===========================================================================
# PHASE 9 — frozen exe: version resource + --version contract
# ===========================================================================
section("Phase 9: frozen exe")

exe = REPO_ROOT / "dist" / "MangaDownloader.exe"
if exe.exists():
    proc = subprocess.run([str(exe), "--version"], capture_output=True, text=True, timeout=60,
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    check("exe --version exit", proc.returncode == 0, str(proc.returncode))
    check("exe --version output", proc.stdout.strip() == "MangaDownloader 1.0.0", proc.stdout.strip())
    check("exe exists and sized", exe.stat().st_size > 1_000_000, f"{exe.stat().st_size} bytes")
else:
    print("  SKIP  frozen-exe checks (dist/MangaDownloader.exe not built in this environment)",
          flush=True)

# ===========================================================================
# CLEAN SHUTDOWN + SUMMARY
# ===========================================================================
section("Shutdown")

app.exit_application()
pump(root, 0.5)
try:
    destroyed = not root.winfo_exists()
except tk.TclError:
    destroyed = True   # app already gone
check("root destroyed on exit", destroyed)
if not destroyed:
    root.destroy()

print("\n" + "=" * 62, flush=True)
print(f"TOTAL: {len(RESULT_PASS)} pass, {len(RESULT_FAIL)} fail", flush=True)
if RESULT_FAIL:
    print("Failures:", flush=True)
    for fail in RESULT_FAIL:
        print(f"  - {fail}", flush=True)
print("=" * 62, flush=True)
sys.exit(0 if not RESULT_FAIL else 1)
