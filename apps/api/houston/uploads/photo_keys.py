from __future__ import annotations


def observation_photo_thumbnail_storage_key(storage_key: str) -> str:
    if not storage_key:
        return ""
    if storage_key.endswith(".thumb.jpg"):
        return storage_key
    filename = storage_key.rsplit("/", 1)[-1]
    if "." not in filename:
        return f"{storage_key}.thumb.jpg"
    stem, _extension = storage_key.rsplit(".", 1)
    return f"{stem}.thumb.jpg"


def observation_photo_storage_keys(storage_key: str) -> list[str]:
    if not storage_key:
        return []
    thumbnail_key = observation_photo_thumbnail_storage_key(storage_key)
    if thumbnail_key == storage_key:
        return [storage_key]
    return [storage_key, thumbnail_key]
