from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass
class ScannedScript:
    filename: str
    path: Path
    content_hash: str


class LibraryScanner:

    def __init__(self, folder: Path):
        self.folder = folder

    def scan(self) -> list[ScannedScript]:

        scripts = []

        self.folder.mkdir(parents=True, exist_ok=True)

        for file in self.folder.glob("*.funscript"):

            scripts.append(
                ScannedScript(
                    filename=file.name,
                    path=file,
                    content_hash=self.hash_file(file)
                )
            )

        return sorted(scripts, key=lambda s: s.filename.lower())

    @staticmethod
    def hash_file(path: Path) -> str:

        h = sha256()

        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)

        return h.hexdigest()