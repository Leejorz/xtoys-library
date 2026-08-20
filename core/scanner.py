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

    def __init__(self, folder: Path, hash_cache: dict | None = None):
        self.folder = folder
        self.hash_cache = hash_cache if hash_cache is not None else {}

    def scan(self) -> list[ScannedScript]:
        scripts = []
        self.folder.mkdir(parents=True, exist_ok=True)
        seen = set()

        for file in self.folder.glob("*.funscript"):
            try:
                stat = file.stat()
                cache_key = str(file.resolve()).lower()
                signature = (stat.st_mtime_ns, stat.st_size)
                cached = self.hash_cache.get(cache_key)
                if cached and cached[0] == signature:
                    content_hash = cached[1]
                else:
                    content_hash = self.hash_file(file)
                    self.hash_cache[cache_key] = (signature, content_hash)
                seen.add(cache_key)
            except OSError:
                # If a file disappears during the scan, skip it rather than
                # failing the entire rebuild.
                continue

            scripts.append(
                ScannedScript(
                    filename=file.name,
                    path=file,
                    content_hash=content_hash,
                )
            )

        # Drop cache entries for files that no longer exist.
        for key in list(self.hash_cache):
            if key not in seen:
                self.hash_cache.pop(key, None)

        return sorted(scripts, key=lambda s: s.filename.lower())

    @staticmethod
    def hash_file(path: Path) -> str:
        h = sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                h.update(chunk)
        return h.hexdigest()
