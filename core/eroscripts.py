from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin
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
                results.append(EroScriptsImportResult(
                    page_url=url, script_url=script_url, filename=filename,
                    content=content, title=title, creator=metadata["creator"],
                    tags=metadata["tags"], video_candidates=result_candidates,
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
    def extract_topic_tags(
        page,
        title: str
    ) -> list[str]:

        tags = []

        try:

            # Get the complete HTML once.
            html = page.content()

            # Locate the actual topic title in the HTML.
            title_pattern = re.escape(
                title
            )

            title_match = re.search(
                title_pattern,
                html,
                flags=re.IGNORECASE
            )

            if not title_match:
                return []

            # Look backward from the title for the topic
            # header area. Discourse normally renders the
            # topic tags near the topic title.
            #
            # 25,000 characters is deliberately generous
            # because EroScripts has a large header.

            start = max(
                0,
                title_match.start() - 25000
            )

            header_html = html[
                start:title_match.end()
            ]

            # Find tag links in this header region.
            #
            # A Discourse tag link normally contains
            # /tag/<slug> in its href.

            matches = re.findall(
                r'<a[^>]+href=["\']([^"\']*/tag/[^"\']*)["\'][^>]*>'
                r'(.*?)'
                r'</a>',
                header_html,
                flags=re.IGNORECASE | re.DOTALL
            )

            for href, inner_html in matches:

                # Remove nested HTML.
                tag = re.sub(
                    r"<[^>]+>",
                    "",
                    inner_html
                )

                # Decode common HTML entities.
                tag = (
                    tag
                    .replace("&amp;", "&")
                    .replace("&quot;", '"')
                    .replace("&#39;", "'")
                    .replace("&lt;", "<")
                    .replace("&gt;", ">")
                )

                tag = re.sub(
                    r"\s+",
                    " ",
                    tag
                ).strip()

                if not tag:
                    continue

                if len(tag) > 50:
                    continue

                if tag.lower() in {
                    "tags",
                    "all tags",
                }:
                    continue

                tags.append(
                    tag
                )

        except Exception:

            return []

        # Remove duplicates while preserving order.
        return list(
            dict.fromkeys(
                tags
            )
        )

    @staticmethod
    def extract_video_for_script(page, script_url: str, filename: str) -> dict | None:
        """Find the video link belonging to one specific funscript.

        EroScripts commonly renders a PMV entry as a single <p> containing
        both the Video link and the Script link. Prefer that local relationship
        over page-wide video discovery so scripts are not assigned to the wrong
        video.
        """
        try:
            loc = page.locator(f'a[href="{script_url}"]')
            if loc.count() == 0:
                loc = page.locator("a").filter(has_text=filename)
            if loc.count() == 0:
                return None

            anchor = loc.first
            # Walk upward until we find a compact block containing a video link.
            node = anchor
            for _ in range(4):
                node = node.locator("xpath=..")
                if node.count() == 0:
                    break
                try:
                    html = node.evaluate("el => el.outerHTML") or ""
                    text = " ".join((node.inner_text(timeout=2000) or "").split())
                except Exception:
                    continue

                if not re.search(r"\bVideo\s*:", text, flags=re.IGNORECASE):
                    continue

                links = node.locator("a[href]")
                for i in range(links.count()):
                    link = links.nth(i)
                    href = link.get_attribute("href") or ""
                    if not href or ".funscript" in href.lower():
                        continue
                    full_url = urljoin(page.url, href)
                    if not re.match(r"^https?://", full_url, flags=re.IGNORECASE):
                        continue
                    link_text = " ".join((link.inner_text(timeout=2000) or "").split())
                    if not link_text:
                        link_text = None
                    site = urlparse(full_url).netloc.lower()
                    if site.startswith("www."):
                        site = site[4:]
                    return {
                        "site": site,
                        "title": link_text,
                        "url": full_url,
                        "source": "script-parent-block",
                    }
        except Exception:
            return None

        return None

    @staticmethod
    def extract_video_candidates(page) -> list[dict]:
        """Extract all visible EroScripts video-link blocks.

        This deliberately returns candidates rather than guessing a
        script-to-video relationship. The application can score a
        candidate and ask for manual input when the match is uncertain.
        """
        try:
            text = page.locator("body").inner_text(timeout=10000)
        except Exception:
            text = ""

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        blocks = []
        for i, line in enumerate(lines):
            if line.lower() != "video link":
                continue
            remaining = lines[i + 1:i + 8]
            site = None
            title = None
            for value in remaining:
                if site is None and "." in value and " " not in value and not value.startswith("http"):
                    site = value
                    continue
                if title is None and value and not value.startswith("http"):
                    title = value
                    break
            if not site:
                continue

            url = None
            try:
                html = page.content()
                if title:
                    pattern = r'href=["\']([^"\']+)["\'][^>]*>[^<]*' + re.escape(title)
                    match = re.search(pattern, html, flags=re.IGNORECASE)
                    if match:
                        url = urljoin(page.url, match.group(1))
            except Exception:
                pass

            item = {"site": site, "title": title, "url": url}
            if item not in blocks:
                blocks.append(item)

        return blocks

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