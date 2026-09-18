# Manga Downloader

[![Regression](https://github.com/GiaHan1907/manga-downloader/actions/workflows/regression.yml/badge.svg)](https://github.com/GiaHan1907/manga-downloader/actions/workflows/regression.yml)

A small Python downloader for publicly accessible manga reader pages. It saves
chapter images locally, can follow the site's next-chapter links, converts WebP
pages to JPG, and packages each chapter as a CBZ archive.

Use this project only for content you are legally allowed to download. The
software does not bypass logins, CAPTCHAs, paywalls, hotlink protection, or
other access controls.

## Features

- Tkinter desktop GUI with a dark Codex-style workspace layout.
- Download one chapter or follow the next-chapter link for 5, 10, or all chapters.
- Supports lazy-loaded image attributes such as `data-src`, `data-lazy-src`, and `srcset`.
- Resume-friendly behavior: existing pages are skipped unless overwrite is enabled.
- Convert `.webp` pages to `.jpg` while preserving the original WebP files.
- Create one `.cbz` archive per chapter.
- Shows per-page and overall chapter progress.
- Keeps a persistent download history with status and details.
- Provides a searchable history view matching manga URLs, output paths, statuses, and details.
- Includes functional History and Settings workspace views from the sidebar.
- Minimizes to the Windows system tray when the window is closed.
- Includes a command-line interface for scripted downloads.

## Requirements

- Python 3.10 or newer
- `requests`
- `beautifulsoup4`
- `Pillow`
- `pystray`

Install the dependencies:

```powershell
py -m pip install -r requirements.txt
```

## Graphical interface

Start the GUI:

```powershell
py manga_gui.py
```

On Windows, double-click `run.bat` to launch the GUI through a detached
Windows Script Host process. `launch_gui.vbs` starts `detached_gui.py` hidden;
the helper then spawns the real `pythonw.exe` interpreter outside the terminal
process tree. The temporary batch terminal closes immediately and does not
control the GUI lifetime.

Choose `English` or `Tiếng Việt` from the language selector. The URL and output
folder fields start empty so they can be filled with your own values. Choose the
first chapter URL, select the chapter range and output folder, then enable
`WebP → JPG` and `Create CBZ` when needed. Each chapter is saved in its own
folder, with the `.cbz` file beside that folder.

The `All chapters` option follows the website's `Next chapter` link until no
next link is found.

Closing the window hides it in the system tray instead of exiting. Use the
tray icon menu to show the window again or exit the application. Download
history is stored locally in `%APPDATA%\MangaDownloader\download_history.json` and keeps
the latest 100 records.

### Verify the GUI layout on Windows

Run the layout smoke test from the repository root after launching the project
environment. It opens Downloader, History, Library, and Settings, records the
required widget geometry, and saves one screenshot per view when Pillow's
`ImageGrab` is available:

```powershell
py tools\check_gui_layout.py --output .relcheck\gui-layout
```

The generated `layout-report.json` contains missing-control checks and window
dimensions. Add `--keep-open` when visually comparing the final view with the
HTML redesign demo.

## Build a standalone Windows executable

Run `build_exe.bat` on Windows. The script installs the project dependencies
and PyInstaller, then creates `dist\MangaDownloader.exe`. The executable is
windowed and can run without a separate Python installation. The same build is
also described by `MangaDownloader.spec` for reproducible PyInstaller builds.

The exe carries Windows version metadata from `version_info.txt` and accepts
`--version` to print the app version (`MangaDownloader 1.0.0`). Releases are
documented in `CHANGELOG.md`.

## Command-line interface

Download the default chapter:

```powershell
py download_manga.py "https://truyentuoitho.com/manga/ninja-loan-thi/tap-1/"
```

Follow the next-chapter link for up to five chapters:

```powershell
py download_manga.py "https://truyentuoitho.com/manga/ninja-loan-thi/tap-1/" --follow-next --max-chapters 5
```

Useful options:

```text
-o, --output DIRECTORY       Output directory (default: downloads)
--follow-next                Follow the site's next-chapter link
--max-chapters N             Maximum chapters; 0 means unlimited
--delay SECONDS              Delay between image requests
--timeout SECONDS            Request timeout
--overwrite                  Re-download existing images
```

## Output layout

```text
downloads/
├── Manga Title - Chapter 1/
│   ├── 0001.jpg
│   ├── 0002.jpg
│   └── ...
└── Manga Title - Chapter 1.cbz
```

## Testing

A composite regression suite covers phases 0-9 of the roadmap in one run
(persistence, queue, pause/retry, SQLite history, transfer speed, archive
library, settings, toasts). It runs on every push via GitHub Actions on
`windows-latest` and can be run locally with:

```bat
python -u tests\regression_all.py
```

Exit code 0 means all checks passed. The frozen-exe checks skip automatically
when `dist\MangaDownloader.exe` has not been built.

## Troubleshooting

If the downloader reports a DNS or connection error, test the domain outside
the script first:

```powershell
Resolve-DnsName example.com
Test-NetConnection example.com -Port 443
```

The downloader uses the operating system's normal DNS and network settings. It
does not attempt to work around network filters or website access controls.
