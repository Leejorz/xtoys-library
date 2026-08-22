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
    def fetch_rule34video_rendered(cls, page, source_url: str, timeout_ms: int = 10000) -> VideoPageMetadata:
        """Read Rule34Video metadata from the rendered browser DOM.

        Rule34Video can inject the per-video tag pills after the initial HTML
        response, so urllib/raw-HTML parsing may see no tags even though they
        are visible in the browser.  This helper intentionally reads only the
        explicit Tags row whose nearby sibling is the Download row.
        """
        if page is None or not source_url:
            return VideoPageMetadata([])
        try:
            page.goto(source_url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Give client-side video metadata a short bounded window to hydrate.
            try:
                page.wait_for_timeout(500)
            except Exception:
                pass
            data = page.evaluate(r"""() => {
                const norm = (v) => (v || '').replace(/\s+/g, ' ').trim();
                const isTagHref = (href) => {
                    try {
                        const p = new URL(href, location.href).pathname.toLowerCase();
                        return /\/(?:tag|tags)\//.test(p);
                    } catch (_) { return false; }
                };
                const visible = (el) => {
                    if (!el) return false;
                    const st = getComputedStyle(el);
                    return st.display !== 'none' && st.visibility !== 'hidden';
                };
                const exactLabel = (el, value) => visible(el) && norm(el.textContent).toLowerCase() === value;
                const labels = Array.from(document.querySelectorAll('span,strong,b,div,dt,th,label,p'))
                    .filter(el => exactLabel(el, 'tags'));
                const candidates = [];

                for (const label of labels) {
                    let row = label;
                    for (let depth = 0; depth < 6 && row; depth++, row = row.parentElement) {
                        const anchors = Array.from(row.querySelectorAll('a[href]'))
                            .filter(a => visible(a) && isTagHref(a.href));
                        if (!anchors.length) continue;

                        // The real Rule34Video Tags row sits immediately before
                        // the Download row in the video's info panel.  Require a
                        // nearby following sibling with an explicit Download label.
                        let sibling = row.nextElementSibling;
                        let hasDownload = false;
                        for (let i = 0; sibling && i < 4; i++, sibling = sibling.nextElementSibling) {
                            const text = norm(sibling.textContent).toLowerCase();
                            if (text === 'download' || text.startsWith('download ')) {
                                hasDownload = true;
                                break;
                            }
                            const dl = Array.from(sibling.querySelectorAll('span,strong,b,div,dt,th,label,p'))
                                .some(el => exactLabel(el, 'download'));
                            if (dl) { hasDownload = true; break; }
                        }
                        if (!hasDownload) continue;

                        const tags = [];
                        const seen = new Set();
                        for (const a of anchors) {
                            const tag = norm(a.textContent).replace(/^\+\s*/, '');
                            const key = tag.toLowerCase();
                            if (!tag || tag.length > 60 || key === 'suggest' || key === 'tags' || seen.has(key)) continue;
                            seen.add(key);
                            tags.push(tag);
                            if (tags.length >= 30) break;
                        }
                        if (tags.length) candidates.push({depth, tags});
                        break;
                    }
                }
                candidates.sort((a,b) => a.depth - b.depth || b.tags.length - a.tags.length);

                let thumbnail = null;
                const meta = document.querySelector('meta[property="og:image"],meta[name="twitter:image"]');
                if (meta) thumbnail = meta.content || null;
                if (!thumbnail) {
                    const video = document.querySelector('video[poster]');
                    if (video) thumbnail = video.poster || video.getAttribute('poster');
                }
                return {tags: candidates.length ? candidates[0].tags : [], thumbnail};
            }""")
            tags = []
            for value in (data or {}).get("tags", []):
                tag = cls._clean_tag(value)
                # Rule34's own explicit tag row is authoritative; unlike generic
                # metadata, PMV/HMV are valid intentional tags here.
                if not tag and str(value).strip().casefold() in {"pmv", "hmv"}:
                    tag = str(value).strip()
                if tag and tag.casefold() not in {t.casefold() for t in tags}:
                    tags.append(tag)
            thumb = (data or {}).get("thumbnail") or None
            return VideoPageMetadata(tags[:30], thumb)
        except Exception:
            return VideoPageMetadata([])

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

        Rule34Video repeats tag links in navigation and recommendations.  The
        video information panel places its real Tags row immediately before the
        Download row, but the labels can be wrapped in icons/spans and therefore
        are not reliably represented as a simple ``>Tags<`` token.

        We consequently evaluate every visible Download marker, walk backwards
        to the nearest standalone Tags marker, and accept only /tag(s)/ anchors
        between those two markers.  If no high-confidence row can be isolated,
        return [] rather than guessing from the rest of the page.
        """
        if not text:
            return []

        def clean_visible(value: str) -> str:
            value = re.sub(r"<script\b[^>]*>.*?</script>", " ", value, flags=re.I | re.S)
            value = re.sub(r"<style\b[^>]*>.*?</style>", " ", value, flags=re.I | re.S)
            value = html.unescape(re.sub(r"<[^>]+>", " ", value))
            return re.sub(r"\s+", " ", value).strip()

        # Match label text even when the site wraps it in spans/icons.  Avoid
        # attribute values by requiring a nearby tag boundary on at least one
        # side, then verify the candidate through the anchors found between the
        # Tags and Download labels.
        label_pattern = lambda label: re.compile(
            rf">\s*(?:<[^>]+>\s*){{0,5}}{label}\s*(?:</[^>]+>\s*){{0,5}}<",
            flags=re.I,
        )
        download_matches = list(label_pattern("Download").finditer(text))
        candidates: list[tuple[int, int, list[str]]] = []

        for download_match in download_matches:
            download_pos = download_match.start()
            # The info panel is compact; a 40 KB window is intentionally broad
            # enough for minified HTML while still excluding most page chrome.
            window_start = max(0, download_pos - 40000)
            before_download = text[window_start:download_pos]
            tag_matches = list(label_pattern("Tags").finditer(before_download))
            if not tag_matches:
                continue

            # Work backwards because the correct row is the nearest Tags label
            # before this Download row.  If a nearer 'Tags' token appears in an
            # attribute/script and produces no /tags/ anchors, try the previous
            # candidate rather than falling back to the whole page.
            for tag_match in reversed(tag_matches[-8:]):
                region_start = window_start + max(tag_match.start(), tag_match.end() - 1)
                region = text[region_start:download_pos]
                if len(region) > 16000:
                    continue

                found: list[str] = []
                seen: set[str] = set()
                for match in re.finditer(r"<a\b([^>]*)>(.*?)</a>", region, flags=re.I | re.S):
                    attrs, body = match.group(1), match.group(2)
                    href_match = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)['\"]", attrs, flags=re.I)
                    href = html.unescape(href_match.group(1)) if href_match else ""
                    path = urlparse(href).path.lower() if href else ""
                    if not re.search(r"/(?:tag|tags)/", path):
                        continue

                    tag = clean_visible(body).strip(" \t\r\n,;|/#")
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

                if found:
                    # Prefer the row closest to Download.  A shorter Tags->Download
                    # span is much less likely to be navigation/recommendation UI.
                    distance = download_pos - region_start
                    candidates.append((distance, -len(found), found))
                    break

        if not candidates:
            return []
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

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
