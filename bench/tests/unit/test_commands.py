"""The console scripts fail on missing arguments (fail fast)."""

import pytest

from bench.record import chain
from bench.scan import scan


def test_bench_scan_needs_arguments() -> None:
    with pytest.raises(SystemExit) as info:
        scan.main([])
    assert info.value.code == 2


def test_bench_verify_needs_arguments() -> None:
    assert chain.main([]) == 2
