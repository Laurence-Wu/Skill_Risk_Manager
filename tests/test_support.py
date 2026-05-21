from __future__ import annotations

import os
import shutil
import uuid
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path


def writable_temp_root() -> Path:
    configured_root = os.environ.get("SKILL_MANAGER_TEST_TMP")
    temp_root = Path(configured_root) if configured_root else Path.cwd() / ".test_tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    return temp_root


@contextmanager
def writable_temp_dir() -> Iterator[Path]:
    temp_dir = writable_temp_root() / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
