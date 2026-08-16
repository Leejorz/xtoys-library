from pathlib import Path
import json
import re
import subprocess
from urllib.parse import urlparse

from app.config import AppConfig
from app.logger import setup_logging
from storage.database import Database
from ui.menu import MainMenu
from core.scanner import LibraryScanner
from core.eroscripts import EroScriptsImporter
from core.eroscripts_auth import EroScriptsAuth
from builders.index_builder import IndexBuilder


class Application:

    # Uniform placeholder used when an embedded xToys-compatible video source
    # cannot be found. This is a real-looking source entry that conforms to
    # the normal index.json site/id/url schema; it is not a custom placeholder
    # site. The video itself is unavailable, so the script can still be used
    # while the real video is opened separately by the user.
    PLACEHOLDER_VIDEO_SITE = "spankbang.com"
    PLACEHOLDER_VIDEO_ID = "8nzm1"
    PLACEHOLDER_VIDEO_URL = "https://spankbang.com/8nzm1/video/fly+away+with+me"

    def __init__(self, root: Path | None = None):

        self.root = (
            root
            or Path(__file__).resolve().parent.parent
        )

        self.config = AppConfig.load(
            self.root / "config.json"
        )

        self.config.ensure_directories(
            self.root
        )

        self.logger = setup_logging(
            self.root
            / self.config.logs_dir
            / "manager.log"
        )

        self.database = Database(
            self.root / self.config.database
        )

        self.database.initialize()

    def run(self):

        self.logger.info(
            "Application started"
        )

        try:

            MainMenu(self).run()

        finally:

            self.database.close()

            self.logger.info(
                "Application stopped"
            )

    def rebuild_library(self):

        scanner = LibraryScanner(
            self.root / self.config.funscripts_dir
        )

        scanned = scanner.scan()

        new_count = 0
        rename_count = 0
        unchanged_count = 0

        for script in scanned:

            existing = self.database.get_script_by_hash(
                script.content_hash
            )

            if existing is None:

                self.database.add_script(
                    script.filename,
                    script.content_hash
                )

                new_count += 1

            elif existing["filename"] != script.filename:

                self.database.update_filename(
                    script.content_hash,
                    script.filename
                )

                rename_count += 1

            else:

                unchanged_count += 1

        print(
            "\nLibrary rebuilt successfully.\n"
        )

        print(
            f"Scripts found : {len(scanned)}"
        )

        print(
            f"New scripts   : {new_count}"
        )

        print(
            f"Renamed       : {rename_count}"
        )

        print(
            f"Unchanged     : {unchanged_count}"
        )

    def build_index(self):

        builder = IndexBuilder(
            self.root,
            self.database,
            self.config
        )

        output_path, count = builder.build()

        print(
            "\nIndex generated successfully.\n"
        )

        print(
            f"Videos : {count}"
        )

        print(
            f"Output : {output_path}"
        )

    def validate_library(self) -> bool:
        """
        Validate the library and optionally clean stale database
        records. This operation never deletes .funscript files.
        """
        connection = self.database.connect()
        funscripts_dir = self.root / self.config.funscripts_dir

        disk_files = {
            path.name
            for path in funscripts_dir.glob("*.funscript")
            if path.is_file()
        }

        scripts = self.database.all_scripts()
        db_filenames = {
            script["filename"]
            for script in scripts
            if script["filename"]
        }

        stale_scripts = [
            script
            for script in scripts
            if script["filename"] not in disk_files
        ]
        stale_scripts.sort(key=lambda row: (row["filename"] or "").lower())

        untracked_files = sorted(
            disk_files - db_filenames,
            key=str.lower
        )

        orphan_script_tags = connection.execute(
            """
            SELECT COUNT(*)
            FROM script_tags st
            LEFT JOIN scripts s ON s.id=st.script_id
            LEFT JOIN tags t ON t.id=st.tag_id
            WHERE s.id IS NULL OR t.id IS NULL
            """
        ).fetchone()[0]

        orphan_videos = connection.execute(
            """
            SELECT COUNT(*)
            FROM video_sources vs
            LEFT JOIN scripts s ON s.id=vs.script_id
            WHERE s.id IS NULL
            """
        ).fetchone()[0]

        orphan_threads = connection.execute(
            """
            SELECT COUNT(*)
            FROM eroscripts_threads et
            LEFT JOIN scripts s ON s.id=et.script_id
            WHERE et.script_id IS NOT NULL AND s.id IS NULL
            """
        ).fetchone()[0]

        invalid_videos = connection.execute(
            """
            SELECT COUNT(*)
            FROM video_sources
            WHERE TRIM(COALESCE(site, ''))=''
               OR TRIM(COALESCE(video_id, ''))=''
            """
        ).fetchone()[0]

        multiple_primary = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT script_id
                FROM video_sources
                WHERE is_primary=1
                GROUP BY script_id
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

        index_errors = []
        index_path = self.root / self.config.index_file

        if not index_path.exists():
            index_errors.append(
                f"Index file does not exist: {index_path}"
            )
        else:
            try:
                with index_path.open("r", encoding="utf-8") as handle:
                    index = json.load(handle)

                indexed = index.get("videos", [])
                expected = set()

                for script in scripts:
                    source = self.database.get_video_source(script["id"])
                    if source is not None:
                        expected.add((
                            source["site"] or "",
                            source["video_id"] or ""
                        ))

                actual = {
                    (video.get("site", ""), video.get("id", ""))
                    for video in indexed
                }

                # The index builder creates one video object for each script.
                # Multiple scripts may intentionally point to the same video
                # source, so compare against scripts-with-source rather than
                # the number of unique site/video-ID pairs.
                if len(indexed) != expected_count:
                    index_errors.append(
                        "Index video count does not match database: "
                        f"index={len(indexed)}, database={expected_count}"
                    )

                if actual != expected:
                    missing = sorted(expected - actual)
                    stale = sorted(actual - expected)
                    if missing:
                        index_errors.append(
                            f"Video sources missing from index: {missing}"
                        )
                    if stale:
                        index_errors.append(
                            f"Stale video sources in index: {stale}"
                        )

            except (OSError, ValueError, TypeError) as error:
                index_errors.append(
                    f"Could not read index.json: {error}"
                )

        relationship_errors = []
        if orphan_script_tags:
            relationship_errors.append(
                f"Orphaned script_tags rows: {orphan_script_tags}"
            )
        if orphan_videos:
            relationship_errors.append(
                f"Orphaned video_sources rows: {orphan_videos}"
            )
        if orphan_threads:
            relationship_errors.append(
                f"Orphaned eroscripts_threads rows: {orphan_threads}"
            )
        if invalid_videos:
            relationship_errors.append(
                f"Video sources with missing site or ID: {invalid_videos}"
            )
        if multiple_primary:
            relationship_errors.append(
                f"Scripts with multiple primary video sources: {multiple_primary}"
            )

        print("\n" + "=" * 41)
        print("        Library Validation")
        print("=" * 41)
        print()
        print(f"Scripts in database : {len(scripts)}")
        print(f"Funscripts on disk  : {len(disk_files)}")
        print(f"Missing from disk   : {len(stale_scripts)}")
        print(f"Untracked on disk   : {len(untracked_files)}")
        print(f"Orphaned relations  : {len(relationship_errors)}")

        if stale_scripts:
            print("\nStale database records detected:")
            for script in stale_scripts:
                info = self.database.get_script_cleanup_info(script["id"])
                print()
                print(f"  Script ID: {script['id']}")
                print(f"  Filename:  {script['filename']}")
                print("  Status:    File no longer exists on disk")
                print(f"  Tags:      {info['tag_count']}")
                print(f"  Videos:    {info['video_count']}")
                print(f"  Threads:   {info['thread_count']}")

        if relationship_errors:
            print("\nRelationship problems:")
            for error in relationship_errors:
                print(f"  ERROR: {error}")

        if untracked_files:
            print("\nUntracked .funscript files (not deleted):")
            for filename in untracked_files:
                print(f"  {filename}")

        if index_errors:
            print("\nIndex problems:")
            for error in index_errors:
                print(f"  ERROR: {error}")

        has_cleanup = bool(
            stale_scripts
            or orphan_script_tags
            or orphan_videos
            or orphan_threads
        )

        if has_cleanup:
            print("\nCleanup can remove stale database metadata only.")
            print(".funscript files will NOT be deleted.")
            answer = input("Perform cleanup? [y/N]: ").strip().lower()

            if answer == "y":
                removed = []
                for script in stale_scripts:
                    removed.append(
                        self.database.delete_script_and_associated_records(
                            script["id"]
                        )
                    )

                orphan_counts = self.database.cleanup_orphaned_records()

                print("\nCleanup completed successfully.")
                for item in removed:
                    print(
                        f"  Removed script {item['script_id']}: "
                        f"{item['filename']}"
                    )
                    print(
                        f"    Tags: {item['tag_count']}, "
                        f"Videos: {item['video_count']}, "
                        f"Threads: {item['thread_count']}"
                    )

                if any(orphan_counts.values()):
                    print("  Orphaned records removed:")
                    for table, count in orphan_counts.items():
                        if count:
                            print(f"    {table}: {count}")

                print("\nRun Build index.json after cleanup if the index changed.")

                # Re-run the core file/database checks without prompting.
                remaining = [
                    script
                    for script in self.database.all_scripts()
                    if script["filename"] not in disk_files
                ]

                if remaining:
                    print("\nValidation still has stale database records.")
                    return False

                print("\nCleanup validation passed.")
                return True

            print("\nCleanup cancelled. No database records were changed.")
            return False

        if relationship_errors or index_errors:
            print("\nVALIDATION FAILED.")
            return False

        print("\nVALIDATION PASSED.")
        return True

    def git_publish_preview(self) -> dict:
        """Return the current GitHub publish target and working-tree changes."""
        if not (self.root / ".git").exists():
            raise RuntimeError("This project folder is not a Git repository.")

        def run_git(*args):
            result = subprocess.run(
                ["git", *args],
                cwd=self.root,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.returncode != 0:
                details = (result.stderr or result.stdout).strip()
                raise RuntimeError(details or f"git {' '.join(args)} failed")
            return result.stdout.strip()

        branch = run_git("branch", "--show-current")
        if branch != "main":
            raise RuntimeError(
                f"GitHub publishing is configured for the main branch, but the current branch is '{branch or 'detached HEAD'}'."
            )

        remote = run_git("remote", "get-url", "origin")
        if not remote:
            raise RuntimeError("No GitHub origin remote is configured.")

        status = run_git("status", "--short")
        files = [line for line in status.splitlines() if line.strip()]
        return {"branch": branch, "remote": remote, "files": files}

    def validate_index_schema(self) -> tuple[bool, str]:
        """Run the project's index schema diagnostic and return its output."""
        result = subprocess.run(
            [
                __import__("sys").executable,
                str(self.root / "Check_index_schema.py"),
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        output = (result.stdout or "") + (result.stderr or "")
        return result.returncode == 0, output.strip()

    def git_publish(self, commit_message: str = "Update xToys Library") -> dict:
        """Validate, stage, commit, and push the current library to origin/main.

        This method is intended for the GUI publisher. It uses the repository's
        existing Git credentials/credential manager and never handles passwords
        itself.
        """
        repo = self.root

        def run_git(*args, check=True):
            result = subprocess.run(
                ["git", *args],
                cwd=repo,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
            )
            if check and result.returncode != 0:
                details = (result.stderr or result.stdout).strip()
                raise RuntimeError(details or f"git {' '.join(args)} failed")
            return result

        if not (repo / ".git").exists():
            raise RuntimeError("This project folder is not a Git repository.")

        remote = run_git("remote", "get-url", "origin").stdout.strip()
        if not remote:
            raise RuntimeError("No GitHub origin remote is configured.")

        branch = run_git("branch", "--show-current").stdout.strip()
        if branch != "main":
            raise RuntimeError(
                f"GitHub publishing is configured for the main branch, but the current branch is '{branch or 'detached HEAD'}'."
            )

        status_before = run_git("status", "--porcelain").stdout.strip()
        if not status_before:
            return {
                "remote": remote,
                "changed": False,
                "commit": "",
                "message": "Nothing to publish. The working tree is already clean.",
            }

        run_git("add", ".")

        staged = run_git("diff", "--cached", "--name-only").stdout.splitlines()
        if not staged:
            raise RuntimeError("Git found no publishable changes after staging.")

        commit = run_git("commit", "-m", commit_message)
        commit_hash = run_git("rev-parse", "--short", "HEAD").stdout.strip()

        push = run_git("push", "-u", "origin", "main")

        return {
            "remote": remote,
            "changed": True,
            "files": staged,
            "commit": commit_hash,
            "message": (push.stdout or commit.stdout).strip(),
        }

    def edit_video_source(
        self,
        source_id: int,
        site: str,
        video_id: str,
        source_url: str | None = None
    ) -> None:

        self.database.edit_video_source(
            source_id=source_id,
            site=site,
            video_id=video_id,
            source_url=source_url
        )

    def import_eroscripts(
        self,
        url: str,
        video_source_url: str | None = None,
        interactive: bool = True,
        persist: bool = True
    ):
        """Import EroScripts content.

        When persist=False, this method performs only the browser/import work
        and returns result objects. This is used by the GUI worker thread so
        that SQLite is never accessed outside the Tkinter/main thread.
        """
        auth = EroScriptsAuth(self.root)

        try:
            auth.start()

            if auth.context is None:
                raise RuntimeError(
                    "Could not start the EroScripts browser session."
                )

            importer = EroScriptsImporter(auth.context)
            destination = self.root / self.config.funscripts_dir

            results = importer.import_all_from_url(url, destination)

            # A caller may supply a source URL (CLI compatibility). For the
            # GUI, source selection is deliberately deferred until after the
            # automatic detection page has completed.
            if video_source_url:
                candidate = self.detect_video_source(video_source_url)
                if candidate is None:
                    raise ValueError(
                        "Could not determine a supported video site and video ID "
                        f"from this source URL: {video_source_url}"
                    )
                for result in results:
                    self.apply_detected_video_source(result, candidate)
            elif persist:
                for result in results:
                    self.assign_video_source(
                        result,
                        preferred_url=None,
                        interactive=interactive
                    )

            if persist:
                requested_url = self.normalize_url(url)
                for result in results:
                    # In normal/CLI mode, assign_video_source above has already
                    # selected a source or placeholder. Database writes happen
                    # in the caller's current thread.
                    self.save_eroscripts_import(result, requested_url)

            print(
                f"\n[IMPORT] Successfully imported {len(results)} funscript(s)."
            )
            return results

        finally:
            auth.close()

    def prepare_video_source(self, result) -> bool:
        """Attempt automatic source detection without prompting or DB access.

        Returns True when a supported source was found and applied to the
        in-memory import result. Returns False when GUI fallback is required.
        """
        candidates = list(getattr(result, "video_candidates", []) or [])

        for candidate in candidates:
            url = candidate.get("url") if isinstance(candidate, dict) else None
            detected = self.detect_video_source(url)
            if detected:
                self.apply_detected_video_source(result, detected)
                return True

        # Some importer results may already contain a video URL even if the
        # candidate list is empty.
        existing_url = getattr(result, "video_url", None)
        detected = self.detect_video_source(existing_url)
        if detected:
            self.apply_detected_video_source(result, detected)
            return True

        result.video_site = None
        result.video_title = None
        result.video_url = None
        result.video_id = None
        return False

    def apply_detected_video_source(self, result, candidate: dict) -> None:
        """Apply a known supported source to an in-memory import result."""
        site = (candidate.get("site") or "").strip().lower()
        url = self.normalize_url(candidate.get("url") or "")
        title = candidate.get("title")
        video_id = candidate.get("video_id") or self.extract_video_id(url)

        if not site or not url or not video_id:
            raise ValueError("Detected video source is incomplete.")

        if site not in self.config.xtoys_supported_video_sites:
            raise ValueError(
                f"Detected site '{site}' is not configured as an xToys-supported site."
            )

        result.video_site = site
        result.video_title = title
        result.video_url = url
        result.video_id = video_id

    def apply_placeholder_video_source(self, result) -> None:
        """Apply the project's fixed placeholder source to an import result."""
        self._apply_placeholder_source(result)

    @staticmethod
    def normalize_url(
        url: str | None
    ) -> str:

        if not url:
            return ""

        url = url.strip()

        # Convert Markdown links:
        #
        # [https://example.com](https://example.com)
        #
        # into:
        #
        # https://example.com

        match = re.fullmatch(
            r"\[([^\]]+)\]\(([^)]+)\)",
            url
        )

        if match:

            url = match.group(2).strip()

        return url

    def assign_video_source(
        self,
        result,
        preferred_url: str | None = None,
        interactive: bool = True
    ) -> None:
        """Choose the video's xToys source.

        A per-script EroScripts video match is preferred. If that source is
        not supported by xToys, use one uniform placeholder source while
        preserving the original URL as source_url so it can still be opened
        separately. If no source can be found, ask for manual input.
        """
        # A GUI/user-supplied source URL takes precedence over anything
        # scraped from the EroScripts page.  This also avoids the old
        # terminal prompts when importing through the GUI.
        if preferred_url:
            candidate = self.detect_video_source(preferred_url)
            if candidate is None:
                raise ValueError(
                    "Could not determine a supported video site and video ID "
                    f"from this source URL: {preferred_url}"
                )
            self._apply_detected_video_source(result, candidate)
            return

        candidates = list(getattr(result, "video_candidates", []) or [])

        if len(candidates) == 1 and candidates[0].get("url"):
            candidate = candidates[0]
            self._apply_detected_video_source(result, candidate)
            return

        if len(candidates) > 1:
            print(
                f"\n[IMPORT] Multiple video sources found for {result.filename}."
            )
            for i, candidate in enumerate(candidates, start=1):
                print(
                    f"  {i}. {candidate.get('site') or '?'} | "
                    f"{candidate.get('title') or '?'} | "
                    f"{candidate.get('url') or 'URL not found'}"
                )
            selection = input(
                "Select the matching video number, or press Enter for manual input: "
            ).strip()
            if selection:
                try:
                    index = int(selection) - 1
                    if 0 <= index < len(candidates) and candidates[index].get("url"):
                        self._apply_detected_video_source(result, candidates[index])
                        return
                except ValueError:
                    pass

        if not interactive:
            # GUI imports must never block on an input() prompt.  If the page
            # did not expose a usable source and the user did not provide one,
            # keep the existing placeholder behavior.
            self._apply_placeholder_source(result)
            return

        print(
            f"\n[IMPORT] Could not confidently determine a video source "
            f"for: {result.filename}"
        )
        print("Enter the video source manually, use the placeholder, or skip it.")
        print("  [M] Manual source")
        print("  [P] Use placeholder video")
        print("  [S] Skip video source")
        choice = input("Choice [P]: ").strip().lower() or "p"

        if choice == "p":
            self._apply_placeholder_source(result)
            return

        if choice != "m":
            result.video_site = None
            result.video_url = None
            result.video_title = None
            result.video_id = None
            print("[IMPORT] Video source skipped; script will still be imported.")
            return

        site = input("Site: ").strip()
        video_id = input("Video ID: ").strip()
        source_url = input("Source URL: ").strip()
        if not video_id and source_url:
            video_id = self.extract_video_id(source_url)
        if not site or not video_id:
            print("[IMPORT] Incomplete video source; using placeholder instead.")
            self._apply_placeholder_source(result)
            return

        result.video_site = site
        result.video_url = source_url or None
        result.video_id = video_id
        result.video_title = None
        print(f"[IMPORT] Manual video source set: {site} -> {video_id}")

    def _apply_detected_video_source(self, result, candidate: dict) -> None:
        site = (candidate.get("site") or "").strip().lower()
        url = candidate.get("url") or None
        title = candidate.get("title")
        video_id = self.extract_video_id(url)

        if not site or not url or not video_id:
            print(f"[IMPORT] Detected video source is incomplete for {result.filename}.")
            self._apply_placeholder_source(result)
            return

        if site not in self.config.xtoys_supported_video_sites:
            print(
                f"\n[IMPORT] Detected source '{site}' is not in the configured xToys-compatible list."
            )
            print("[IMPORT] Choose how to handle this video:")
            print("  [M] Enter a compatible video source manually")
            print("  [P] Use placeholder video")
            print("  [S] Skip video source")
            choice = input("Choice [P]: ").strip().lower() or "p"

            if choice == "m":
                site_input = input("Site: ").strip()
                video_id_input = input("Video ID: ").strip()
                source_url_input = input("Source URL: ").strip()
                if not video_id_input and source_url_input:
                    video_id_input = self.extract_video_id(source_url_input)
                if site_input and video_id_input:
                    result.video_site = site_input.lower()
                    result.video_title = None
                    result.video_url = source_url_input or None
                    result.video_id = video_id_input
                    print(f"[IMPORT] Manual video source set: {result.video_site} -> {result.video_id}")
                    return
                print("[IMPORT] Incomplete manual source; using placeholder video.")
            elif choice == "s":
                result.video_site = None
                result.video_url = None
                result.video_title = None
                result.video_id = None
                print("[IMPORT] Video source skipped; script will still be imported.")
                return

            self._apply_placeholder_source(result)
            return

        result.video_site = site
        result.video_title = title
        result.video_url = url
        result.video_id = video_id
        print(f"[IMPORT] Video automatically matched: {site} -> {url}")

    @staticmethod
    def _apply_placeholder_source(result) -> None:
        """Apply the single fixed placeholder video source.

        This deliberately uses the same normal site/id/url fields as every
        other video source so index.json remains compatible with the reference
        schema. The placeholder is intentionally unavailable for playback.
        """
        result.video_site = Application.PLACEHOLDER_VIDEO_SITE
        result.video_id = Application.PLACEHOLDER_VIDEO_ID
        result.video_url = Application.PLACEHOLDER_VIDEO_URL
        result.video_title = "Fly Away With Me (placeholder)"
        print(
            "[IMPORT] Using placeholder video: "
            f"{Application.PLACEHOLDER_VIDEO_URL}"
        )

    def save_eroscripts_import(
        self,
        result,
        requested_url: str
    ) -> None:

        # Always store a clean URL in SQLite.
        requested_url = self.normalize_url(
            requested_url
        )

        content_hash = result.content_hash

        existing = (
            self.database.get_script_by_hash(
                content_hash
            )
        )

        if existing is None:

            script_id = (
                self.database.add_script_metadata(
                    filename=result.filename,
                    content_hash=content_hash,
                    title=result.title,
                    display_name=result.title,
                    creator=result.creator,
                    eroscripts_url=requested_url
                )
            )

        else:

            script_id = existing["id"]

            self.database.update_script_metadata(
                script_id=script_id,
                filename=result.filename,
                title=result.title,
                display_name=result.title,
                creator=result.creator,
                eroscripts_url=requested_url
            )

        self.database.replace_script_tags(
            script_id,
            result.tags
        )

        if result.video_site:

            video_id = (
                getattr(result, "video_id", None)
                or self.extract_video_id(result.video_url)
            )

            if not video_id:
                video_id = result.video_url or ""

            self.database.upsert_video_source(
                script_id=script_id,
                site=result.video_site,
                video_id=video_id,
                source_url=result.video_url,
                duration=result.duration,
                average_speed=result.average_speed,
                action_count=result.action_count
            )

        self.database.upsert_eroscripts_thread(
            script_id=script_id,
            thread_url=requested_url
        )

    @classmethod
    def detect_video_source(cls, video_url: str | None) -> dict | None:
        """Detect the xToys-compatible site and ID directly from a video URL."""
        if not video_url:
            return None

        video_url = cls.normalize_url(video_url)
        parsed = urlparse(video_url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]

        supported = {
            "eporner.com",
            "rule34video.com",
            "noodledude.io",
        }

        # Treat supported-site subdomains such as cdn.noodledude.io as the
        # same source family. The canonical site stored in the library is
        # always the configured xToys-compatible root domain.
        if host == "noodledude.io" or host.endswith(".noodledude.io"):
            host = "noodledude.io"

        if host not in supported:
            return None

        path = parsed.path.rstrip("/")
        video_id = ""

        # Eporner: /video-IslEEgDDtNt/title/
        if host == "eporner.com":
            match = re.search(r"/video-([A-Za-z0-9_-]+)(?:/|$)", path, re.I)
            if match:
                video_id = match.group(1)

        # Common video URL forms used by the other supported sites.
        if not video_id:
            for pattern in (
                r"/video/([A-Za-z0-9_-]+)(?:/|$)",
                r"/videos?/([A-Za-z0-9_-]+)(?:/|$)",
                r"/v/([A-Za-z0-9_-]+)(?:/|$)",
            ):
                match = re.search(pattern, path, re.I)
                if match:
                    video_id = match.group(1)
                    break

        # Some supported sites expose the ID in a query parameter.
        if not video_id:
            for key in ("video", "video_id", "id"):
                value = parsed.query
                match = re.search(r"(?:^|&)" + re.escape(key) + r"=([^&]+)", value, re.I)
                if match:
                    video_id = match.group(1)
                    break

        if not video_id:
            return None

        return {
            "site": host,
            "url": video_url,
            "title": None,
            "video_id": video_id,
        }

    @staticmethod
    def extract_video_id(
        video_url: str | None
    ) -> str:

        if not video_url:
            return ""

        video_url = video_url.strip()

        detected = Application.detect_video_source(video_url)
        if detected:
            return detected["video_id"]

        # Handle Markdown links:
        #
        # [https://example.com/video/123/title](
        #     https://example.com/video/123/title
        # )
        #
        # Extract the actual URL from the Markdown wrapper.

        match = re.search(
            r"\]\((https?://[^)]+)\)",
            video_url
        )

        if match:

            video_url = match.group(1).strip()

        # Extract the ID specifically from:
        #
        # /video/<ID>/
        #
        # This prevents numbers later in the title from
        # being mistaken for the video ID.
        #
        # Example:
        #
        # /video/3109515/gee-gee-marie-rose-...-4d-...
        #
        # Correct result:
        #
        # 3109515

        match = re.search(
            r"/video/(\d+)(?:/|$)",
            video_url
        )

        if match:

            return match.group(1)

        # Fallback for URLs that don't use the expected
        # /video/<ID>/ format.

        parsed = urlparse(
            video_url
        )

        path = parsed.path.rstrip(
            "/"
        )

        path_parts = [
            part
            for part in path.split("/")
            if part
        ]

        for part in reversed(path_parts):

            if part.isdigit():

                return part

        return ""

    def login_eroscripts(self):

        auth = EroScriptsAuth(
            self.root
        )

        try:

            auth.login()

        finally:

            auth.close()
