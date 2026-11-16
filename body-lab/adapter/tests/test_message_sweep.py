"""No text the bench writes holds a term derived from the body-lab model files (Decision 44).

A derived term in a bench message turns a normal refusal into a bench failure that ends the session: the
a normal refusal must stay a refusal. The strings are collected by the fixed
rule in `bench/tests/message_sweep.py` and scanned at builder level with the real scan sources and the real
stop list.
"""

import sys
from pathlib import Path

import bench
from bench.scan.scan import Scanner

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[1]
sys.path.insert(0, str(ROOT / "bench" / "tests"))
from message_sweep import collect_all  # noqa: E402

STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
BENCH = Path(bench.__file__).resolve().parent


def test_no_bench_text_holds_a_derived_term() -> None:
    scanner = Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)
    pieces = collect_all(BENCH)
    assert len(pieces) > 500, len(pieces)  # the rule collects the bench's own text, not nothing
    found = [
        f"{piece.file}:{piece.line}: {finding} in {piece.text!r}"
        for piece in pieces
        for finding in scanner.scan_text(piece.text, "builder", "output")
    ]
    assert found == []
