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

        eroscripts = data.get(
            "eroscripts",
            {}
        )

        video_sites = data.get(
            "video_sources",
            {}
        )

        def path_value(key, default):
            value = lib.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (str, Path)):
                return Path(default)
            return Path(value)

        return cls(

            path_value("funscripts_dir", "funscripts"),
            path_value("images_dir", "images"),
            path_value("metadata_dir", "metadata"),
            path_value("cache_dir", "cache"),
            path_value("logs_dir", "logs"),
            path_value("database", "storage/library.db"),
            path_value("index_file", "index.json"),
            bool(github.get("enabled", False)),
            bool(github.get("auto_push", False)),
            str(github.get("raw_base_url", "") or ""),
            bool(eroscripts.get("enabled", False)),
            tuple(dict.fromkeys(
                [
                    str(site).strip().lower()
                    for site in video_sites.get(
                        "xtoys_supported_sites",
                        ["eporner.com", "rule34video.com", "noodledude.io"]
                    )
                    if str(site).strip()
                ] + ["spankbang.com"]
            ))
        )

    def save(self, path: Path) -> None:
        """Persist editable settings while preserving unrelated config keys."""
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data.setdefault("library", {})
        data.setdefault("github", {})
        data.setdefault("eroscripts", {})
        data.setdefault("video_sources", {})
        data["library"].update({
            "funscripts_dir": str(self.funscripts_dir),
            "images_dir": str(self.images_dir),
            "metadata_dir": str(self.metadata_dir),
            "cache_dir": str(self.cache_dir),
            "logs_dir": str(self.logs_dir),
            "database": str(self.database),
            "index_file": str(self.index_file),
        })
        data["github"].update({
            "enabled": bool(self.github_enabled),
            "auto_push": bool(self.github_auto_push),
            "raw_base_url": str(self.raw_base_url),
        })
        data["eroscripts"]["enabled"] = bool(self.eroscripts_enabled)
        data["video_sources"]["xtoys_supported_sites"] = list(self.xtoys_supported_video_sites)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")

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