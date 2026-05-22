from __future__ import annotations

import hashlib
from pathlib import Path


def file_hash(path: Path, chunk_size: int = 1024 * 256) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as hashed_file:
        while True:
            chunk = hashed_file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def cache_metadata(path: Path, computed_hash: str | None = None) -> dict:
    stat_result = path.stat()
    return {
        "size": stat_result.st_size,
        "mtime_ns": stat_result.st_mtime_ns,
        "hash": computed_hash,
    }


def stat_matches_cache(path: Path, cache_record: dict | None) -> bool:
    if not cache_record:
        return False
    try:
        stat_result = path.stat()
    except OSError:
        return False
    return (
        int(cache_record.get("size", -1)) == stat_result.st_size
        and int(cache_record.get("mtime_ns", -1)) == stat_result.st_mtime_ns
    )

