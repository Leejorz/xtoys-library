from __future__ import annotations

import base64
import html
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image

from core.pixeldrain import resolve_pixeldrain_url


class ThumbnailExtractor:
    """Best-effort video-source thumbnail extraction without changing the DB schema.

    The extractor intentionally works from the source page metadata rather than
    requiring the source to be playable by xToys.  This keeps thumbnail support
    independent from the player's playback capabilities.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )

    @classmethod
    def fetch(cls, source_url: str | None, timeout: float = 12.0) -> str | None:
        if not source_url:
            return None

        url = source_url.strip()
        if not re.match(r"^https?://", url, re.I):
            return None

        # Pixeldrain exposes a dedicated thumbnail endpoint. For list URLs,
        # resolve #item=N to the concrete file before building that endpoint.
        resolved_pixeldrain = resolve_pixeldrain_url(url, timeout=timeout)
        if resolved_pixeldrain and resolved_pixeldrain.get("thumbnail_url"):
            return resolved_pixeldrain["thumbnail_url"]

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
                    return None
                raw = response.read(2_500_000)
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

        encoding = "utf-8"
        content_type = ""
        try:
            content_type = response.headers.get_content_charset() or ""
        except Exception:
            pass
        if content_type:
            encoding = content_type

        try:
            text = raw.decode(encoding, errors="replace")
        except LookupError:
            text = raw.decode("utf-8", errors="replace")

        return cls.extract_from_html(text, url)

    @classmethod
    def extract_from_html(cls, text: str, base_url: str) -> str | None:
        if not text:
            return None

        # Highest-confidence source: OpenGraph image used by most supported
        # video sites.  Prefer image dimensions when multiple values exist.
        candidates: list[tuple[int, str]] = []

        def add(value: str | None, score: int) -> None:
            if not value:
                return
            value = html.unescape(value).strip().strip("\"'")
            if not value or value.startswith("data:") or value.startswith("blob:"):
                return
            value = urljoin(base_url, value)
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return
            candidates.append((score, value))

        # Handle either property/name first and content in either attribute order.
        for match in re.finditer(
            r"<meta\b[^>]*(?:property|name)\s*=\s*['\"]([^'\"]+)['\"][^>]*content\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
            text,
            flags=re.I,
        ):
            key, value = match.group(1).strip().lower(), match.group(2)
            if key in {"og:image", "og:image:url"}:
                add(value, 100)
            elif key in {"twitter:image", "twitter:image:src"}:
                add(value, 90)
            elif key in {"thumbnail", "thumbnailurl", "video:thumbnail"}:
                add(value, 85)

        for match in re.finditer(
            r"<meta\b[^>]*content\s*=\s*['\"]([^'\"]+)['\"][^>]*(?:property|name)\s*=\s*['\"]([^'\"]+)['\"][^>]*>",
            text,
            flags=re.I,
        ):
            value, key = match.group(1), match.group(2).strip().lower()
            if key in {"og:image", "og:image:url"}:
                add(value, 100)
            elif key in {"twitter:image", "twitter:image:src"}:
                add(value, 90)
            elif key in {"thumbnail", "thumbnailurl", "video:thumbnail"}:
                add(value, 85)

        # JSON-LD is a common fallback on video pages.
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
                        if str(key).lower() in {"thumbnailurl", "thumbnail_url"}:
                            if isinstance(item, list):
                                for entry in item:
                                    if isinstance(entry, str):
                                        add(entry, 80)
                            elif isinstance(item, str):
                                add(item, 80)
                        walk(item)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            walk(data)

        # Player poster / data attributes are useful when social metadata is absent.
        for pattern, score in (
            (r"<video\b[^>]*\bposter\s*=\s*['\"]([^'\"]+)['\"]", 75),
            (r"\b(?:data-poster|data-thumbnail|data-thumb)\s*=\s*['\"]([^'\"]+)['\"]", 70),
        ):
            for match in re.finditer(pattern, text, flags=re.I):
                add(match.group(1), score)

        # Last-resort image candidates.  Avoid tiny UI assets and known icons.
        for match in re.finditer(
            r"<img\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]",
            text,
            flags=re.I,
        ):
            value = match.group(1)
            lower = value.lower()
            if any(token in lower for token in ("logo", "avatar", "icon", "emoji", "favicon")):
                continue
            add(value, 40)

        if not candidates:
            return None

        # Deduplicate while retaining the highest score for each URL.
        best: dict[str, int] = {}
        for score, value in candidates:
            best[value] = max(score, best.get(value, 0))
        return max(best.items(), key=lambda item: item[1])[0]

    @classmethod
    def download_image(
        cls,
        image_url: str | None,
        destination_stem: Path,
        referer: str | None = None,
        timeout: float = 15.0,
    ) -> Path | None:
        """Download and normalize a thumbnail in the original xToys format.

        The xsqueezeme library's ``images/*.jpeg`` files are intentionally text
        files containing a ``data:image/jpeg;base64,...`` URL.  The Generic
        Funscript Player fetches those files with ``getXhr()`` and passes the
        returned text directly to ``canvas.drawImage()``.

        Therefore we must *not* write raw binary JPEG bytes here.  Decode the
        remote image, normalize it to RGB JPEG, resize it to the same 256px
        maximum used by the original project, then save the base64 data URL as
        UTF-8 text in a ``.jpeg`` file.
        """
        if not image_url:
            return None

        url = image_url.strip()
        if not re.match(r"^https?://", url, re.I):
            return None

        headers = {
            "User-Agent": cls.USER_AGENT,
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        }
        if referer:
            headers["Referer"] = referer

        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                content_type = (
                    (response.headers.get("Content-Type") or "")
                    .split(";", 1)[0]
                    .strip()
                    .lower()
                )
                data = response.read(10_000_001)
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

        if not data or len(data) > 10_000_000:
            return None

        # Reject obvious non-image responses before Pillow sees them.
        if content_type and not content_type.startswith("image/"):
            return None

        try:
            with Image.open(BytesIO(data)) as source:
                source.load()

                # Animated images use the first frame, matching thumbnail use.
                try:
                    source.seek(0)
                except Exception:
                    pass

                image = source.convert("RGB")
                image.thumbnail((256, 256), Image.Resampling.LANCZOS)

                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85, optimize=True)
                jpeg_bytes = buffer.getvalue()

            # Verify that the normalized output is itself a readable JPEG.
            with Image.open(BytesIO(jpeg_bytes)) as verify:
                verify.verify()

        except Exception:
            return None

        data_url = (
            "data:image/jpeg;base64,"
            + base64.b64encode(jpeg_bytes).decode("ascii")
        )

        destination_stem.parent.mkdir(parents=True, exist_ok=True)
        destination = destination_stem.with_suffix(".jpeg")

        try:
            destination.write_text(data_url, encoding="utf-8")
        except OSError:
            return None

        return destination
