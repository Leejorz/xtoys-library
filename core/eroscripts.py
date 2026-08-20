from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse
from core.pixeldrain import is_pixeldrain_host, resolve_pixeldrain_url
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

    def discover_from_url(self, url: str) -> list[dict]:
        """Discover funscript attachments without downloading or writing files."""
        print("\n[IMPORT] Cleaning EroScripts URL...")
        url = self.clean_url(url)
        print(f"[IMPORT] URL: {url}")
        if not url:
            raise ValueError("EroScripts URL cannot be empty.")

        page = self.context.new_page()
        try:
            print("[IMPORT] Opening browser page for discovery...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None:
                raise RuntimeError("EroScripts did not return a page response.")
            print(f"[IMPORT] HTTP status: {response.status}")
            if response.status >= 400:
                raise RuntimeError(f"EroScripts returned HTTP {response.status}.")
            if "/login" in page.url.lower():
                raise RuntimeError("The EroScripts session has expired. Please log in again through Settings -> EroScripts Login.")

            candidates = self.find_script_links(page, url)
            if not candidates:
                raise RuntimeError("Could not find a .funscript download link on the EroScripts page.")

            print(f"[IMPORT] Discovery complete: {len(candidates)} funscript candidate(s). No files downloaded.")
            return [
                {"filename": filename, "script_url": script_url, "index": index}
                for index, (script_url, filename) in enumerate(candidates)
            ]
        finally:
            try:
                page.close()
            except Exception:
                pass

    @staticmethod
    def _select_current_candidates(
        candidates: list[tuple[str, str]],
        selected: list[dict] | list[str]
    ) -> list[tuple[str, str]]:
        """Map discovery selections onto a freshly loaded page.

        Blob URLs are page-scoped and can change between discovery and download,
        so selection is matched by filename/occurrence rather than stale blob URL.
        """
        wanted = []
        for item in selected or []:
            if isinstance(item, dict):
                wanted.append(str(item.get("filename") or ""))
            else:
                wanted.append(str(item))

        remaining = list(candidates)
        chosen = []
        for filename in wanted:
            match_index = None
            for i, candidate in enumerate(remaining):
                if candidate[1] == filename:
                    match_index = i
                    break
            if match_index is not None:
                chosen.append(remaining.pop(match_index))
        return chosen

    def import_selected_from_url(
        self,
        url: str,
        destination: Path,
        selected: list[dict] | list[str],
        write_files: bool = False,
    ) -> list[EroScriptsImportResult]:
        """Download only user-selected funscripts from an EroScripts page."""
        print("\n[IMPORT] Cleaning EroScripts URL...")
        url = self.clean_url(url)
        if not url:
            raise ValueError("EroScripts URL cannot be empty.")
        if not selected:
            return []

        page = self.context.new_page()
        try:
            print("[IMPORT] Opening browser page for selected downloads...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if response is None:
                raise RuntimeError("EroScripts did not return a page response.")
            if response.status >= 400:
                raise RuntimeError(f"EroScripts returned HTTP {response.status}.")
            if "/login" in page.url.lower():
                raise RuntimeError("The EroScripts session has expired. Please log in again through Settings -> EroScripts Login.")

            current_candidates = self.find_script_links(page, url)
            candidates = self._select_current_candidates(current_candidates, selected)
            if not candidates:
                raise RuntimeError("None of the selected funscripts could be found after reopening the EroScripts page.")

            title = self.extract_topic_title(page)
            metadata = self.extract_metadata(page, title)
            video_candidates = self.extract_video_candidates(page)
            diagnostic_path = self._write_diagnostic_report(page, url, candidates, video_candidates)
            print(f"[IMPORT] Diagnostic report: {diagnostic_path.resolve()}")

            if write_files:
                destination.mkdir(parents=True, exist_ok=True)

            results = []
            failures = []
            for number, (script_url, filename) in enumerate(candidates, start=1):
                print(f"\n[IMPORT] Downloading selected script {number}/{len(candidates)}: {filename}")
                try:
                    content = self.download_script(page, script_url)
                except Exception as exc:
                    failures.append(f"{filename}: {exc}")
                    print(f"[IMPORT] Skipping failed script: {filename}: {exc}")
                    continue

                if write_files:
                    output_path = destination / filename
                    output_path.write_bytes(content)
                    print(f"[IMPORT] Saved: {output_path}")

                content_hash = hashlib.sha256(content).hexdigest()
                matched_video = self.extract_video_for_script(page, script_url, filename)
                result_candidates = [matched_video] if matched_video else []
                if matched_video:
                    matched_video = dict(matched_video)
                    detected_id = matched_video.get("video_id") or self._extract_video_id_from_url(matched_video.get("url"))
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

            if failures and not results:
                raise RuntimeError("All selected funscripts failed to download:\n" + "\n".join(failures))
            if failures:
                print("[IMPORT] Some selected scripts failed and were skipped:")
                for failure in failures:
                    print(f"[IMPORT]   {failure}")
            return results
        finally:
            print("[IMPORT] Closing browser page...")
            try:
                page.close()
            except Exception:
                pass

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
                    detected_id = matched_video.get("video_id") or self._extract_video_id_from_url(matched_video.get("url"))
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
    def _expand_collapsed_script_sections(page) -> int:
        """Open collapsed Discourse <details> blocks before scanning attachments.

        Hidden <details> content is normally present in the DOM, but opening the
        blocks makes extraction reliable across Discourse/theme variations that
        defer or rewrite attachment markup until the section is expanded.
        """
        expanded = 0
        try:
            expanded = page.locator("details:not([open])").count()
            if expanded:
                page.locator("details:not([open])").evaluate_all(
                    "els => els.forEach(el => { el.open = true; el.setAttribute('open', ''); })"
                )
                page.wait_for_timeout(150)
        except Exception:
            pass
        return expanded


    @staticmethod
    def _hydrate_full_topic(page) -> None:
        """Scroll through the whole Discourse topic so lazy attachment widgets hydrate.

        Long EroScripts topics can defer creating attachment/blob anchors until their
        post region has entered the viewport. Walk the page from top to bottom, pausing
        briefly between viewport-sized jumps, then return to the top before scanning.
        """
        try:
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(100)
            page.evaluate("""async () => {
                const step = Math.max(400, Math.floor(window.innerHeight * 0.8));
                let lastHeight = 0;
                let stablePasses = 0;
                for (let guard = 0; guard < 250; guard++) {
                    const height = Math.max(
                        document.body ? document.body.scrollHeight : 0,
                        document.documentElement ? document.documentElement.scrollHeight : 0
                    );
                    if (height === lastHeight) stablePasses++; else stablePasses = 0;
                    lastHeight = height;
                    const maxY = Math.max(0, height - window.innerHeight);
                    const nextY = Math.min(maxY, window.scrollY + step);
                    window.scrollTo(0, nextY);
                    await new Promise(resolve => setTimeout(resolve, 120));
                    if (nextY >= maxY && stablePasses >= 2) break;
                }
                window.scrollTo(0, 0);
            }""")
            page.wait_for_timeout(200)
        except Exception:
            pass

    @staticmethod
    def _looks_generated_script_filename(filename: str) -> bool:
        """Reject obvious Discourse/browser-generated attachment tokens.

        Some blob-backed attachments expose an internal random identifier in the
        download attribute (for example a 25+ character alphanumeric token with
        ``.funscript`` appended). Those are not filenames shown by the post and
        should never be offered to the user as separate scripts.
        """
        stem = re.sub(r"\.funscript$", "", filename or "", flags=re.IGNORECASE)
        return bool(
            len(stem) >= 20
            and re.fullmatch(r"[A-Za-z0-9]+", stem)
            and any(ch.islower() for ch in stem)
            and any(ch.isupper() for ch in stem)
            and any(ch.isdigit() for ch in stem)
        )

    @staticmethod
    def _script_link_filename(href: str | None, text: str | None,
                              download: str | None = None,
                              title: str | None = None) -> str | None:
        """Return a trustworthy .funscript filename advertised by an anchor.

        For normal Discourse upload links, the download attribute can contain the
        original filename. For browser ``blob:`` links, however, that attribute
        may instead contain a generated internal token. Blob attachments therefore
        prefer only human-facing text/title metadata and ignore generated names.
        """
        is_blob = str(href or "").lower().startswith("blob:")
        values = [text, title] if is_blob else [text, download, title, href]
        for value in values:
            if not value:
                continue
            match = re.search(r"([^\\/\r\n<>:\"|?*]+?\.funscript)(?:\b|$|[?#])",
                              str(value), flags=re.IGNORECASE)
            if match:
                cleaned = EroScriptsImporter.clean_filename(match.group(1))
                if cleaned and not EroScriptsImporter._looks_generated_script_filename(cleaned):
                    return cleaned
        return None

    @staticmethod
    def _find_script_anchor(page, script_url: str, filename: str):
        """Find an attachment anchor by resolved URL or advertised filename."""
        try:
            links = page.locator("a[href]")
            wanted = (filename or "").strip().lower()
            for i in range(links.count()):
                link = links.nth(i)
                try:
                    href = link.get_attribute("href") or ""
                    full_url = urljoin(page.url, href)
                    if full_url == script_url:
                        return link
                    text = link.inner_text(timeout=1500) or ""
                    download = link.get_attribute("download") or ""
                    title = link.get_attribute("title") or ""
                    advertised = EroScriptsImporter._script_link_filename(
                        href, text, download, title
                    )
                    if advertised and advertised.lower() == wanted:
                        return link
                except Exception:
                    continue
        except Exception:
            pass
        return None

    @staticmethod
    def find_script_links(
        page,
        page_url: str
    ) -> list[tuple[str, str]]:

        print("[IMPORT] Expanding collapsed script sections...")
        expanded = EroScriptsImporter._expand_collapsed_script_sections(page)
        if expanded:
            print(f"[IMPORT] Expanded {expanded} collapsed section(s).")

        print("[IMPORT] Hydrating lazy-loaded topic content...")
        EroScriptsImporter._hydrate_full_topic(page)

        # Scrolling can cause Discourse to instantiate additional collapsed blocks.
        expanded_after_scroll = EroScriptsImporter._expand_collapsed_script_sections(page)
        if expanded_after_scroll:
            print(f"[IMPORT] Expanded {expanded_after_scroll} additional collapsed section(s).")
            page.wait_for_timeout(150)

        print("[IMPORT] Scanning page links...")

        links = page.locator("a[href]")
        count = links.count()

        print(f"[IMPORT] Found {count} links on page.")

        # Key by resolved URL so duplicate appearances of the exact same
        # attachment are removed while distinct versions remain separate.
        candidates = {}

        for index in range(count):
            try:
                link = links.nth(index)
                href = link.get_attribute("href", timeout=5000)
                if not href:
                    continue

                text = (link.inner_text(timeout=5000) or "").strip()
                download = (link.get_attribute("download") or "").strip()
                title = (link.get_attribute("title") or "").strip()
                aria_label = (link.get_attribute("aria-label") or "").strip()
                data_filename = (link.get_attribute("data-filename") or "").strip()

                # Important: Discourse attachments can use a short /uploads/
                # href with no extension. Treat human-facing filename metadata
                # as authoritative when it advertises a .funscript. Blob-backed
                # links sometimes put the real filename in a sibling/parent
                # label while their own download attribute contains only a
                # generated token, so recover from the nearest attachment text
                # only after direct metadata has been exhausted.
                filename = EroScriptsImporter._script_link_filename(
                    href, text, download, title
                )
                if not filename:
                    for advertised_text in (aria_label, data_filename):
                        filename = EroScriptsImporter._script_link_filename(
                            href, advertised_text, None, None
                        )
                        if filename:
                            break

                if not filename and str(href).lower().startswith("blob:"):
                    nearby_values = []
                    for xpath in ("xpath=..", "xpath=../.."):
                        try:
                            nearby = " ".join(
                                (link.locator(xpath).inner_text(timeout=1500) or "").split()
                            )
                            if nearby and nearby not in nearby_values:
                                nearby_values.append(nearby)
                        except Exception:
                            pass

                    for nearby in nearby_values:
                        # A local attachment wrapper can contain both the
                        # generated blob token and the visible real filename.
                        # Extract every .funscript-looking name and accept the
                        # first non-generated one.
                        for match in re.finditer(
                            r"([^\/\r\n<>:\"|?*]+?\.funscript)(?:\b|$|[?#])",
                            nearby,
                            flags=re.IGNORECASE,
                        ):
                            candidate_name = EroScriptsImporter.clean_filename(match.group(1))
                            if (
                                candidate_name
                                and not EroScriptsImporter._looks_generated_script_filename(candidate_name)
                            ):
                                filename = candidate_name
                                break
                        if filename:
                            break

                if not filename:
                    continue
            except Exception:
                continue

            script_url = urljoin(page_url, href)

            if script_url in candidates:
                continue

            candidates[script_url] = filename

            print(f"[IMPORT] Found unique script candidate: {filename}")
            print(f"[IMPORT] Candidate URL: {script_url}")

        if not candidates:
            print("[IMPORT] No .funscript candidates found.")
            return []

        candidate_list = list(candidates.items())

        print("\n[IMPORT] Unique .funscript candidates:")
        for index, (script_url, filename) in enumerate(candidate_list, start=1):
            print(f"[IMPORT]   {index}. {filename}")
            print(f"[IMPORT]      {script_url}")

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

        if str(script_url).lower().startswith("blob:"):
            print("[IMPORT] Browser blob URL detected; reading attachment inside the EroScripts page...")
            try:
                values = page.evaluate(
                    """async (url) => {
                        const response = await fetch(url);
                        if (!response.ok) throw new Error(`Blob fetch failed: ${response.status}`);
                        const buffer = await response.arrayBuffer();
                        return Array.from(new Uint8Array(buffer));
                    }""",
                    script_url,
                )
                content = bytes(values or [])
            except Exception as exc:
                raise RuntimeError(
                    "Timed out or failed while reading the browser-only .funscript attachment: "
                    f"{exc}"
                ) from exc
            if not content:
                raise RuntimeError("EroScripts returned an empty funscript file.")
            print(f"[IMPORT] Browser blob download complete: {len(content):,} bytes")
            return content

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
        if is_pixeldrain_host(host):
            resolved = resolve_pixeldrain_url(video_url)
            return (resolved or {}).get("video_id")
        patterns = []
        if host == "spankbang.com":
            patterns.append(r"/([A-Za-z0-9_-]+)/video(?:/|$)")
        if host == "eporner.com":
            patterns.append(r"/video-([A-Za-z0-9_-]+)(?:/|$)")
        if host == "hmvmania.com":
            match = re.search(r"/video/([^/]+)(?:/|$)", path, re.I)
            if match:
                value = match.group(1)
                fragment = parsed.fragment or ""
                frag_query = fragment.split("?", 1)[1] if "?" in fragment else fragment
                item = re.search(r"(?:^|&)videoId=([^&]+)", frag_query, re.I)
                return value + ("#videoId=" + item.group(1) if item else "")
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
            loc = cls._find_script_anchor(page, script_url, "")
            if loc is None:
                return None
            container = cls._common_post_ancestor(loc)
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
        """Find the nearest supported video link preceding a script in its Discourse post."""
        try:
            loc = EroScriptsImporter._find_script_anchor(page, script_url, filename)
            if loc is None:
                return None

            supported_hosts = {
                "eporner.com", "rule34video.com", "noodledude.io",
                "spankbang.com", "pmvhaven.com", "hmvmania.com", "pixeldrain.com",
            }
            image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif")

            try:
                prior_links = loc.evaluate("""el => {
                    const root = el.closest('article') || el.closest('.topic-post') || el.closest('.cooked') || el.parentElement;
                    if (!root) return [];
                    const links = Array.from(root.querySelectorAll('a[href]'));
                    const before = [];
                    for (const a of links) {
                        if (a === el || a.contains(el) || el.contains(a)) continue;
                        const pos = a.compareDocumentPosition(el);
                        if (pos & Node.DOCUMENT_POSITION_FOLLOWING) {
                            before.push({href: a.href || a.getAttribute('href') || '', text: (a.innerText || a.textContent || '').trim()});
                        }
                    }
                    return before.reverse();
                }""") or []
            except Exception:
                prior_links = []

            if not prior_links:
                container = EroScriptsImporter._common_post_ancestor(loc)
                if container is not None:
                    links = container.locator("a[href]")
                    for i in range(links.count() - 1, -1, -1):
                        link = links.nth(i)
                        prior_links.append({
                            "href": link.get_attribute("href") or "",
                            "text": " ".join((link.inner_text(timeout=2000) or "").split()),
                        })

            for raw in prior_links:
                href = (raw.get("href") or "").strip()
                if not href or ".funscript" in href.lower():
                    continue
                full_url = urljoin(page.url, href)
                if not re.match(r"^https?://", full_url, re.I):
                    continue
                parsed = urlparse(full_url)
                host = (parsed.hostname or "").lower().removeprefix("www.")
                path_lower = (parsed.path or "").lower()
                if not host or host in {"discuss.eroscripts.com", "eroscripts.com"}:
                    continue
                if path_lower.endswith(image_exts):
                    continue

                text = " ".join((raw.get("text") or "").split()) or None
                if is_pixeldrain_host(host):
                    resolved = resolve_pixeldrain_url(full_url) or {}
                    return {
                        "site": "pixeldrain.com",
                        "title": resolved.get("title") or text,
                        "url": full_url,
                        "video_id": resolved.get("video_id"),
                        "source": "nearest-preceding-video-link",
                    }

                if host in supported_hosts or host.endswith(".noodledude.io"):
                    return {
                        "site": host,
                        "title": text,
                        "url": full_url,
                        "video_id": EroScriptsImporter._extract_video_id_from_url(full_url),
                        "source": "nearest-preceding-video-link",
                    }

            return None
        except Exception:
            return None

    @staticmethod
    def extract_video_candidates(page) -> list[dict]:
        """Extract external video links from actual EroScripts post blocks only."""
        candidates = []
        try:
            EroScriptsImporter._expand_collapsed_script_sections(page)
            script_pairs = EroScriptsImporter.find_script_links(page, page.url)
            for script_url, filename in script_pairs:
                loc = EroScriptsImporter._find_script_anchor(page, script_url, filename)
                if loc is None:
                    continue
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
                    if is_pixeldrain_host(host):
                        resolved = resolve_pixeldrain_url(full_url) or {}
                        item = {
                            "site": "pixeldrain.com",
                            "title": resolved.get("title") or text,
                            "url": full_url,
                            "video_id": resolved.get("video_id"),
                        }
                    else:
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