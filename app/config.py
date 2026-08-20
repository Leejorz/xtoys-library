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
    github_owner: str
    github_repo: str
    github_branch: str
    github_remote_url: str

    eroscripts_enabled: bool
    xtoys_supported_video_sites: tuple[str, ...]
    tag_presets: tuple[str, ...]

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

            str(github.get("owner", "leejorz")).strip(),
            str(github.get("repo", "xtoys-library")).strip(),
            str(github.get("branch", "main")).strip() or "main",
            str(github.get("remote_url", "")).strip(),

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
                    ["eporner.com", "rule34video.com", "noodledude.io", "spankbang.com", "pmvhaven.com", "hmvmania.com", "pixeldrain.com"]
                )
                if str(site).strip()
            ),

            tuple(
                str(tag).strip()
                for tag in video_sites.get(
                    "tag_presets",
                    ["HMV", "PMV", "Asian", "White", "TikTok"]
                )
                if str(tag).strip()
            )
        )

    def save(self, path: Path) -> None:
        data = {
            "library": {
                "funscripts_dir": str(self.funscripts_dir),
                "images_dir": str(self.images_dir),
                "metadata_dir": str(self.metadata_dir),
                "cache_dir": str(self.cache_dir),
                "logs_dir": str(self.logs_dir),
                "database": str(self.database),
                "index_file": str(self.index_file),
                "index_hash_file": "index-hash.sha",
            },
            "github": {
                "enabled": self.github_enabled,
                "auto_push": self.github_auto_push,
                "owner": self.github_owner,
                "repo": self.github_repo,
                "branch": self.github_branch,
                "remote_url": self.github_remote_url,
                "raw_base_url": self.raw_base_url,
            },
            "eroscripts": {"enabled": self.eroscripts_enabled},
            "video_sources": {
                "xtoys_supported_sites": list(self.xtoys_supported_video_sites),
                "tag_presets": list(self.tag_presets),
            },
        }
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

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