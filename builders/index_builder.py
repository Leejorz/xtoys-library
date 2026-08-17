import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


class IndexBuilder:

    def __init__(
        self,
        root: Path,
        database,
        config
    ):
        self.root = root
        self.database = database
        self.config = config

    def build(self):

        scripts = self.database.all_scripts()

        videos = []

        for script in scripts:

            video = self.build_video(script)

            if video is not None:
                videos.append(video)

        videos.sort(
            key=lambda video: video["displayName"].lower()
        )

        tags = self.build_tags(videos)

        index = {
            "author": "local",
            "videos": videos,
            "version": 1,
            "tags": tags
        }

        index["hash"] = self.calculate_hash(index)

        output_path = (
            self.root / self.config.index_file
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                index,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.write("\n")

        # The original xToys player expects a separate index-hash.sha
        # file in addition to the "hash" field inside index.json.
        hash_path = output_path.parent / "index-hash.sha"

        with open(
            hash_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(index["hash"])
            file.write("\n")

        return output_path, len(videos)

    def build_video(self, script):

        script_id = script["id"]
        filename = script["filename"]

        display_name = Path(
            filename
        ).stem

        now = datetime.now(
            timezone.utc
        ).isoformat()

        tags = self.database.get_tags_for_script(
            script_id
        )

        video_source = self.database.get_video_source(
            script_id
        )

        site = ""
        video_id = ""

        if video_source:

            site = self.normalize_site(
                video_source["site"]
            )

            video_id = (
                video_source["video_id"]
                or ""
            )

        # IMPORTANT: xToys uses the EroScripts page as the video object's
        # `url`. The actual video-host URL is stored separately in the
        # database and is used only to derive site + video_id.
        eroscripts_url = self.normalize_url(
            script["eroscripts_url"]
        )

        return {
            "name": display_name,

            "site": site,

            "id": video_id,

            "scripts": [
                {
                    "name": filename,
                    "location":
                        self.build_script_location(
                            filename
                        )
                }
            ],

            "tags": tags,

            "created_at": (
                script["created_at"]
                or now
            ),

            "url": eroscripts_url,

            "valid": True,

            "creator": (
                script["creator"]
                or ""
            ),

            "ignore": False,

            "last_checked": now,

            "thumbnail": (
                script["thumbnail"]
                or ""
            ),

            "displayName": display_name
        }

    @staticmethod
    def normalize_site(site: str | None) -> str:

        if not site:
            return ""

        value = site.strip().lower()

        # Keep the identifiers expected by the original xToys index.
        aliases = {
            "spankbang.com": "spankbang",
            "www.spankbang.com": "spankbang",
            "pornhub.com": "pornhub",
            "www.pornhub.com": "pornhub",
            "xvideos.com": "xvideos",
            "www.xvideos.com": "xvideos",
            "xhamster.com": "xhamster",
            "www.xhamster.com": "xhamster",
            "eporner.com": "eporner",
            "www.eporner.com": "eporner",
            "rule34video.com": "rule34video",
            "www.rule34video.com": "rule34video",
            "noodledude.io": "noodledude",
            "www.noodledude.io": "noodledude",
        }

        return aliases.get(value, value.removeprefix("www.").split(".")[0])

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

        if (
            url.startswith("[")
            and "](" in url
            and url.endswith(")")
        ):

            closing_bracket = url.find("](")

            if closing_bracket > 0:

                target = url[
                    closing_bracket + 2:
                    -1
                ]

                if target:
                    return target.strip()

        return url

    def build_script_location(
        self,
        filename: str
    ):

        base_url = getattr(
            self.config,
            "raw_base_url",
            ""
        )

        if not base_url:
            return filename

        # GitHub raw URLs should use forward slashes.
        filename = filename.replace(
            "\\",
            "/"
        )

        # Encode the filename for use inside
        # an HTTP URL while preserving the
        # filename separators.
        encoded_filename = quote(
            filename,
            safe="/"
        )

        return (
            base_url.rstrip("/")
            + "/"
            + encoded_filename
        )

    @staticmethod
    def build_tags(
        videos
    ):

        tags = {}

        for video in videos:

            for tag in video["tags"]:

                if tag not in tags:
                    tags[tag] = []

                tags[tag].append(
                    video["displayName"]
                )

        for tag in tags:

            tags[tag].sort(
                key=str.lower
            )

        return dict(
            sorted(
                tags.items(),
                key=lambda item:
                    item[0].lower()
            )
        )

    @staticmethod
    def calculate_hash(
        index
    ):

        content = dict(index)

        content.pop(
            "hash",
            None
        )

        serialized = json.dumps(
            content,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            ),
            sort_keys=True
        )

        return hashlib.sha256(
            serialized.encode(
                "utf-8"
            )
        ).hexdigest()