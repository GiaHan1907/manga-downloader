#!/usr/bin/env python3
"""Download manga pages from a publicly accessible web reader.

Use only for content you are allowed to download.  The script does not try to
bypass login pages, CAPTCHAs, paywalls, hotlink protection, or other access
controls.  It also waits between requests to avoid putting unnecessary load on
the website.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import mimetypes
import re
import sys
import time
from pathlib import Path
from threading import Event
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_URL = "https://truyentuoitho.com/manga/ninja-loan-thi/tap-1/"
DEFAULT_DELAY = 1.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)


class DownloadCancelled(RuntimeError):
    """Raised when the GUI requests a clean stop between page downloads."""


def normalize_url(raw_url: str) -> str:
    """Accept a plain URL as well as a Markdown link copied from chat."""
    value = raw_url.strip()
    markdown = re.fullmatch(r"\[[^\]]+\]\((https?://[^)]+)\)", value)
    if markdown:
        value = markdown.group(1)
    value = value.strip().strip("<>")
    if not re.match(r"^https?://", value, re.IGNORECASE):
        raise ValueError("URL must start with http:// or https://")
    return value


def clean_name(value: str, fallback: str) -> str:
    """Make a safe Windows-compatible directory or filename component."""
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    return value[:120] or fallback


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "vi,en;q=0.8"})
    return session


def best_src(img, page_url: str) -> str | None:
    """Return the most likely full-size image URL from an <img> element."""
    for attr in ("data-src", "data-lazy-src", "data-original", "data-url", "src"):
        value = img.get(attr)
        if value and not value.startswith("data:"):
            return urljoin(page_url, value.strip())

    # Some readers expose only srcset. Pick the largest candidate.
    srcset = img.get("data-srcset") or img.get("srcset")
    if srcset:
        candidates = []
        for item in srcset.split(","):
            bits = item.strip().split()
            if not bits:
                continue
            width = 0
            if len(bits) > 1:
                match = re.match(r"(\d+)w", bits[1])
                width = int(match.group(1)) if match else 0
            candidates.append((width, urljoin(page_url, bits[0])))
        if candidates:
            return max(candidates)[1]
    return None


def is_probable_page_image(url: str, img) -> bool:
    """Filter common theme icons, logos, thumbnails, and tracking pixels."""
    lower = url.lower()
    classes = " ".join(img.get("class", [])).lower()
    image_id = str(img.get("id", "")).lower()
    hints = f"{lower} {classes} {image_id}"
    blocked = ("logo", "avatar", "icon", "favicon", "sprite", "banner", "ads", "advert")
    if any(word in hints for word in blocked):
        return False
    if lower.startswith(("javascript:", "mailto:", "data:")):
        return False
    return True


def extract_images(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    seen: set[str] = set()

    # Prefer reader containers, then fall back to all images for theme changes.
    containers = soup.select(
        ".reading-content, .reading-content-wrap, .entry-content, "
        ".chapter-content, .wp-manga-chapter-img, article"
    )
    images = [img for container in containers for img in container.select("img")]
    if not images:
        images = soup.select("img")

    for img in images:
        image_url = best_src(img, page_url)
        if image_url and image_url not in seen and is_probable_page_image(image_url, img):
            seen.add(image_url)
            urls.append(image_url)
    return urls


def page_title(html: str, url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for selector in ("h1", ".entry-title", ".c-breadcrumb-wrapper h1", "title"):
        node = soup.select_one(selector)
        if node and node.get_text(" ", strip=True):
            return clean_name(node.get_text(" ", strip=True), "chapter")
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return clean_name(slug, "chapter")


def next_chapter(html: str, current_url: str) -> str | None:
    """Find a same-site next-chapter link, if the page exposes one."""
    soup = BeautifulSoup(html, "html.parser")
    current = urlparse(current_url)
    for link in soup.select("a"):
        text = link.get_text(" ", strip=True).lower()
        rel = " ".join(link.get("rel", [])).lower()
        href = link.get("href")
        if not href:
            continue
        candidate = urljoin(current_url, href)
        parsed = urlparse(candidate)
        if parsed.netloc != current.netloc:
            continue
        if ("tập sau" in text or "tap sau" in text or "next" in rel or "next" in text) and candidate != current_url:
            return candidate
    return None


def extension_from_response(response: requests.Response, image_url: str) -> str:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    ext = mimetypes.guess_extension(content_type) if content_type.startswith("image/") else None
    if ext in {".jpe", ".jpeg"}:
        return ".jpg"
    if ext:
        return ext
    suffix = Path(urlparse(image_url).path).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"} else ".jpg"


def download_chapter(
    session: requests.Session,
    chapter_url: str,
    output_root: Path,
    delay: float,
    timeout: float,
    overwrite: bool,
    cancel_event: Event | None = None,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> tuple[str, int]:
    if cancel_event and cancel_event.is_set():
        raise DownloadCancelled("Stopped by user request.")
    response = session.get(chapter_url, timeout=timeout)
    response.raise_for_status()
    title = page_title(response.text, chapter_url)
    chapter_dir = output_root / title
    chapter_dir.mkdir(parents=True, exist_ok=True)
    image_urls = extract_images(response.text, response.url)
    if not image_urls:
        raise RuntimeError("No chapter page images were found in the HTML.")
    if progress_callback:
        progress_callback(title, 0, len(image_urls))

    print(f"{title}: found {len(image_urls)} images")
    downloaded = 0
    for index, image_url in enumerate(image_urls, start=1):
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelled("Stopped by user request.")
        # Page extension is discovered after the response, so a temporary path
        # is not needed: use the common jpg name first and preserve existing files.
        existing = next((chapter_dir / f"{index:04d}{ext}" for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif") if (chapter_dir / f"{index:04d}{ext}").exists()), None)
        if existing and not overwrite:
            print(f"  [{index}/{len(image_urls)}] already exists, skipped")
            if progress_callback:
                progress_callback(title, index, len(image_urls))
            continue

        if index > 1:
            if cancel_event:
                if cancel_event.wait(delay):
                    raise DownloadCancelled("Stopped by user request.")
            else:
                time.sleep(delay)
        image_response = session.get(
            image_url,
            headers={"Referer": response.url, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"},
            timeout=timeout,
        )
        image_response.raise_for_status()
        if not image_response.content:
            raise RuntimeError(f"Empty image response: {image_url}")
        ext = extension_from_response(image_response, image_url)
        target = chapter_dir / f"{index:04d}{ext}"
        target.write_bytes(image_response.content)
        downloaded += 1
        print(f"  [{index}/{len(image_urls)}] {target.name}")
        if progress_callback:
            progress_callback(title, index, len(image_urls))
    return title, len(image_urls)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download manga page images from a public reader.")
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="Chapter URL")
    parser.add_argument("-o", "--output", default="downloads", help="Output directory (default: downloads)")
    parser.add_argument("--follow-next", action="store_true", help="Follow the site's next-chapter link")
    parser.add_argument("--max-chapters", type=int, default=0, help="Maximum chapters with --follow-next; 0 = unlimited")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Seconds between image requests (default: 1)")
    parser.add_argument("--timeout", type=float, default=30, help="Request timeout in seconds")
    parser.add_argument("--overwrite", action="store_true", help="Re-download existing images")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.delay < 0 or args.timeout <= 0:
        print("--delay must be >= 0 and --timeout must be > 0", file=sys.stderr)
        return 2
    try:
        url = normalize_url(args.url)
    except ValueError as exc:
        print(f"URL error: {exc}", file=sys.stderr)
        return 2
    if url != args.url.strip():
        print(f"Normalized URL: {url}")

    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    session = make_session()
    visited: set[str] = set()
    chapters = 0

    while url and url not in visited:
        if args.max_chapters and chapters >= args.max_chapters:
            break
        visited.add(url)
        try:
            title, _ = download_chapter(session, url, output_root, args.delay, args.timeout, args.overwrite)
            chapters += 1
            print(f"Processed: {title}")
            if not args.follow_next:
                break
            time.sleep(max(args.delay, 1.0))
            page = session.get(url, timeout=args.timeout)
            page.raise_for_status()
            url = next_chapter(page.text, page.url)
            if url:
                print(f"Next chapter: {url}")
        except requests.HTTPError as exc:
            print(f"HTTP error at {url}: {exc}", file=sys.stderr)
            return 1
        except requests.ConnectionError as exc:
            host = urlparse(url).hostname or "website"
            print(f"Connection error for {host}: {exc}", file=sys.stderr)
            print(
                "Tip: check DNS with "
                f"Resolve-DnsName {host}. If it returns 127.0.0.1 or ::1, "
                "change DNS or switch networks and try again.",
                file=sys.stderr,
            )
            return 1
        except requests.RequestException as exc:
            print(f"Network error at {url}: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
