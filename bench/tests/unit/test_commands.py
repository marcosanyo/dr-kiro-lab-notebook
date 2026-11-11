"""The console scripts exist and fail until they are implemented (fail fast)."""

from bench.record import chain
from bench.scan import scan


def test_bench_scan_stub_fails() -> None:
    assert scan.main() != 0


def test_bench_verify_stub_fails() -> None:
    assert chain.main() != 0
