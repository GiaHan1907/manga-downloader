# Changelog

All notable changes to Manga Downloader are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Phase 10.1 — Single-instance guard: a named Windows mutex denies a second
  launch, which signals the running instance (flag file + main-thread poll)
  to surface its window and exits cleanly; two apps can no longer share the
  same `queue.json`/`history.db`.
- Phase 10.2 — Crash log and fatal toast: `sys.excepthook` and
  `threading.excepthook` write `crash-*.crash.log` (traceback, version,
  activity-log tail) into AppData and a non-modal toast surfaces the error;
  fatal errors no longer vanish silently.
- Phase 10.3 — Data-file self-checks and recovery: `history.db` is validated
  with a SQLite integrity check + schema probe and `queue.json` with a schema
  probe on startup; damaged files are quarantined as `.corrupt` and rebuilt
  from timestamped `.bak` snapshots (history via `VACUUM INTO`, queue after
  every save, newest 3 kept).
- Phase 10.4 — Queue-level progress: the queue card gains an aggregate header
  (`task i/N · completed/failed · bytes`) and a thick progress bar computed on
  the main thread; byte totals are banked on final task states, persist in
  `queue.json`, and re-queued tasks stop contributing (no double counting).
- Phase 10.5 — Richer history events: every finished task stores a `transfer`
  history event with pages downloaded, bytes transferred, paused seconds and
  attempts (localized EN/VI), and the history record's `pages` column now
  holds the real page count; the pump handler for history writes is
  fault-isolated so a database error cannot stop event delivery.
- Phase 10.6 — Truncated-image guard: when the server declares
  `Content-Length`, a short response body raises `TruncatedImageError` before
  the file is written, so truncated images never enter chapter folders or CBZ
  archives and retries refetch them via the existing skip-existing resume.
- Phase 10.7 — First-run onboarding hints: bilingual empty-state hints on the
  queue and history cards and in the library window's empty state, hidden
  whenever content exists and re-evaluated on language switches.
- Phase 10.8 — `--url` CLI-to-GUI bridge: `--url <chapter-url>` opens the GUI
  with the field prefilled; when an instance is already running, the second
  launch forwards the URL through the single-instance show request (flag
  payload "show" = surface only, a URL = prefill and surface) and exits 0.
- Performance: the per-task log panel no longer rebuilds its entire content
  on every emitted log line during a download. It renders incrementally with
  a rendered-line cache, and the event pump coalesces bursts into one render
  per tick; a 400-line chapter log went from ~2.1 s of cumulative Tk work to
  a few milliseconds. Activity-log writes track widget state in a Python flag
  instead of an extra Tk round-trip per line.
- Fixed a latent bug surfaced while testing 10.4: `QueueTask.from_dict`
  returned before restoring `total_bytes`/`bank_bytes`, so persisted byte
  totals were silently dropped on reload; the bytes now also survive app
  restarts. `_exit_application` additionally cancels the single-instance poll
  tick, removing a `bgerror` at shutdown.

## [1.0.0] — 2026-09-16

First feature-complete release covering ROADMAP phases 0–9.

### Added
- **Downloader core (Phase 0)**: chapter page downloads from public readers
  with delay, timeout, overwrite handling, and a strict no-access-control-
  bypass safety boundary.
- **GUI (Tkinter, dark/light)**: bilingual English/Tiếng Việt interface with
  system-tray integration and terminal-detached launch on Windows.
- **Phase 1 — Workspace**: searchable download history, open-output-folder
  actions, tooltips, collapsible activity log, and unified status labels with
  colored state dots (Ready / Preparing / Downloading / Converting /
  Creating CBZ / Complete / Failed).
- **Phase 2 — Download queue**: task model with per-task state and progress,
  sequential queue runner, add/remove/reorder/retry/clear controls, per-task
  log panel, and crash-safe `queue.json` persistence with atomic writes.
- **Phase 3 — Reliability**: page-level and task-boundary pause/resume,
  automatic retries with bounded exponential backoff (2s→4s→8s, cap 30s),
  retry counts persisted, and event-pump hardening.
- **Phase 4 — Advanced history**: SQLite-backed history with one-time JSON
  migration, SQL-backed search, status filters, sorting, per-record actions
  (copy URL, re-queue, delete, CSV export), and a per-record event trail.
- **Phase 5 — Speed, size, ETA**: 10-second rolling speed window computed in
  the worker (pause time excluded), smoothed ETA that only appears once the
  rate is stable, and live per-task progress in the queue tree.
- **Phase 6 — Archive library**: scans output roots for chapter folders and
  CBZ archives, cover grid + list views with async thumbnails, search and
  CBZ filters, plus open/rename/delete with safeguards (bilingual).
- **Phase 7 — Settings**: persisted `settings.json` (atomic, type-guarded)
  covering timeout, retries, chapter folder naming (strip site / slug),
  sound, popups, close-to-tray, language, and dark/light/system theme with
  comfortable/compact density; validation and reset-to-defaults.
- **Phase 8 — Windows notifications**: non-modal slide-in toasts for
  completion, failure, stop, and queue events with a success/failed summary;
  clicking a toast restores the window; governed by the independent
  notification preference.

### Changed
- Line endings normalized repository-wide via `.gitattributes` (LF for text,
  CRLF for Windows scripts, binary handling for icons).
- Event pump no longer schedules ticks after shutdown (no more `bgerror`
  noise while the app closes).

### Fixed
- Tray thread reading Tkinter variables crashed on shutdown.
- One failing event handler could kill the GUI event pump.
- Retried tasks duplicated history rows; history selection was lost on
  refresh; combobox startup crash with empty values; settings/theme rebuild
  issues found by smoke tests.
- Queue transfer tracking: `last_bytes` is now recorded per progress event.
- Archive library rename/delete survive transient Windows sharing locks
  (antivirus, indexer, image viewers) via bounded filesystem retries.

### Fixed
- Tray thread reading Tkinter variables crashed on shutdown.
- One failing event handler could kill the GUI event pump.
- Retried tasks duplicated history rows; history selection was lost on
  refresh; combobox startup crash with empty values; settings/theme rebuild
  issues found by smoke tests.

### Packaging
- PyInstaller one-file windowed build with bundled PNG/ICO resources,
  `pystray` hidden imports, and Windows version metadata
  (`MangaDownloader.spec`, `version_info.txt`, `build_exe.bat`).
- Composite regression suite (77 checks, phases 0–9) runs on GitHub Actions
  (`windows-latest`) on every push; the suite plus a clean-install run of the
  exe (first-run, legacy migration, tray/exit) verified this release.
