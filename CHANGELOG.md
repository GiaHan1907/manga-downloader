# Changelog

All notable changes to Manga Downloader are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

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
