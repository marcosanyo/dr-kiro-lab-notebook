"""No term derived from the solver files appears in the told set (wind-tunnel Requirement 13.8).

The real told set and the real derived terms are scanned the way `bench-scan` does. The hits found
earlier were decided by the user in task 12.4 (`wind-tunnel/blind-scan-findings.md`); this test fails when the
real hits are not empty, so a new collision shows at once. The user approved the 19 derived terms of the
former findings for the stop list in task 12.4, so the told set has no hit at all.
"""

from pathlib import Path

from bench.frontend.describe import declaration_text
from bench.scan.scan import Scanner

from wind_tunnel.declaration import scan_adapter
from wind_tunnel.failures import PUBLIC_REASONS

ADAPTER = Path(__file__).resolve().parents[1]
FINDINGS = ADAPTER.parent / "blind-scan-findings.md"
STOP_LIST = ADAPTER.parents[1] / ".kiro" / "blind-scan" / "stop-list.txt"


def _scanner() -> Scanner:
    return Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)


def _told_set_hits() -> set[tuple[str, int]]:
    text = declaration_text(scan_adapter().declaration()) + "\n"
    return {(word.lower(), text.count("\n", 0, start) + 1) for start, _, word in _scanner().find_terms(text)}


def test_told_set_has_no_hit():
    assert _told_set_hits() == set()


def test_findings_file_records_none():
    text = FINDINGS.read_text(encoding="utf-8")
    assert "Status: **none.**" in text
    assert not [line for line in text.splitlines() if line.startswith("| `")]


def test_scanner_derives_terms_from_every_kind_of_solver_file():
    terms = {name for name in _scanner().terms.values()}
    # a dictionary keyword, a patch name, a function-object library and a geometry-script class name
    assert {"deltaT", "inlet", "fieldFunctionObjects", "GeometryError"} <= terms


def test_public_reasons_contain_no_derived_term():
    scanner = _scanner()
    for reason in PUBLIC_REASONS.values():
        assert scanner.find_terms(reason) == []
