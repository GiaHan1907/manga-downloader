# Manga Downloader — Roadmap and AI Handoff

This document is the working handoff for future AI contributors. Read it before making changes, preserve completed behavior, and update the relevant phase status after each implementation.

## Project snapshot

The project is a Windows-focused Python/Tkinter manga downloader. It downloads publicly accessible chapter images, follows next-chapter links, converts WebP images to JPG, creates CBZ archives, and exposes both a GUI and CLI.

The current branch is `main`. The intended source entry point is `manga_gui.py`; `run.bat` launches the detached GUI source through `launch_gui.vbs`. The standalone executable is built with `build_exe.bat` and `MangaDownloader.spec`.

## Completed capabilities

- Download one chapter or 5, 10, or all chapters through next-chapter links.
- Resume-friendly skipping of existing page files.
- WebP-to-JPG conversion with original WebP preservation.
- CBZ creation per chapter.
- Per-page and overall progress bars.
- English and Vietnamese UI text.
- Completion popup and Windows completion sound with fallback.
- Manus-inspired dark workspace styling with purple accent, expanded sidebar, cards, spacing, and `MANUS WORKSPACE` badge.
- Basic system tray behavior: closing the window hides it; tray menu can show the window or exit.
- Persistent JSON download history with time, source, output path, status, and details; latest 100 records are retained.
- `MangaDownloader.png` used by the window/tray and bundled into the application.
- Generated multi-size `MangaDownloader.ico` for Windows executable branding.
- PyInstaller build script with cleanup of obsolete `pathlib` backport and locked old executable handling.
- Open-output-folder actions in the folder card and the actions row; a missing folder can be created after confirmation.
- Hover tooltips on the main controls, resolved in the active UI language.
- Collapsible activity log with a Hide/Show toggle that keeps the window layout stable.
- Phase 2 download queue: add tasks from the URL field, run the queue sequentially, per-task states (queued/active/completed/stopped/failed), remove/reorder/retry failed/clear completed, start selected or all pending tasks, per-task log panel, and atomic `queue.json` persistence with crash recovery (an `active` task found on startup returns to `queued`).
- Unified status-bar states through `set_state()`: Ready, Preparing, Downloading, Converting, Creating CBZ, Complete/Queue finished, Stopped/Queue paused, Error — each with a color-coded indicator dot and full Vietnamese translations; workers emit `Converting`/`Creating CBZ` state events around post-processing.

## Known limitations and risks

- The `.exe` must be built on Windows. A previous build attempt failed when an old `dist\\MangaDownloader.exe` was still running/locked; always exit the tray application before rebuilding. `build_exe.bat` now attempts to terminate the old process and delete the old executable.
- The current tray feature depends on `pystray`; when it is unavailable in source development, close exits instead of minimizing.
- Download history is JSON and is not yet a full queue database.
- Sidebar entries for Archive and Settings are visual navigation items only; they do not yet switch pages.
- The downloader currently has one active worker and no true pause/resume queue.
- Do not add scraping bypasses, CAPTCHA bypasses, paywall bypasses, or access-control workarounds.

## Phase plan

### Phase 0 — Platform stability

**Status: In progress / must be revalidated on Windows.**

Checkpoint update: the first Phase 0 review found that `.gitignore` excluded
`MangaDownloader.spec`, which made clean GitHub clones unable to reproduce the
icon-enabled PyInstaller build. This was fixed and pushed in commit `bb60f39`.

1. Install dependencies in the intended Windows Python environment.
2. Remove obsolete `pathlib` backport if PyInstaller reports it.
3. Close all running MangaDownloader tray/process instances.
4. Run `build_exe.bat` and confirm `dist\\MangaDownloader.exe` exists.
5. Launch the executable without a terminal.
6. Verify the custom icon, system tray show/exit behavior, history persistence, and clean process exit.
7. Repeat the build twice to confirm replacement works.

Acceptance: clean standalone EXE build and no orphan process after tray exit.

### Phase 1 — UI and UX foundation

**Status: In progress — navigation, history search, open-folder, tooltips, and collapsible log implemented.**

- Make sidebar navigation functional: Downloader, History, Archive, Settings.
- Current checkpoint: the second sidebar item now opens a dedicated searchable
  History window; Settings opens a dedicated settings placeholder window. The
  main Downloader view also has a live history filter.
- Search matches source URL, output path, status, and details.
- Open-output-folder actions added to the folder card and the actions row;
  `os.startfile` on Windows with `open`/`xdg-open` fallbacks, and a missing
  folder can be created after a confirmation prompt.
- Tooltips cover the URL entry, output folder buttons, start/stop, delay,
  history search, conversion checkboxes, and clear-log button. Tooltip text is
  resolved lazily so switching English/Vietnamese updates it too.
