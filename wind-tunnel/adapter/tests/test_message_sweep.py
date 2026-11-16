"""No text the bench writes holds a term derived from the wind-tunnel solver files (Decision 44).

A derived term in a bench message turns a normal refusal into a bench failure that ends the session: the
real session wt-003 ended at its first action by the word "empty". The strings are collected by the fixed
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


def test_the_input_refusals_hold_no_derived_term_at_builder_level() -> None:
    """The refusal messages of the corner rule and the splitter floor, for several inputs, pass the
    builder-level scan with the real scan sources and the real stop list (Decision 45)."""
    from wind_tunnel_model.input_rule import input_refusal
    from wind_tunnel_model.settings import Settings

    settings = Settings.load()
    scanner = Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)
    cases = [(1.75, 0.5, v) for v in (1e-9, 1e-8, 3e-8, 5e-7, 9.99e-7)] + [
        (a, c, 1e-9) for a in (0.5, 1.75, 3.0) for c in (0.001, 0.01, 0.999)
    ]
    messages = [input_refusal(a, c, s, settings) for a, c, s in cases]
    assert all(m is not None for m in messages)
    found = [
        f"{finding} in {text!r}"
        for text in messages
        for finding in scanner.scan_text(text, "builder", "output")
    ]
    assert found == []
