from __future__ import annotations

import html
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from core.pixeldrain import parse_pixeldrain_url, resolve_pixeldrain_url

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)


def _valid_media_url(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    value = html.unescape(value).strip().strip('"\'')
    if not value or value.startswith(("blob:", "data:")):
        return None
    value = urljoin(base_url, value)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def extract_playback_url_from_html(text: str, base_url: str) -> str | None:
    """Best-effort extraction of a browser-playable media URL from a video page."""
    if not text:
        return None

    candidates: list[tuple[int, str]] = []

    def add(value: str | None, score: int) -> None:
        url = _valid_media_url(value, base_url)
        if url:
            candidates.append((score, url))

    # OpenGraph video metadata is the cleanest signal when present.
    for match in re.finditer(
        r"<meta\b[^>]*(?:property|name)\s*=\s*['\"]([^'\"]+)['\"][^>]*content\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
        text,
        flags=re.I,
    ):
        key, value = match.group(1).strip().lower(), match.group(2)
        if key in {"og:video", "og:video:url", "og:video:secure_url"}:
            add(value, 120)

    for match in re.finditer(
        r"<meta\b[^>]*content\s*=\s*['\"]([^'\"]+)['\"][^>]*(?:property|name)\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
        text,
        flags=re.I,
    ):
        value, key = match.group(1), match.group(2).strip().lower()
        if key in {"og:video", "og:video:url", "og:video:secure_url"}:
            add(value, 120)

    # JSON-LD VideoObject contentUrl/embedUrl.
    for block in re.findall(
        r"<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
        text,
        flags=re.I | re.S,
    ):
        try:
            data = json.loads(html.unescape(block.strip()))
        except Exception:
            continue

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    lower = str(key).lower()
                    if lower == "contenturl" and isinstance(item, str):
                        add(item, 115)
                    elif lower == "embedurl" and isinstance(item, str):
                        # Usually a webpage/player rather than media; keep as weak fallback.
                        add(item, 35)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(data)

    # Native video/source tags.
    for pattern, score in (
        (r"<source\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", 110),
        (r"<video\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", 108),
        (r"\bdata-(?:src|video|video-url|file)\s*=\s*['\"]([^'\"]+)['\"]", 90),
    ):
        for match in re.finditer(pattern, text, flags=re.I):
            add(match.group(1), score)

    # Common player configuration keys used by WordPress/custom players.
    for pattern, score in (
        (r"['\"](?:file|src|source|video_url|videoUrl|contentUrl)['\"]\s*:\s*['\"]([^'\"]+)['\"]", 95),
        (r"(?:file|src|source|video_url|videoUrl)\s*=\s*['\"]([^'\"]+)['\"]", 85),
    ):
        for match in re.finditer(pattern, text, flags=re.I):
            add(match.group(1).replace(r"\/", "/"), score)

    # Direct media URLs embedded anywhere in the HTML/JS.
    for match in re.finditer(
        r"https?:(?:\\/\\/|//)[^\s'\"<>]+?(?:\.mp4|\.webm|\.m3u8)(?:\?[^\s'\"<>]*)?",
        text,
        flags=re.I,
    ):
        add(match.group(0).replace(r"\/", "/"), 80)

    if not candidates:
        return None

    # Prefer actual media-looking URLs over generic pages at equal score.
    def rank(item: tuple[int, str]) -> tuple[int, int]:
        score, url = item
        media_bonus = 10 if re.search(r"\.(?:mp4|webm|m3u8)(?:$|[?#])", url, re.I) else 0
        return score + media_bonus, -len(url)

    return max(candidates, key=rank)[1]


def resolve_playback_url(site: str | None, video_id: str | None, source_url: str | None, timeout: float = 12.0) -> str | None:
    """Resolve the URL that xToys can hand to its generic URL video action.

    Pixeldrain has a deterministic direct-file endpoint. HMVMania and PMVHaven
    are resolved from their page markup at index-build time. If extraction fails,
    return None so the JS player falls back to manual synchronization.
    """
    site_value = (site or "").strip().lower().removeprefix("www.")
    source = (source_url or "").strip()

    if site_value in {"pixeldrain", "pixeldrain.com"}:
        file_id = (video_id or "").strip()
        if source:
            resolved = resolve_pixeldrain_url(source, timeout=timeout)
            if resolved and resolved.get("file_id"):
                file_id = str(resolved["file_id"])
        if file_id and "#item=" not in file_id:
            return f"https://pixeldrain.com/api/file/{file_id}"
        return None

    if site_value not in {"hmvmania", "hmvmania.com", "pmvhaven", "pmvhaven.com"}:
        return None
    if not source or not re.match(r"^https?://", source, re.I):
        return None

    try:
        request = Request(
            source,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        with urlopen(request, timeout=timeout) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if content_type and "html" not in content_type and "xhtml" not in content_type:
                final_url = response.geturl()
                return final_url if final_url else source
            raw = response.read(4_000_000)
            charset = response.headers.get_content_charset() or "utf-8"
    except (HTTPError, URLError, TimeoutError, OSError):
        return None

    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    return extract_playback_url_from_html(text, source)