- The activity log collapses through a Hide/Show toggle using
  `grid_remove`/`grid`, resizing the window height instead of breaking the
  grid weights.
- Still open: minimum-window-size testing with the Vietnamese layout.

### Phase 2 — Download queue

**Status: Implemented in source — needs real-network validation.**

- Add multiple URL tasks with queued, active, completed, stopped, and failed states — done.
- Start all/selected, remove, reorder, clear completed, and retry failed — done.
- Persist unfinished queue tasks safely — done (`queue.json` written atomically via temp file + `os.replace`; unfinished tasks survive restart).
- Keep task logs and progress separated — done (per-task log panel next to the queue table; main activity log keeps global entries).
- Still open: task detail view with chapter/page events, and manual reordering of multi-selection mid-list (current move moves selection to top/bottom).

### Phase 3 — Pause, resume, and retry

**Status: Implemented in source — needs real-network validation.**

- Pause after the current request without deleting completed files — done: `queue_pause_event` suspends `download_chapter` between page requests and parks pending tasks in a `paused` state at task boundaries.
- Resume by skipping already-present page files — done: pause/resume relies on the existing skip-existing behavior; page 1 survives a failed attempt and the retry only fetches missing pages.
- Add automatic retry with bounded exponential backoff — done: up to `QueueTask.MAX_ATTEMPTS = 3` attempts per task with 2s/4s/8s… backoff capped at 30s; only Stop can cut a backoff short.
- Expose retry count and final error details — done: `attempts` persists in `queue.json`, is reset by Retry, and per-task logs plus history records keep the last error.
- Bug fixes made along the way: retried tasks no longer duplicate rows in the history tree, and one failing event handler can no longer kill the GUI event pump (`finally` reschedule in `process_events`).

### Phase 4 — Advanced history

**Status: Implemented (local, uncommitted).**

