import re
import sqlite3
from pathlib import Path


SCHEMA = '''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    title TEXT,
    display_name TEXT,
    creator TEXT,
    eroscripts_url TEXT,
    thumbnail TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS script_tags (
    script_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (script_id, tag_id),
    FOREIGN KEY (script_id)
        REFERENCES scripts(id)
        ON DELETE CASCADE,
    FOREIGN KEY (tag_id)
        REFERENCES tags(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS video_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER NOT NULL,
    site TEXT NOT NULL,
    video_id TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    notes TEXT,
    duration TEXT,
    average_speed REAL,
    action_count INTEGER,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(script_id, site, video_id),
    FOREIGN KEY (script_id)
        REFERENCES scripts(id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS eroscripts_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id INTEGER,
    thread_url TEXT NOT NULL UNIQUE,
    last_checked TEXT,
    last_successful_import TEXT,
    FOREIGN KEY (script_id)
        REFERENCES scripts(id)
        ON DELETE SET NULL
);
'''


class Database:

    def __init__(
        self,
        path: Path
    ):
        self.path = path
        self.connection = None

    def connect(self):

        if self.connection is None:

            self.path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self.connection = sqlite3.connect(
                self.path
            )

            self.connection.row_factory = (
                sqlite3.Row
            )

            self.connection.execute(
                "PRAGMA foreign_keys = ON"
            )
            # WAL + NORMAL drastically reduces the cost of the many small
            # metadata commits performed while saving/importing scripts, while
            # retaining durable SQLite transactions.
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = NORMAL")
            self.connection.execute("PRAGMA busy_timeout = 5000")

        return self.connection

    def initialize(self):

        connection = self.connect()

        connection.executescript(
            SCHEMA
        )

        self.migrate()

        connection.commit()

    def migrate(self):

        connection = self.connect()

        video_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(video_sources)"
            ).fetchall()
        }

        video_migrations = {
            "duration":
                "ALTER TABLE video_sources "
                "ADD COLUMN duration TEXT",
            "average_speed":
                "ALTER TABLE video_sources "
                "ADD COLUMN average_speed REAL",
            "action_count":
                "ALTER TABLE video_sources "
                "ADD COLUMN action_count INTEGER",
        }

        for column, statement in video_migrations.items():
            if column not in video_columns:
                connection.execute(statement)


    def close(self):

        if self.connection:

            self.connection.close()

            self.connection = None

    def script_exists(
        self,
        content_hash: str
    ) -> bool:

        row = self.connect().execute(
            "SELECT id FROM scripts "
            "WHERE content_hash=?",
            (content_hash,)
        ).fetchone()

        return row is not None

    def get_script_by_hash(
        self,
        content_hash: str
    ):

        return self.connect().execute(
            "SELECT * FROM scripts "
            "WHERE content_hash=?",
            (content_hash,)
        ).fetchone()

    def update_script_thumbnail(
        self,
        script_id: int,
        thumbnail: str | None
    ) -> None:
        """Update the existing thumbnail field without changing the schema."""
        self.connect().execute(
            "UPDATE scripts SET thumbnail=?, updated_at=datetime('now') WHERE id=?",
            (thumbnail or "", script_id),
        )
        self.connection.commit()

    def update_filename(
        self,
        content_hash: str,
        filename: str
    ) -> None:

        self.connect().execute(
            "UPDATE scripts "
            "SET filename=?, "
            "updated_at=datetime('now') "
            "WHERE content_hash=?",
            (
                filename,
                content_hash
            )
        )

        self.connection.commit()

    def add_script(
        self,
        filename: str,
        content_hash: str
    ) -> None:

        self.connect().execute(
            """
            INSERT INTO scripts
            (
                filename,
                content_hash,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                datetime('now'),
                datetime('now')
            )
            """,
            (
                filename,
                content_hash
            )
        )

        self.connection.commit()

    def add_script_metadata(
        self,
        filename: str,
        content_hash: str,
        title: str | None = None,
        display_name: str | None = None,
        creator: str | None = None,
        eroscripts_url: str | None = None,
        thumbnail: str | None = None
    ) -> int:

        cursor = self.connect().execute(
            """
            INSERT INTO scripts
            (
                filename,
                content_hash,
                title,
                display_name,
                creator,
                eroscripts_url,
                thumbnail,
                created_at,
                updated_at
            )
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                datetime('now'),
                datetime('now')
            )
            """,
            (
                filename,
                content_hash,
                title,
                display_name,
                creator,
                eroscripts_url,
                thumbnail
            )
        )

        self.connection.commit()

        return cursor.lastrowid

    def update_script_metadata(
        self,
        script_id: int,
        filename: str,
        title: str | None = None,
        display_name: str | None = None,
        creator: str | None = None,
        eroscripts_url: str | None = None,
        thumbnail: str | None = None
    ) -> None:

        self.connect().execute(
            """
            UPDATE scripts
            SET filename=?,
                title=?,
                display_name=?,
                creator=?,
                eroscripts_url=?,
                thumbnail=COALESCE(?, thumbnail),
                updated_at=datetime('now')
            WHERE id=?
            """,
            (
                filename,
                title,
                display_name,
                creator,
                eroscripts_url,
                thumbnail,
                script_id
            )
        )

        self.connection.commit()

    def get_or_create_tag(
        self,
        name: str
    ) -> int:

        name = name.strip()

        if not name:

            raise ValueError(
                "Tag name cannot be empty."
            )

        connection = self.connect()

        connection.execute(
            """
            INSERT OR IGNORE INTO tags
            (name)
            VALUES (?)
            """,
            (name,)
        )

        row = connection.execute(
            """
            SELECT id
            FROM tags
            WHERE name=?
            """,
            (name,)
        ).fetchone()

        self.connection.commit()

        return row["id"]

    def replace_script_tags(
        self,
        script_id: int,
        tags: list[str] | None
    ) -> None:

        connection = self.connect()

        connection.execute(
            """
            DELETE FROM script_tags
            WHERE script_id=?
            """,
            (script_id,)
        )

        if tags:

            cleaned_tags = []

            for tag in tags:

                if not tag:
                    continue

                tag = tag.strip()

                if not tag:
                    continue

                if tag not in cleaned_tags:

                    cleaned_tags.append(
                        tag
                    )

            for tag in cleaned_tags:

                tag_id = self.get_or_create_tag(
                    tag
                )

                connection.execute(
                    """
                    INSERT OR IGNORE INTO script_tags
                    (
                        script_id,
                        tag_id
                    )
                    VALUES (?, ?)
                    """,
                    (
                        script_id,
                        tag_id
                    )
                )

        connection.commit()

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

        markdown_match = re.search(
            r"\]\((https?://[^)]+)\)",
            url
        )

        if markdown_match:

            return markdown_match.group(1).strip()

        # Also handle a plain URL that may have
        # surrounding Markdown or other text.

        url_match = re.search(
            r"https?://[^\s\]\)]+",
            url
        )

        if url_match:

            return url_match.group(0).strip()

        return url

    def upsert_video_source(
        self,
        script_id: int,
        site: str,
        video_id: str,
        source_url: str | None = None,
        duration: str | None = None,
        average_speed: float | None = None,
        action_count: int | None = None
    ) -> None:

        connection = self.connect()

        site = (
            site.strip()
            if site
            else ""
        )

        video_id = (
            str(video_id).strip()
            if video_id is not None
            else ""
        )

        source_url = self.normalize_url(
            source_url
        )

        if not site:

            raise ValueError(
                "Video source site cannot be empty."
            )

        if not video_id:

            raise ValueError(
                "Video source ID cannot be empty."
            )

        # ---------------------------------------------------------
        # First, look for the exact video ID.
        # ---------------------------------------------------------

        existing = connection.execute(
            """
            SELECT id
            FROM video_sources
            WHERE script_id=?
              AND site=?
              AND video_id=?
            """,
            (
                script_id,
                site,
                video_id
            )
        ).fetchone()

        # ---------------------------------------------------------
        # If the exact ID does not exist, look for the same
        # script/site/source URL.
        #
        # This is important because an earlier import may have
        # stored an incorrect video ID while still having the
        # correct video URL.
        #
        # Example:
        #
        # old:
        #   video_id = 4
        #
        # new:
        #   video_id = 3109515
        #
        # Same source URL means this is an update, not a new
        # video source.
        # ---------------------------------------------------------

        if existing is None and source_url:

            existing = connection.execute(
                """
                SELECT id
                FROM video_sources
                WHERE script_id=?
                  AND site=?
                  AND source_url=?
                ORDER BY
                    is_primary DESC,
                    updated_at DESC,
                    id DESC
                LIMIT 1
                """,
                (
                    script_id,
                    site,
                    source_url
                )
            ).fetchone()

        # ---------------------------------------------------------
        # Only one source for a script/site should be primary.
        #
        # We deliberately do this AFTER identifying the row that
        # should be updated so an existing source is not lost.
        # ---------------------------------------------------------

        connection.execute(
            """
            UPDATE video_sources
            SET is_primary=0
            WHERE script_id=?
              AND site=?
            """,
            (
                script_id,
                site
            )
        )

        if existing:

            # -----------------------------------------------------
            # Update the existing row.
            #
            # The video_id is included here so an incorrect old
            # ID can be replaced by the actual site ID.
            # -----------------------------------------------------

            try:

                connection.execute(
                    """
                    UPDATE video_sources
                    SET video_id=?,
                        source_url=?,
                        duration=?,
                        average_speed=?,
                        action_count=?,
                        is_primary=1,
                        updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (
                        video_id,
                        source_url,
                        duration,
                        average_speed,
                        action_count,
                        existing["id"]
                    )
                )

            except sqlite3.IntegrityError:

                # -------------------------------------------------
                # This can happen if another row already owns the
                # same script/site/video_id.
                #
                # In that case, update that exact row instead.
                # -------------------------------------------------

                exact = connection.execute(
                    """
                    SELECT id
                    FROM video_sources
                    WHERE script_id=?
                      AND site=?
                      AND video_id=?
                    LIMIT 1
                    """,
                    (
                        script_id,
                        site,
                        video_id
                    )
                ).fetchone()

                if exact is None:
                    raise

                connection.execute(
                    """
                    UPDATE video_sources
                    SET source_url=?,
                        duration=?,
                        average_speed=?,
                        action_count=?,
                        is_primary=1,
                        updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (
                        source_url,
                        duration,
                        average_speed,
                        action_count,
                        exact["id"]
                    )
                )

        else:

            connection.execute(
                """
                INSERT INTO video_sources
                (
                    script_id,
                    site,
                    video_id,
                    is_primary,
                    source_url,
                    duration,
                    average_speed,
                    action_count,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?,
                    ?,
                    ?,
                    1,
                    ?,
                    ?,
                    ?,
                    ?,
                    datetime('now'),
                    datetime('now')
                )
                """,
                (
                    script_id,
                    site,
                    video_id,
                    source_url,
                    duration,
                    average_speed,
                    action_count
                )
            )

        connection.commit()

    def upsert_eroscripts_thread(
        self,
        script_id: int,
        thread_url: str
    ) -> None:

        thread_url = self.normalize_url(
            thread_url
        )

        connection = self.connect()

        existing = connection.execute(
            """
            SELECT id
            FROM eroscripts_threads
            WHERE thread_url=?
            """,
            (thread_url,)
        ).fetchone()

        if existing:

            connection.execute(
                """
                UPDATE eroscripts_threads
                SET script_id=?,
                    last_checked=datetime('now'),
                    last_successful_import=datetime('now')
                WHERE id=?
                """,
                (
                    script_id,
                    existing["id"]
                )
            )

        else:

            connection.execute(
                """
                INSERT INTO eroscripts_threads
                (
                    script_id,
                    thread_url,
                    last_checked,
                    last_successful_import
                )
                VALUES (
                    ?,
                    ?,
                    datetime('now'),
                    datetime('now')
                )
                """,
                (
                    script_id,
                    thread_url
                )
            )

        connection.commit()

    def get_tags_for_script(
        self,
        script_id: int
    ) -> list[str]:

        rows = self.connect().execute(
            """
            SELECT tags.name
            FROM tags
            INNER JOIN script_tags
                ON script_tags.tag_id = tags.id
            WHERE script_tags.script_id=?
            ORDER BY tags.name COLLATE NOCASE
            """,
            (script_id,)
        ).fetchall()

        return [
            row["name"]
            for row in rows
        ]

    def edit_video_source(
        self,
        source_id: int,
        site: str,
        video_id: str,
        source_url: str | None = None
    ) -> None:

        connection = self.connect()

        site = (
            site.strip()
            if site
            else ""
        )

        video_id = (
            str(video_id).strip()
            if video_id is not None
            else ""
        )

        source_url = self.normalize_url(
            source_url
        )

        if not site:
            raise ValueError(
                "Video source site cannot be empty."
            )

        if not video_id:
            raise ValueError(
                "Video source ID cannot be empty."
            )

        current = connection.execute(
            """
            SELECT id, script_id
            FROM video_sources
            WHERE id=?
            """,
            (source_id,)
        ).fetchone()

        if current is None:
            raise ValueError(
                f"Video source {source_id} was not found."
            )

        duplicate = connection.execute(
            """
            SELECT id
            FROM video_sources
            WHERE script_id=?
              AND site=?
              AND video_id=?
              AND id<>?
            LIMIT 1
            """,
            (
                current["script_id"],
                site,
                video_id,
                source_id
            )
        ).fetchone()

        if duplicate is not None:
            raise ValueError(
                "That script already has another video source "
                "with the same site and video ID."
            )

        connection.execute(
            """
            UPDATE video_sources
            SET site=?,
                video_id=?,
                source_url=?,
                is_primary=1,
                updated_at=datetime('now')
            WHERE id=?
            """,
            (
                site,
                video_id,
                source_url,
                source_id
            )
        )

        # Editing a source makes it the script's primary source.
        connection.execute(
            """
            UPDATE video_sources
            SET is_primary=0
            WHERE script_id=?
              AND id<>?
            """,
            (
                current["script_id"],
                source_id
            )
        )

        connection.commit()

    def get_video_source(
        self,
        script_id: int
    ):

        return self.connect().execute(
            """
            SELECT *
            FROM video_sources
            WHERE script_id=?
            ORDER BY
                is_primary DESC,
                updated_at DESC,
                id DESC
            LIMIT 1
            """,
            (script_id,)
        ).fetchone()

    def get_script_cleanup_info(self, script_id: int):
        connection = self.connect()

        script = connection.execute(
            "SELECT * FROM scripts WHERE id=?",
            (script_id,)
        ).fetchone()

        if script is None:
            return None

        tag_count = connection.execute(
            "SELECT COUNT(*) FROM script_tags WHERE script_id=?",
            (script_id,)
        ).fetchone()[0]

        video_count = connection.execute(
            "SELECT COUNT(*) FROM video_sources WHERE script_id=?",
            (script_id,)
        ).fetchone()[0]

        thread_count = connection.execute(
            "SELECT COUNT(*) FROM eroscripts_threads WHERE script_id=?",
            (script_id,)
        ).fetchone()[0]

        return {
            "script": script,
            "tag_count": tag_count,
            "video_count": video_count,
            "thread_count": thread_count
        }

    def delete_script_and_associated_records(self, script_id: int) -> dict:
        connection = self.connect()

        info = self.get_script_cleanup_info(script_id)

        if info is None:
            raise ValueError(
                f"Script ID {script_id} does not exist."
            )

        try:
            connection.execute("BEGIN")

            connection.execute(
                "DELETE FROM eroscripts_threads WHERE script_id=?",
                (script_id,)
            )

            connection.execute(
                "DELETE FROM script_tags WHERE script_id=?",
                (script_id,)
            )

            connection.execute(
                "DELETE FROM video_sources WHERE script_id=?",
                (script_id,)
            )

            connection.execute(
                "DELETE FROM scripts WHERE id=?",
                (script_id,)
            )

            # Remove tag rows that are no longer used by any script.
            connection.execute(
                """
                DELETE FROM tags
                WHERE id NOT IN (
                    SELECT DISTINCT tag_id
                    FROM script_tags
                )
                """
            )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        return {
            "script_id": script_id,
            "filename": info["script"]["filename"],
            "tag_count": info["tag_count"],
            "video_count": info["video_count"],
            "thread_count": info["thread_count"]
        }

    def cleanup_orphaned_records(self) -> dict:
        connection = self.connect()

        counts = {
            "script_tags": 0,
            "video_sources": 0,
            "threads": 0,
            "tags": 0
        }

        try:
            connection.execute("BEGIN")

            cursor = connection.execute(
                """
                DELETE FROM script_tags
                WHERE script_id NOT IN (SELECT id FROM scripts)
                   OR tag_id NOT IN (SELECT id FROM tags)
                """
            )
            counts["script_tags"] = cursor.rowcount

            cursor = connection.execute(
                """
                DELETE FROM video_sources
                WHERE script_id NOT IN (SELECT id FROM scripts)
                """
            )
            counts["video_sources"] = cursor.rowcount

            cursor = connection.execute(
                """
                DELETE FROM eroscripts_threads
                WHERE script_id IS NOT NULL
                  AND script_id NOT IN (SELECT id FROM scripts)
                """
            )
            counts["threads"] = cursor.rowcount

            cursor = connection.execute(
                """
                DELETE FROM tags
                WHERE id NOT IN (
                    SELECT DISTINCT tag_id FROM script_tags
                )
                """
            )
            counts["tags"] = cursor.rowcount

            connection.commit()

        except Exception:
            connection.rollback()
            raise

        return counts

    def all_scripts(self):

        return self.connect().execute(
            """
            SELECT *
            FROM scripts
            ORDER BY filename
            """
        ).fetchall()