from pathlib import Path

import pytest

from labkit import Lab


@pytest.fixture
def lab(tmp_path: Path) -> Lab:
    return Lab(tmp_path)
