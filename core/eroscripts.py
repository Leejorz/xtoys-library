from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
import hashlib
import re

from playwright.sync_api import BrowserContext


@dataclass
class EroScriptsImportResult:
    page_url: str
    script_url: str
    filename: str
    content: bytes
    title: str

    creator: str | None = None
    tags: list[str] = field(default_factory=list)

    video_site: str | None = None
    video_title: str | None = None
    video_url: str | None = None
    video_id: str | None = None
    video_candidates: list[dict] = field(default_factory=list)
    thumbnail_url: str | None = None

    duration: str | None = None
    action_count: int | None = None
    average_speed: float | None = None

    content_hash: str = ""

    @property
    def file_size(self) -> int:
        return len(self.content)


class EroScriptsImporter:

    def __init__(
        self,
        context: BrowserContext,
        root: Path | None = None
    ):
        self.context = context
        self.root = Path(root).resolve() if root is not None else Path.cwd().resolve()

    def _write_diagnostic_report(self, page, page_url: str, candidates: list[tuple[str, str]], video_candidates: list[dict]) -> Path:
        """Write a safe diagnostic report for importer debugging.

        The report contains page/link structure and importer decisions, but never
        browser cookies, storage state, headers, or credentials.
        """
        logs_dir = self.root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = logs_dir / f"eroscripts_diagnostic_{stamp}.txt"

        lines = [
            "xToys Library Manager - EroScripts Import Diagnostic",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Page URL: {page_url}",
            f"Current page URL: {page.url}",
            "",
            "IMPORTANT: This report intentionally excludes cookies, storage state, request headers, and credentials.",
            "",
        ]

        try:
            body_text = page.locator("body").inner_text(timeout=10000)
        except Exception as exc:
            body_text = f"<body text unavailable: {type(exc).__name__}: {exc}>"

        lines += ["=== PAGE TEXT ===", body_text, ""]

        try:
            anchors = page.locator("a")
            count = anchors.count()
        except Exception as exc:
            anchors = None
            count = 0
            lines.append(f"Could not enumerate anchors: {type(exc).__name__}: {exc}")

        lines += [f"=== ALL PAGE LINKS ({count}) ==="]
        if anchors is not None:
            for i in range(count):
                try:
                    a = anchors.nth(i)
                    href = a.get_attribute("href") or ""
                    text = " ".join((a.inner_text(timeout=2000) or "").split())
                    lines.append(f"[{i+1}] text={text!r} href={href!r}")
                except Exception as exc:
                    lines.append(f"[{i+1}] <link read error: {type(exc).__name__}: {exc}>")
        lines.append("")

        lines += [f"=== UNIQUE FUNSCRIPT CANDIDATES ({len(candidates)}) ==="]
        for i, (script_url, filename) in enumerate(candidates, 1):
            lines += [f"[{i}] filename={filename!r}", f"    url={script_url}"]
            try:
                loc = page.locator(f'a[href="{script_url}"]')
                if loc.count() == 0:
                    # Short-link normalization can make the exact href differ.
                    loc = page.locator("a").filter(has_text=filename)
                if loc.count():
                    a = loc.first
                    lines.append(f"    anchor_text={' '.join((a.inner_text(timeout=2000) or '').split())!r}")
                    try:
                        parent_text = " ".join((a.locator("xpath=..").inner_text(timeout=2000) or "").split())
                        lines.append(f"    parent_text={parent_text!r}")
                    except Exception:
                        pass
                    try:
                        outer = a.evaluate("el => el.parentElement ? el.parentElement.outerHTML : el.outerHTML")
                        outer = re.sub(r"\\s+", " ", outer or "")
                        lines.append(f"    parent_html={outer[:4000]}")
                    except Exception:
                        pass
            except Exception as exc:
                lines.append(f"    context_error={type(exc).__name__}: {exc}")
        lines.append("")

        lines += [f"=== PAGE-WIDE VIDEO CANDIDATES ({len(video_candidates)}) ==="]
        for i, candidate in enumerate(video_candidates, 1):
            lines.append(f"[{i}] {candidate!r}")
        lines.append("")

        lines += ["=== PER-SCRIPT VIDEO ASSOCIATION ==="]
        for i, (script_url, filename) in enumerate(candidates, 1):
            matched = self.extract_video_for_script(page, script_url, filename)
            lines.append(f"[{i}] {filename!r}")
            lines.append(f"    matched_video={matched!r}")
        lines.append("")

        lines += [
            "=== IMPORTER NOTE ===",
            "The report is intended to reveal the page structure needed to associate individual funscripts with individual video sources.",
            "It does not contain browser cookies or Playwright storage state.",
        ]

        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def import_all_from_url(
        self,
        url: str,
        destination: Path
    ) -> list[EroScriptsImportResult]:
        """Import every unique funscript attachment on an EroScripts page."""
        print("\n[IMPORT] Cleaning EroScripts URL...")
        url = self.clean_url(url)
        print(f"[IMPORT] URL: {url}")
        if not url:
            raise ValueError("EroScripts URL cannot be empty.")

        page = self.context.new_page()
        try:
            print("[IMPORT] Opening browser page...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None:
                raise RuntimeError("EroScripts did not return a page response.")
            print("[IMPORT] Navigation complete.")
            print(f"[IMPORT] Current page: {page.url}")
            print(f"[IMPORT] HTTP status: {response.status}")
            if response.status >= 400:
                raise RuntimeError(f"EroScripts returned HTTP {response.status}.")
            print("[IMPORT] Checking login state...")
            if "/login" in page.url.lower():
                raise RuntimeError("The EroScripts session has expired. Please log in again through Settings -> EroScripts Login.")
            print("[IMPORT] Login check passed.")

            candidates = self.find_script_links(page, url)
            if not candidates:
                raise RuntimeError("Could not find a .funscript download link on the EroScripts page.")

            title = self.extract_topic_title(page)
            metadata = self.extract_metadata(page, title)
            video_candidates = self.extract_video_candidates(page)
            print(f"[IMPORT] Found {len(candidates)} unique .funscript candidate(s).")
            print("[IMPORT] Matching each funscript to the video link in its local EroScripts block.")

            diagnostic_path = self._write_diagnostic_report(page, url, candidates, video_candidates)
            print(f"[IMPORT] Diagnostic report: {diagnostic_path.resolve()}")

            destination.mkdir(parents=True, exist_ok=True)
            results = []
            for number, (script_url, filename) in enumerate(candidates, start=1):
                print(f"\n[IMPORT] Importing script {number}/{len(candidates)}: {filename}")
                content = self.download_script(page, script_url)
                output_path = destination / filename
                output_path.write_bytes(content)
                content_hash = hashlib.sha256(content).hexdigest()
                matched_video = self.extract_video_for_script(
                    page, script_url, filename
                )
                result_candidates = [matched_video] if matched_video else []
                if matched_video:
                    matched_video = dict(matched_video)
                    detected_id = self._extract_video_id_from_url(matched_video.get("url"))
                    if detected_id:
                        matched_video["video_id"] = detected_id
                    result_video_site = matched_video.get("site")
                    result_video_url = matched_video.get("url")
                    result_video_title = matched_video.get("title")
                else:
                    result_video_site = result_video_url = result_video_title = None
                results.append(EroScriptsImportResult(
                    page_url=url, script_url=script_url, filename=filename,
                    content=content, title=title, creator=metadata["creator"],
                    tags=metadata["tags"], video_site=result_video_site,
                    video_url=result_video_url, video_title=result_video_title,
                    video_id=(matched_video or {}).get("video_id"),
                    video_candidates=result_candidates,
                    thumbnail_url=self.extract_eroscripts_thumbnail(page, script_url),
                    duration=metadata["duration"], action_count=metadata["action_count"],
                    average_speed=metadata["average_speed"], content_hash=content_hash
                ))
                print(f"[IMPORT] Saved: {output_path}")
                print(f"[IMPORT] SHA256: {content_hash}")
            print(f"\n[IMPORT] Imported {len(results)} unique funscript(s).")
            return results
        finally:
            print("[IMPORT] Closing browser page...")
            try:
                page.close()
            except Exception:
                pass

    def import_from_url(
        self,
        url: str,
        destination: Path
    ) -> EroScriptsImportResult:

        print("\n[IMPORT] Cleaning EroScripts URL...")

        url = self.clean_url(url)

        print(
            f"[IMPORT] URL: {url}"
        )

        if not url:
            raise ValueError(
                "EroScripts URL cannot be empty."
            )

        print(
            "[IMPORT] Opening browser page..."
        )

        page = self.context.new_page()

        try:

            print(
                "[IMPORT] Navigating to EroScripts page..."
            )

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000
            )

            if response is None:
                raise RuntimeError(
                    "EroScripts did not return a page response."
                )

            print(
                "[IMPORT] Navigation complete."
            )

            print(
                f"[IMPORT] Current page: {page.url}"
            )

            print(
                f"[IMPORT] HTTP status: {response.status}"
            )

            if response.status >= 400:
                raise RuntimeError(
                    f"EroScripts returned HTTP "
                    f"{response.status}."
                )

            print(
                "[IMPORT] Checking login state..."
            )

            if "/login" in page.url.lower():
                raise RuntimeError(
                    "The EroScripts session has expired. "
                    "Please log in again through "
                    "Settings -> EroScripts Login."
                )

            print(
                "[IMPORT] Login check passed."
            )

            print(
                "[IMPORT] Looking for .funscript links..."
            )

            candidates = self.find_script_links(
                page,
                url
            )

            script_info = self.choose_final_script_candidate(
                candidates
            )

            if script_info is None:
                raise RuntimeError(
                    "Could not find a .funscript "
                    "download link on the EroScripts page."
                )

            script_url, filename = script_info

            print(
                "\n[IMPORT] Selected script:"
            )

            print(
                f"[IMPORT] Filename: {filename}"
            )

            print(
                f"[IMPORT] URL: {script_url}"
            )

            print(
                "[IMPORT] Downloading selected script..."
            )

            content = self.download_script(
                page,
                script_url
            )

            print(
                f"[IMPORT] Download complete: "
                f"{len(content):,} bytes"
            )

            destination.mkdir(
                parents=True,
                exist_ok=True
            )

            output_path = destination / filename

            print(
                f"[IMPORT] Saving script: {output_path}"
            )

            output_path.write_bytes(
                content
            )

            print(
                "[IMPORT] Script saved successfully."
            )

            print(
                "[IMPORT] Extracting topic title..."
            )

            title = self.extract_topic_title(
                page
            )

            print(
                f"[IMPORT] Title: {title}"
            )

            print(
                "[IMPORT] Extracting metadata..."
            )

            metadata = self.extract_metadata(
                page,
                title
            )

            content_hash = hashlib.sha256(
                content
            ).hexdigest()

            thumbnail_url = self.extract_eroscripts_thumbnail(page, script_url)

            print(
                f"[IMPORT] SHA256: {content_hash}"
            )

            print(
                "[IMPORT] Import completed successfully."
            )

            return EroScriptsImportResult(
                page_url=url,
                script_url=script_url,
                filename=filename,
                content=content,
                title=title,
                creator=metadata["creator"],
                tags=metadata["tags"],
                video_site=metadata["video_site"],
                video_title=metadata["video_title"],
                video_url=metadata["video_url"],
                video_candidates=self.extract_video_candidates(page),
                thumbnail_url=thumbnail_url,
                duration=metadata["duration"],
                action_count=metadata["action_count"],
                average_speed=metadata["average_speed"],
                content_hash=content_hash
            )

        except Exception as exc:

            print(
                "\n[IMPORT] ERROR:"
            )

            print(
                f"[IMPORT] {type(exc).__name__}: {exc}"
            )

            raise

        finally:

            print(
                "[IMPORT] Closing browser page..."
            )

            try:
                page.close()
            except Exception:
                pass

    @staticmethod
    def clean_url(
        url: str
    ) -> str:

        url = url.strip()

        if (
            url.startswith("[")
            and "](" in url
            and url.endswith(")")
        ):
            url = url.split(
                "](",
                1
            )[1][:-1]

        return url.strip(
            "\"' "
        )

    @staticmethod
    def extract_topic_title(
        page
    ) -> str:

        headings = page.locator(
            "h1"
        )

        ignored_titles = {
            "reputable script creators",
            "so we revamped it with automation",
            "how does this work?",
        }

        count = headings.count()

        for index in range(count):

            try:

                text = headings.nth(
                    index
                ).inner_text(
                    timeout=5000
                ).strip()

            except Exception:

                continue

            if not text:
                continue

            if text.lower() in ignored_titles:
                continue

            return text

        try:

            title = page.title().strip()

        except Exception:

            title = ""

        title = re.sub(
            r"\s*[-|]\s*Scripts\s*/.*$",
            "",
            title,
            flags=re.IGNORECASE
        )

        if title:
            return title

        return "Untitled Script"

    @staticmethod
    def find_script_links(
        page,
        page_url: str
    ) -> list[tuple[str, str]]:

        print(
            "[IMPORT] Scanning page links..."
        )

        links = page.locator(
            "a[href]"
        )

        count = links.count()

        print(
            f"[IMPORT] Found {count} links on page."
        )

        # Use a dictionary keyed by URL.
        #
        # This removes duplicate occurrences of the
        # exact same attachment while preserving order.
        #
        # Important:
        # EroScripts pages can contain multiple versions
        # of the same .funscript with the same filename but
        # different attachment URLs.
        #
        # Example:
        #
        # old script:
        #   /uploads/short-url/AAAA.funscript
        #
        # updated script:
        #   /uploads/short-url/BBBB.funscript
        #
        # We want to keep BOTH.
        candidates = {}

        for index in range(count):

            try:

                link = links.nth(
                    index
                )

                href = link.get_attribute(
                    "href",
                    timeout=5000
                )

                if not href:
                    continue

                if ".funscript" not in href.lower():
                    continue

                text = link.inner_text(
                    timeout=5000
                ).strip()

            except Exception:

                continue

            if not text:
                continue

            filename = (
                EroScriptsImporter.clean_filename(
                    text
                )
            )

            if not filename:
                continue

            script_url = urljoin(
                page_url,
                href
            )

            # Deduplicate exact duplicate links.
            if script_url in candidates:
                continue

            candidates[script_url] = filename

            print(
                f"[IMPORT] Found unique script candidate: "
                f"{filename}"
            )

            print(
                f"[IMPORT] Candidate URL: "
                f"{script_url}"
            )

        if not candidates:

            print(
                "[IMPORT] No .funscript candidates found."
            )

            return []

        candidate_list = list(
            candidates.items()
        )

        print(
            "\n[IMPORT] Unique .funscript candidates:"
        )

        for index, (
            script_url,
            filename
        ) in enumerate(
            candidate_list,
            start=1
        ):

            print(
                f"[IMPORT]   {index}. {filename}"
            )

            print(
                f"[IMPORT]      {script_url}"
            )

        # Keep every unique candidate. The caller may choose one
        # candidate explicitly, while the multi-script importer uses
        # this complete list.
        return candidate_list

    @staticmethod
    def choose_final_script_candidate(
        candidates: list[tuple[str, str]]
    ) -> tuple[str, str] | None:

        if not candidates:
            return None

        non_music = [
            item for item in candidates
            if "(music)" not in item[1].lower()
        ]

        if non_music:
            candidates = non_music

        return candidates[-1]

    def download_script(
        self,
        page,
        script_url: str
    ) -> bytes:

        print(
            "[IMPORT] Starting .funscript HTTP download..."
        )

        print(
            f"[IMPORT] Download URL: {script_url}"
        )

        try:

            response = page.request.get(
                script_url,
                timeout=30000
            )

        except Exception as exc:

            raise RuntimeError(
                "Timed out or failed while downloading "
                f"the .funscript: {exc}"
            ) from exc

        print(
            f"[IMPORT] Script HTTP status: "
            f"{response.status}"
        )

        if not response.ok:

            raise RuntimeError(
                f"Funscript download failed "
                f"with HTTP {response.status}."
            )

        content = response.body()

        if not content:

            raise RuntimeError(
                "EroScripts returned an empty "
                "funscript file."
            )

        return content

    @staticmethod
    def clean_filename(
        text: str
    ) -> str:

        match = re.search(
            r"([^\r\n]+?\.funscript)",
            text,
            flags=re.IGNORECASE
        )

        if match:

            filename = match.group(
                1
            ).strip()

        else:

            filename = text.strip()

        filename = re.sub(
            r'[<>:"/\\|?*]',
            "",
            filename
        )

        filename = re.sub(
            r"[\x00-\x1f]",
            "",
            filename
        )

        filename = re.sub(
            r"\s+",
            " ",
            filename
        ).strip()

        filename = filename.rstrip(
            ". "
        )

        if not filename:
            return ""

        if not filename.lower().endswith(
            ".funscript"
        ):
            filename += ".funscript"

        return filename

    @staticmethod
    def extract_topic_tags(page, title: str) -> list[str]:
        """Extract only the topic's explicit /tag/ links, not navigation/sidebar tags."""
        def clean(value: str) -> str:
            value = re.sub(r"<[^>]+>", "", value or "")
            value = (
                value.replace("&amp;", "&")
                .replace("&quot;", '"')
                .replace("&#39;", "'")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
            )
            return re.sub(r"\s+", " ", value).strip()

        ignored = {"tags", "all tags"}

        # Discourse renders the topic title and its tag chips in a shared
        # topic-header region. Walk upward from the exact title element and
        # choose the smallest ancestor containing explicit /tag/ links.
        try:
            title_loc = page.locator("a, h1").filter(has_text=title)
            if title_loc.count():
                node = title_loc.first
                for _ in range(7):
                    node = node.locator("xpath=..")
                    if node.count() == 0:
                        break
                    tags = []
                    links = node.locator('a[href*="/tag/"]')
                    for i in range(links.count()):
                        tag = clean(links.nth(i).inner_text(timeout=2000) or "")
                        if tag and tag.lower() not in ignored and len(tag) <= 50:
                            if tag not in tags:
                                tags.append(tag)
                    if tags:
                        return tags
        except Exception:
            pass

        # Structured fallback: only anchors whose href is an explicit /tag/
        # URL and which occur near the first exact topic-title occurrence.
        try:
            html_text = page.content()
            title_match = re.search(re.escape(title), html_text, flags=re.I)
            if title_match:
                tail = html_text[title_match.end():]
                article_start = re.search(r"<article\b", tail, flags=re.I)
                region = tail[:article_start.start()] if article_start else tail[:12000]
                matches = re.findall(
                    r'<a[^>]+href=["\'][^"\']*/tag/[^"\']*["\'][^>]*>(.*?)</a>',
                    region, flags=re.I | re.S
                )
                tags = []
                for inner in matches:
                    tag = clean(inner)
                    if tag and tag.lower() not in ignored and len(tag) <= 50 and tag not in tags:
                        tags.append(tag)
                return tags
        except Exception:
            pass
        return []

    @staticmethod
    def _extract_video_id_from_url(video_url: str | None) -> str | None:
        if not video_url:
            return None
        parsed = urlparse(video_url)
        path = parsed.path.rstrip("/")
        host = (parsed.hostname or "").lower().removeprefix("www.")
        patterns = []
        if host == "spankbang.com":
            patterns.append(r"/([A-Za-z0-9_-]+)/video(?:/|$)")
        if host == "eporner.com":
            patterns.append(r"/video-([A-Za-z0-9_-]+)(?:/|$)")
        patterns.extend((
            r"/video/(\d+)(?:/|$)",
            r"/video/([A-Za-z0-9_-]+)(?:/|$)",
            r"/videos?/([A-Za-z0-9_-]+)(?:/|$)",
            r"/v/([A-Za-z0-9_-]+)(?:/|$)",
        ))
        if host == "pmvhaven.com":
            patterns.insert(0, r"/video/.+_([A-Za-z0-9]+)(?:/|$)")
        for pattern in patterns:
            match = re.search(pattern, path, re.I)
            if match:
                return match.group(1)
        for key in ("video", "video_id", "id"):
            match = re.search(r"(?:^|&)" + re.escape(key) + r"=([^&]+)", parsed.query, re.I)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _common_post_ancestor(anchor):
        """Find a compact Discourse post/article ancestor for an attachment link."""
        node = anchor
        best = None
        for _ in range(8):
            try:
                node = node.locator("xpath=..")
                if node.count() == 0:
                    break
                html_text = node.evaluate("el => el.outerHTML") or ""
                if re.search(r"https?://", html_text, re.I) and (
                    re.search(r"funscript", html_text, re.I)
                    or re.search(r"video", html_text, re.I)
                ):
                    best = node
                if re.search(r"<(article|div)[^>]+(?:data-post-id|class=\"[^\"]*(?:topic-post|post-stream|cooked)[^\"]*)", html_text, re.I):
                    return node
            except Exception:
                continue
        return best

    @classmethod
    def extract_eroscripts_thumbnail(cls, page, script_url: str) -> str | None:
        """Return a real EroScripts preview image, excluding blob heatmaps/icons."""
        try:
            loc = page.locator(f'a[href="{script_url}"]')
            if loc.count() == 0:
                return None
            container = cls._common_post_ancestor(loc.first)
            if container is None:
                return None
            images = container.locator("img[src]")
            candidates = []
            for i in range(images.count()):
                img = images.nth(i)
                src = img.get_attribute("src") or ""
                if not src or src.startswith(("blob:", "data:")):
                    continue
                lower = src.lower()
                if any(token in lower for token in ("bookmark_tabs", "emoji", "heatmap", "avatar", "icon")):
                    continue
                src = urljoin(page.url, src)
                if re.match(r"^https?://", src, re.I):
                    candidates.append(src)
            return candidates[0] if candidates else None
        except Exception:
            return None

    @staticmethod
    def extract_video_for_script(page, script_url: str, filename: str) -> dict | None:
        """Find the video link(s) belonging to the same Discourse post as a script."""
        try:
            loc = page.locator(f'a[href="{script_url}"]')
            if loc.count() == 0:
                loc = page.locator("a").filter(has_text=filename)
            if loc.count() == 0:
                return None

            container = EroScriptsImporter._common_post_ancestor(loc.first)
            if container is None:
                return None

            links = container.locator("a[href]")
            preferred = []
            fallback = []
            supported_hosts = {
                "eporner.com", "rule34video.com", "noodledude.io",
                "spankbang.com", "pmvhaven.com",
            }
            for i in range(links.count()):
                link = links.nth(i)
                href = link.get_attribute("href") or ""
                if not href or ".funscript" in href.lower():
                    continue
                full_url = urljoin(page.url, href)
                if not re.match(r"^https?://", full_url, re.I):
                    continue
                host = (urlparse(full_url).hostname or "").lower().removeprefix("www.")
                if host in {"discuss.eroscripts.com", "eroscripts.com"}:
                    continue
                link_text = " ".join((link.inner_text(timeout=2000) or "").split()) or None
                candidate = {
                    "site": host,
                    "title": link_text,
                    "url": full_url,
                    "source": "script-post-block",
                }
                if host in supported_hosts or host.endswith(".noodledude.io"):
                    preferred.append(candidate)
                elif link_text and re.match(r"https?://", link_text, re.I):
                    preferred.append(candidate)
                else:
                    fallback.append(candidate)

            return (preferred + fallback)[0] if (preferred or fallback) else None
        except Exception:
            return None

    @staticmethod
    def extract_video_candidates(page) -> list[dict]:
        """Extract external video links from actual EroScripts post blocks only."""
        candidates = []
        try:
            scripts = page.locator('a[href*=".funscript"]')
            for i in range(scripts.count()):
                loc = scripts.nth(i)
                container = EroScriptsImporter._common_post_ancestor(loc)
                if container is None:
                    continue
                links = container.locator("a[href]")
                for j in range(links.count()):
                    link = links.nth(j)
                    href = link.get_attribute("href") or ""
                    if not href or ".funscript" in href.lower():
                        continue
                    full_url = urljoin(page.url, href)
                    parsed = urlparse(full_url)
                    host = (parsed.hostname or "").lower().removeprefix("www.")
                    if not host or host in {"discuss.eroscripts.com", "eroscripts.com"}:
                        continue
                    text = " ".join((link.inner_text(timeout=2000) or "").split()) or None
                    item = {"site": host, "title": text, "url": full_url}
                    if item not in candidates:
                        candidates.append(item)
        except Exception:
            return []
        return candidates

    @staticmethod
    def extract_metadata(
        page,
        title: str
    ) -> dict:

        try:

            text = page.locator(
                "body"
            ).inner_text(
                timeout=10000
            )

        except Exception:

            text = ""

        creator = None

        # -------------------------------------------------
        # Creator
        # -------------------------------------------------

        creator_match = re.search(
            r"post by\s+([^\s]+)\s+on\s+",
            text,
            flags=re.IGNORECASE
        )

        if creator_match:

            creator = creator_match.group(
                1
            )

        # -------------------------------------------------
        # Topic tags
        # -------------------------------------------------

        tags = (
            EroScriptsImporter.extract_topic_tags(
                page,
                title
            )
        )

        # -------------------------------------------------
        # Video information
        # -------------------------------------------------

        video_site = None
        video_title = None
        video_url = None

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        video_index = -1

        for index, line in enumerate(
            lines
        ):

            if line.lower() == "video link":

                video_index = index

                break

        if video_index >= 0:

            remaining = lines[
                video_index + 1:
            ]

            if remaining:

                candidate = remaining[0]

                if (
                    "." in candidate
                    and " " not in candidate
                ):

                    video_site = candidate

            if len(remaining) >= 2:

                video_title = remaining[1]

        # -------------------------------------------------
        # Video URL
        # -------------------------------------------------

        if video_title:

            try:

                html = page.content()

                escaped_title = re.escape(
                    video_title
                )

                pattern = (
                    r'href=["\']([^"\']+)["\'][^>]*>'
                    r'[^<]*'
                    + escaped_title
                )

                match = re.search(
                    pattern,
                    html,
                    flags=re.IGNORECASE
                )

                if match:

                    video_url = urljoin(
                        page.url,
                        match.group(1)
                    )

            except Exception:

                video_url = None

        # -------------------------------------------------
        # Script statistics
        # -------------------------------------------------

        duration = None
        action_count = None
        average_speed = None

        stats_match = re.search(
            r"Duration:\s*([0-9:]+)"
            r"\s*\|\s*Average Speed:\s*([\d.]+)"
            r"\s*\|\s*Actions:\s*([\d,]+)",
            text,
            flags=re.IGNORECASE
        )

        if stats_match:

            duration = (
                stats_match.group(1)
            )

            try:

                average_speed = float(
                    stats_match.group(2)
                )

            except ValueError:

                average_speed = None

            try:

                action_count = int(
                    stats_match.group(3)
                    .replace(",", "")
                )

            except ValueError:

                action_count = None

        return {
            "creator": creator,
            "tags": tags,
            "video_site": video_site,
            "video_title": video_title,
            "video_url": video_url,
            "duration": duration,
            "action_count": action_count,
            "average_speed": average_speed,
        }