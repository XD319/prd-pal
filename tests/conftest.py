from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Iterator

import pytest


_TMP_ROOT = Path(__file__).resolve().parents[1] / ".test-tmp"


@pytest.fixture
def tmp_path() -> Iterator[Path]:
    _TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = _TMP_ROOT / f"pytest-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
