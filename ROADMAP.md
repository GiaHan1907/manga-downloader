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

**Status: Planned.**

- Make sidebar navigation functional: Downloader, History, Archive, Settings.
- Add clear state labels: Ready, Preparing, Downloading, Converting, Creating CBZ, Complete, Failed.
- Make the activity log collapsible or move it to a detail panel.
- Add open-output-folder action and tooltips.
- Test minimum window size and Vietnamese layout.

### Phase 2 — Download queue

**Status: Planned.**

- Add multiple URL tasks with queued, active, completed, stopped, and failed states.
- Start all/selected, remove, reorder, clear completed, and retry failed.
- Persist unfinished queue tasks safely.
- Keep task logs and progress separated.

### Phase 3 — Pause, resume, and retry

**Status: Planned.**

- Pause after the current request without deleting completed files.
- Resume by skipping already-present page files.
- Add automatic retry with bounded exponential backoff.
- Expose retry count and final error details.

### Phase 4 — Advanced history

**Status: Planned.**

- Evaluate migration from JSON to SQLite once queue/history grows.
- Add search, filters, sorting, open folder, copy URL, retry, delete record, and export.
- Add a detailed task view with chapter/page events and errors.

### Phase 5 — Speed, size, and ETA

**Status: Planned.**

- Track bytes, rolling speed, page/chapter counts, and ETA.
- Update UI from the main thread only.
- Avoid unstable ETA before enough samples exist.

### Phase 6 — Archive library

**Status: Planned.**

- Scan local output and CBZ files.
- Add cover/grid/list views, search, filters, open folder, open CBZ, refresh, rename, and delete with safeguards.

### Phase 7 — Settings

**Status: Planned.**

- Persist output folder, delay, timeout, retries, conversion/CBZ defaults, naming, notification preferences, language, theme, density, and tray behavior.
- Add validation and reset-to-defaults.

### Phase 8 — Windows notifications

**Status: Planned.**

- Add non-modal Windows toast notifications for completion, failure, and queue completion.
- Keep sound, popup, and tray notification preferences independent.

### Phase 9 — Release packaging

**Status: Planned.**

- Add versioning, changelog, portable package, installer, shortcuts, optional CBZ association, and clean-install testing.
- Consider code signing only when a certificate is available.

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