- Evaluate migration from JSON to SQLite once queue/history grows — done: new `history_store.py` keeps records + per-record events in `history.db` (AppData); the legacy `download_history.json` is imported once on first open and renamed to `.migrated` as a backup. All GUI history reads/writes go through `HistoryStore` now.
- Add search, filters, sorting, open folder, copy URL, retry, delete record, and export — done: real-time search (URL/output/status/details) now backed by SQL `LIKE`; status filter (All / Completed / Failed / Stopped-Paused, matching old EN and VI labels so pre-migration records stay filterable); sort by newest/oldest/source; per-record actions Copy URL, Re-queue to download queue (reuses the record's URL/output), delete with confirmation, and CSV export of the current view; record count label on the main history card.
- Add a detailed task view with chapter/page events and errors — done: an events panel below the history window list shows the started/finished trail of the selected record (pruned to 300 events); selection survives refreshes so the detail view follows filter/sort/language changes.
- Bug fixes made along the way: combobox startup crash when `values` was empty, migration dropped `chapters`/`pages` from legacy records, and opening the history window no longer loses the current selection (the events panel stays populated).

### Phase 5 — Speed, size, and ETA

**Status: Implemented (local, uncommitted).**

- Track bytes, rolling speed, page/chapter counts, and ETA — done: `download_chapter` now accepts a `bytes_callback(received_bytes, total_bytes, kbps)` fed by a 10 s rolling speed window inside the worker (pause time excluded), and returns `(title, pages, downloaded, paused_seconds)`. The GUI keeps all math on the main thread: `note_transfer_bytes` maintains the samples/smoothed rate, `transfer_summary` derives speed and ETA text, and the status bar shows `Downloading <chapter> — <speed> · <bytes> · ETA <time>` (EN/VI) while the queue's Progress column shows `<chapters> · <bytes> · <speed>` for the active task. Bytes reset per chapter; the smoothed rate survives retries but resets when a queue task starts.
- Update UI from the main thread only — done: everything arrives as a `bytes_progress` event consumed by `process_events`.
- Avoid unstable ETA before enough samples exist — done: the ETA hides ("calculating") until at least 3 samples exist, the smoothed rate has been stable within ±25 % for 3 s, and at least 3 pages of the current chapter are done; it then estimates remaining pages × average bytes per page ÷ smoothed rate.

### Phase 6 — Archive library

**Status: Implemented (local, uncommitted).**

- Scan local output and CBZ files — done: a `ArchiveLibrary.scan` walks the current output folder plus the 50 most recent history output roots, keeps chapter folders that contain page images or a sibling `<name>.cbz`, skips non-chapter files and empty directories, and deduplicates by chapter name. Scan runs synchronously on demand (open + ↻ Scan button); thumbnails decode on daemon threads that only push results into a queue drained by an `after()` loop on the main thread (ROADMAP rule #4).
- Add cover/grid/list views, search, filters, open folder, open CBZ, refresh, rename, and delete with safeguards — done: the Library window (sidebar `▦ Library`) offers a cover grid (double-click opens the CBZ if present, else the folder) and a list view, real-time search, a status filter (All / CBZ ready / Pages only), an item count, and a right-click menu with Open CBZ, Open folder, Rename and Delete. Rename validates the new name (illegal characters, duplicates, no-op) and moves the folder plus its CBZ together; Delete confirms with the page count before `rmtree`, and also removes the sibling CBZ. All labels are bilingual (EN/VI) and follow the language switch live.

### Phase 7 — Settings

**Status: Implemented (local, uncommitted).**

- Persist output folder, delay, timeout, retries, conversion/CBZ defaults, naming, notification preferences, language, theme, density, and tray behavior — done: an `AppSettings` store keeps everything in `settings.json` next to the queue file with atomic writes and type-guarded loads. The Settings window covers request timeout (5–120 s), automatic retries per task (1–10, wired live into `QueueTask.MAX_ATTEMPTS`), chapter folder naming (original title / strip site name / slug-only / both — implemented in `page_title`), completion sound, popups on completion/failure, close-to-tray behavior, language, and theme/density. The chosen language re-applies at startup and survives UI rebuilds; the timeout and naming mode are threaded through `download_worker` and the CLI-side `download_chapter`.
- Add validation and reset-to-defaults — done: Save validates ranges with a bilingual error and keeps the previous values on failure; ↺ Reset restores defaults everywhere (disk, form, live language, retries) with confirmation-free logging; theme/density (Dark / Light / follow-Windows, Comfortable / Compact) are applied by rebuilding the main UI in place, with the language selection preserved across the rebuild.

### Phase 8 — Windows notifications

**Status: Implemented (local, uncommitted).**

- Add non-modal Windows toast notifications for completion, failure, and queue completion — done: a dependency-free `show_toast` builds a slide-in `Toplevel` (no taskbar entry, always-on-top) anchored at the bottom-right corner of the screen, stacking above any toast already visible. It renders in the app's dark/light palette with a per-kind accent bar (green success, red failure, purple info, amber warning), self-dismisses after 6 s, and clicking it restores the main window — so a download finishing while the window is hidden in the tray is one click away. Toasts fire on: single download done (replaces the old modal popup), download failed (replaces the old modal popup), stopped, queue finished (with a `{done} succeeded · {failed} failed` summary computed from the task states), and queue paused. Because they are non-modal, downloads no longer pause behind a dialog box.
- Keep sound, popup, and tray notification preferences independent — done: toasts respect the Phase 7 `notify` preference only (`toasts_enabled()`), while the completion sound stays governed by the separate `sound` preference; suppress `notify` and the completion sound still plays, and no toast or popup appears.
- Cleanup: `_exit_application` destroys any lingering toasts before closing the app.

### Phase 9 — Release packaging

**Status: Implemented (local, uncommitted).**

- Add versioning, changelog, portable package, installer, shortcuts, optional CBZ association, and clean-install testing — done: `APP_VERSION = "1.0.0"` lives in `manga_gui.py` with a `--version` CLI flag (works in the windowed exe, prints and exits), the version is shown in the window title, the sidebar, and the tray tooltip; `version_info.txt` embeds Windows file/product metadata (verified via `Get-Item ... .VersionInfo`); `CHANGELOG.md` documents phases 0–9. The portable package is the one-file `dist\MangaDownloader.exe` (~36 MB, no console, PNG + ICO resources bundled, `pystray` hidden imports + `PIL._tkinter_finder`), rebuilt with `build_exe.bat` which now smoke-checks `--version` after building. The full build + runtime smoke was executed on this machine: build succeeds, `--version` prints `MangaDownloader 1.0.0`, the GUI process starts with a visible `Manga Downloader · v1.0.0` window (verified via EnumWindows on the onefile child process). Installer/shortcuts/CBZ association stay open: no installer toolchain is required for the portable exe, and code signing is deferred until a certificate is available.

## Working rules for future AI contributors

1. Read this file and `README.md` before editing.
2. Preserve the existing downloader safety boundary and do not bypass access controls.
3. Make targeted edits; do not replace the whole GUI without need.
4. Keep Tkinter calls on the main thread; use the event queue for worker updates.
5. Run `python -m py_compile manga_gui.py download_manga.py` after source changes.
6. On Windows, close the tray app before rebuilding the EXE.
7. Update this roadmap status and acceptance notes after completing a phase.
8. Commit in coherent checkpoints with messages such as `phase-0: stabilize windows packaging`.
9. Do not commit temporary runtime folders, downloaded manga, `build/`, or `dist/` unless explicitly requested.

## Suggested next action

Complete Phase 0 on Windows first. The immediate verification command is:

```powershell
cd D:\Project\Manga-Downloader
build_exe.bat
```

Then launch `dist\\MangaDownloader.exe`, confirm the title contains `Manus Workspace`, and verify the custom icon and tray behavior.
