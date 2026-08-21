from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from core.pixeldrain import resolve_pixeldrain_url
from core.thumbnails import ThumbnailExtractor


@dataclass
class VideoPageMetadata:
    tags: list[str]
    thumbnail_url: str | None = None


class VideoMetadataExtractor:
    """Best-effort per-video metadata extraction for importer enrichment.

    This deliberately uses short, bounded HTTP reads and never raises for a
    remote-site failure.  EroScripts tags remain the per-script fallback.
    """

    USER_AGENT = ThumbnailExtractor.USER_AGENT
    MAX_HTML_BYTES = 2_500_000
    MAX_TAGS = 40

    # Generic labels that are poor library classifiers when scraped from hosts.
    IGNORED = {
        "video", "videos", "download", "downloads", "watch", "home",
        "hmv", "pmv", "funscript", "funscripts", "eroscripts", "porn",
        "adult", "nsfw", "uncategorized", "category", "categories", "tag",
        "tags", "featured", "latest", "popular",
    }

    @classmethod
    def fetch(cls, source_url: str | None, timeout: float = 6.0) -> VideoPageMetadata:
        if not source_url:
            return VideoPageMetadata([])
        url = str(source_url).strip()
        if not re.match(r"^https?://", url, re.I):
            return VideoPageMetadata([])

        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        if "pixeldrain" in host or host == "pixeldra.in":
            resolved = resolve_pixeldrain_url(url, timeout=timeout)
            thumb = resolved.get("thumbnail_url") if resolved else None
            # Pixeldrain is a file host, not a useful semantic tag source.
            return VideoPageMetadata([], thumb)

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": cls.USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                content_type = (response.headers.get("Content-Type") or "").lower()
                if content_type and "html" not in content_type and "xhtml" not in content_type:
                    return VideoPageMetadata([])
                raw = response.read(cls.MAX_HTML_BYTES + 1)
                if len(raw) > cls.MAX_HTML_BYTES:
                    return VideoPageMetadata([])
                charset = response.headers.get_content_charset() or "utf-8"
        except (HTTPError, URLError, TimeoutError, OSError):
            return VideoPageMetadata([])

        try:
            text = raw.decode(charset, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")

        host = (urlparse(url).hostname or "").lower().removeprefix("www.")
        if host == "rule34video.com" or host.endswith(".rule34video.com"):
            # Rule34Video pages contain many unrelated /tags/ links in menus,
            # recommendations and other page chrome.  Only trust the explicit
            # per-video Tags row.  If that row cannot be isolated, return no
            # source tags so the importer falls back to this funscript's own
            # EroScripts tags rather than guessing.
            tags = cls.extract_rule34video_tags(text)
        else:
            tags = cls.extract_tags_from_html(text, url)

        return VideoPageMetadata(
            tags=tags,
            thumbnail_url=ThumbnailExtractor.extract_from_html(text, url),
        )

    @classmethod
    def _clean_tag(cls, value: object) -> str | None:
        if value is None:
            return None
        tag = html.unescape(str(value))
        tag = re.sub(r"<[^>]+>", " ", tag)
        tag = re.sub(r"\s+", " ", tag).strip(" \t\r\n,;|/#")
        if not tag or len(tag) > 60:
            return None
        if re.match(r"^https?://", tag, re.I):
            return None
        if tag.casefold() in cls.IGNORED:
            return None
        if not re.search(r"[A-Za-z0-9]", tag):
            return None
        return tag

    @classmethod
    def extract_rule34video_tags(cls, text: str) -> list[str]:
        """Return only tags from Rule34Video's explicit per-video Tags row.

        The site repeats tag links in navigation/recommendations, so a whole-page
        /tags/ scrape produces unrelated labels.  Anchor extraction is therefore
        restricted to the markup between the visible ``Tags`` label and the next
        ``Download`` section.
        """
        if not text:
            return []

        # Locate the visible metadata-row label rather than metadata keywords.
        start_match = re.search(r">\s*Tags\s*<", text, flags=re.I)
        if not start_match:
            return []
        start = start_match.end()
        # The tag pills sit immediately before the Download row on current pages.
        tail = text[start:start + 16000]
        stop_match = re.search(r">\s*Download\s*<", tail, flags=re.I)
        if stop_match:
            tail = tail[:stop_match.start()]

        found: list[str] = []
        seen: set[str] = set()
        for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", tail, flags=re.I | re.S):
            attrs, body = match.group(1), match.group(2)
            href_match = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)['\"]", attrs, flags=re.I)
            href = html.unescape(href_match.group(1)) if href_match else ""
            path = urlparse(href).path.lower() if href else ""
            # Rule34Video's actual video tags use /tags/... links.
            if not re.search(r"/(?:tag|tags)/", path):
                continue
            label = html.unescape(re.sub(r"<[^>]+>", " ", body))
            tag = re.sub(r"\s+", " ", label).strip(" \t\r\n,;|/#")
            # The explicit Rule34Video Tags row is already high confidence, so
            # keep meaningful labels such as PMV/HMV that the generic scraper
            # intentionally suppresses on noisier sites.
            if (
                not tag
                or len(tag) > 60
                or not re.search(r"[A-Za-z0-9]", tag)
                or tag.casefold() in {"suggest", "+ suggest", "video", "download", "tags"}
            ):
                continue
            key = tag.casefold()
            if key in seen:
                continue
            seen.add(key)
            found.append(tag)
            if len(found) >= 20:
                break
        return found

    @classmethod
    def extract_tags_from_html(cls, text: str, base_url: str = "") -> list[str]:
        if not text:
            return []

        found: list[str] = []
        seen: set[str] = set()

        def add(value: object) -> None:
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    add(item)
                return
            if isinstance(value, str) and ("," in value or ";" in value):
                for item in re.split(r"[,;]", value):
                    add(item)
                return
            tag = cls._clean_tag(value)
            if not tag:
                return
            key = tag.casefold()
            if key in seen:
                return
            seen.add(key)
            found.append(tag)

        # Standard keywords metadata.
        for match in re.finditer(
            r"<meta\b[^>]*(?:name|property)\s*=\s*['\"]([^'\"]+)['\"][^>]*content\s*=\s*['\"]([^'\"]*)['\"][^>]*>",
            text, flags=re.I,
        ):
            key, value = match.group(1).strip().lower(), match.group(2)
            if key in {"keywords", "news_keywords", "article:tag", "video:tag"}:
                add(value)
        for match in re.finditer(
            r"<meta\b[^>]*content\s*=\s*['\"]([^'\"]*)['\"][^>]*(?:name|property)\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
            text, flags=re.I,
        ):
            value, key = match.group(1), match.group(2).strip().lower()
            if key in {"keywords", "news_keywords", "article:tag", "video:tag"}:
                add(value)

        # JSON-LD VideoObject / article metadata.
        for block in re.findall(
            r"<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
            text, flags=re.I | re.S,
        ):
            try:
                data = json.loads(html.unescape(block.strip()))
            except Exception:
                continue

            def walk(value):
                if isinstance(value, dict):
                    for key, item in value.items():
                        low = str(key).lower()
                        if low in {"keywords", "genre", "tags", "tag"}:
                            add(item)
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            walk(data)

        # Visible tag links used by WordPress and most video CMSs.
        for match in re.finditer(
            r"<a\b([^>]*)>(.*?)</a>", text, flags=re.I | re.S,
        ):
            attrs, body = match.group(1), match.group(2)
            href_match = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)['\"]", attrs, flags=re.I)
            rel_match = re.search(r"\brel\s*=\s*['\"]([^'\"]+)['\"]", attrs, flags=re.I)
            href = html.unescape(href_match.group(1)) if href_match else ""
            rel = (rel_match.group(1) if rel_match else "").lower()
            parsed_path = urlparse(urljoin(base_url, href)).path.lower() if href else ""
            if "tag" not in rel.split() and not re.search(r"/(?:tag|tags)/", parsed_path):
                continue
            label = re.sub(r"<[^>]+>", " ", body)
            add(label)

        return found[: cls.MAX_TAGS]
