from __future__ import annotations

import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


PIXELDRAIN_HOSTS = {
    "pixeldrain.com",
    "pixeldrain.net",
    "pixeldra.in",
    "pixeldrain.nl",
    "pixeldrain.biz",
    "pixeldrain.tech",
    "pixeldrain.dev",
}
CANONICAL_HOST = "pixeldrain.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36"
)


def is_pixeldrain_host(host: str | None) -> bool:
    value = (host or "").lower().removeprefix("www.").rstrip(".")
    return value in PIXELDRAIN_HOSTS


def parse_pixeldrain_url(url: str | None) -> dict | None:
    """Parse a Pixeldrain file or list URL without making a network request."""
    if not url:
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower().removeprefix("www.").rstrip(".")
    if not is_pixeldrain_host(host):
        return None

    path = parsed.path.rstrip("/")
    match = re.match(r"^/l/([A-Za-z0-9_-]+)$", path, re.I)
    if match:
        fragment = parse_qs(parsed.fragment, keep_blank_values=True)
        try:
            item_index = int((fragment.get("item") or ["0"])[0])
        except (TypeError, ValueError):
            item_index = 0
        if item_index < 0:
            item_index = 0
        return {
            "kind": "list",
            "site": CANONICAL_HOST,
            "list_id": match.group(1),
            "item_index": item_index,
            "url": url.strip(),
        }

    for pattern in (
        r"^/u/([A-Za-z0-9_-]+)$",
        r"^/api/file/([A-Za-z0-9_-]+)$",
        r"^/api/file/([A-Za-z0-9_-]+)/info$",
    ):
        match = re.match(pattern, path, re.I)
        if match:
            return {
                "kind": "file",
                "site": CANONICAL_HOST,
                "file_id": match.group(1),
                "url": url.strip(),
            }
    return None


def _get_json(url: str, timeout: float = 10.0) -> dict | None:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(2_000_000)
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    try:
        value = json.loads(data.decode("utf-8", errors="replace"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def resolve_pixeldrain_url(url: str | None, timeout: float = 10.0) -> dict | None:
    """Resolve a Pixeldrain list item to the concrete file ID.

    Public list/file metadata reads do not require authentication. If metadata
    cannot be fetched, list URLs still get a stable composite fallback ID so
    two different ``#item=`` entries never collapse onto one video record.
    """
    parsed = parse_pixeldrain_url(url)
    if not parsed:
        return None

    if parsed["kind"] == "file":
        file_id = parsed["file_id"]
        info = _get_json(f"https://pixeldrain.com/api/file/{file_id}/info", timeout) or {}
        return {
            "site": CANONICAL_HOST,
            "video_id": file_id,
            "file_id": file_id,
            "title": info.get("name"),
            "mime_type": info.get("mime_type"),
            "thumbnail_url": f"https://pixeldrain.com/api/file/{file_id}/thumbnail?width=256&height=256",
            "url": parsed["url"],
        }

    list_id = parsed["list_id"]
    item_index = parsed["item_index"]
    info = _get_json(f"https://pixeldrain.com/api/list/{list_id}", timeout)
    files = info.get("files") if isinstance(info, dict) else None
    if isinstance(files, list) and 0 <= item_index < len(files):
        item = files[item_index] if isinstance(files[item_index], dict) else {}
        file_id = str(item.get("id") or "").strip()
        if file_id:
            return {
                "site": CANONICAL_HOST,
                "video_id": file_id,
                "file_id": file_id,
                "list_id": list_id,
                "item_index": item_index,
                "title": item.get("name"),
                "mime_type": item.get("mime_type"),
                "thumbnail_url": f"https://pixeldrain.com/api/file/{file_id}/thumbnail?width=256&height=256",
                "url": parsed["url"],
            }

    return {
        "site": CANONICAL_HOST,
        "video_id": f"{list_id}#item={item_index}",
        "file_id": None,
        "list_id": list_id,
        "item_index": item_index,
        "title": None,
        "mime_type": None,
        "thumbnail_url": None,
        "url": parsed["url"],
    }
