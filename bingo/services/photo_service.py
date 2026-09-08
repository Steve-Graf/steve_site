import re
import shutil
from pathlib import Path
from uuid import uuid4

from flask import url_for

PHOTOS_ROOT = Path(__file__).resolve().parent.parent / "bingo_photos"

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9_-]+$")


def save_tile_photo(game_id: str, tile_id: int, file_storage) -> str:
    ext = ALLOWED_CONTENT_TYPES.get(file_storage.content_type)
    if not ext:
        raise ValueError("Unsupported photo type")

    game_dir = PHOTOS_ROOT / game_id
    game_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{tile_id}-{uuid4().hex}.{ext}"
    file_storage.save(game_dir / filename)
    return filename


def delete_tile_photo(game_id: str, filename: str) -> None:
    path = PHOTOS_ROOT / game_id / filename
    path.unlink(missing_ok=True)


def delete_all_photos(game_id: str) -> None:
    shutil.rmtree(PHOTOS_ROOT / game_id, ignore_errors=True)


def resolve_photo_path(game_id: str, filename: str) -> Path | None:
    if not _SAFE_SEGMENT.match(game_id):
        return None

    stem, _, ext = filename.rpartition(".")
    if not stem or not _SAFE_SEGMENT.match(stem) or ext.lower() not in ALLOWED_CONTENT_TYPES.values():
        return None

    path = (PHOTOS_ROOT / game_id / filename).resolve()
    if PHOTOS_ROOT.resolve() not in path.parents:
        return None
    return path


def with_photo_urls(game_id: str, tile: dict) -> dict:
    tile = dict(tile)
    tile["photos"] = [
        {**photo, "url": url_for("bingo_pages.tile_photo", game_id=game_id, filename=photo["filename"])}
        for photo in tile.get("photos") or []
    ]
    return tile
