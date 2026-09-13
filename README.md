# Manga Downloader

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
- Includes a command-line interface for scripted downloads.

## Requirements

- Python 3.10 or newer
- `requests`
- `beautifulsoup4`
- `Pillow`

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
Windows Script Host process. The batch terminal exits immediately, while the
GUI continues running independently. `launch_gui.vbs` resolves the
`pythonw.exe` path from the active Python launcher and never runs the GUI
through a console-based `py.exe` process.

Choose `English` or `Tiếng Việt` from the language selector. The URL and output
folder fields start empty so they can be filled with your own values. Choose the
first chapter URL, select the chapter range and output folder, then enable
`WebP → JPG` and `Create CBZ` when needed. Each chapter is saved in its own
folder, with the `.cbz` file beside that folder.

The `All chapters` option follows the website's `Next chapter` link until no
next link is found.

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

## Troubleshooting

If the downloader reports a DNS or connection error, test the domain outside
the script first:

```powershell
Resolve-DnsName example.com
Test-NetConnection example.com -Port 443
```

The downloader uses the operating system's normal DNS and network settings. It
does not attempt to work around network filters or website access controls.
