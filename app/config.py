import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:

    funscripts_dir: Path
    images_dir: Path
    metadata_dir: Path
    cache_dir: Path
    logs_dir: Path
    database: Path
    index_file: Path

    github_enabled: bool
    github_auto_push: bool
    raw_base_url: str

    publish_destination: str
    github_remote_url: str
    github_raw_base_url: str
    file_server_upload_url: str
    file_server_public_base_url: str
    file_server_username: str
    file_server_password: str

    eroscripts_enabled: bool
    xtoys_supported_video_sites: tuple[str, ...]

    @classmethod
    def load(cls, path: Path):

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        lib = data.get(
            "library",
            {}
        )

        github = data.get(
            "github",
            {}
        )

        publishing = data.get(
            "publishing",
            {}
        )

        eroscripts = data.get(
            "eroscripts",
            {}
        )

        video_sites = data.get(
            "video_sources",
            {}
        )

        return cls(

            Path(
                lib.get(
                    "funscripts_dir",
                    "funscripts"
                )
            ),

            Path(
                lib.get(
                    "images_dir",
                    "images"
                )
            ),

            Path(
                lib.get(
                    "metadata_dir",
                    "metadata"
                )
            ),

            Path(
                lib.get(
                    "cache_dir",
                    "cache"
                )
            ),

            Path(
                lib.get(
                    "logs_dir",
                    "logs"
                )
            ),

            Path(
                lib.get(
                    "database",
                    "storage/library.db"
                )
            ),

            Path(
                lib.get(
                    "index_file",
                    "index.json"
                )
            ),

            bool(
                github.get(
                    "enabled",
                    False
                )
            ),

            bool(
                github.get(
                    "auto_push",
                    False
                )
            ),

            github.get(
                "raw_base_url",
                ""
            ),

            str(publishing.get(
                "destination",
                "github"
            )).strip().lower(),

            str(publishing.get(
                "github_remote_url",
                ""
            ) or ""),

            str(publishing.get(
                "github_raw_base_url",
                github.get("raw_base_url", "")
            ) or ""),

            str(publishing.get(
                "file_server_upload_url",
                ""
            ) or ""),

            str(publishing.get(
                "file_server_public_base_url",
                ""
            ) or ""),

            str(publishing.get(
                "file_server_username",
                ""
            ) or ""),

            str(publishing.get(
                "file_server_password",
                ""
            ) or ""),

            bool(
                eroscripts.get(
                    "enabled",
                    False
                )
            ),

            tuple(
                str(site).strip().lower()
                for site in video_sites.get(
                    "xtoys_supported_sites",
                    ["eporner.com", "rule34video.com", "noodledude.io"]
                )
                if str(site).strip()
            )
        )

    def ensure_directories(
        self,
        root: Path
    ):

        directories = (
            self.funscripts_dir,
            self.images_dir,
            self.metadata_dir,
            self.cache_dir,
            self.logs_dir,
            self.database.parent
        )

        for directory in directories:

            (
                root / directory
            ).mkdir(
                parents=True,
                exist_ok=True
            )