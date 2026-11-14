"""No term derived from the solver files appears in the told set (wind-tunnel Requirement 13.8).

The real told set and the real derived terms are scanned the way `bench-scan` does. The hits that remain are
listed in `wind-tunnel/blind-scan-findings.md` for the user's decision (task 12.4); this test fails when the
real hits and that list differ, so a new collision, or a fixed one, shows at once. When the user has settled
every finding the list is empty and the test says: no hit at all.
"""

import re
from pathlib import Path

from bench.frontend.describe import declaration_text
from bench.scan.scan import Scanner

from wind_tunnel.declaration import scan_adapter
from wind_tunnel.failures import PUBLIC_REASONS

ADAPTER = Path(__file__).resolve().parents[1]
FINDINGS = ADAPTER.parent / "blind-scan-findings.md"
STOP_LIST = ADAPTER.parents[1] / ".kiro" / "blind-scan" / "stop-list.txt"
ROW = re.compile(r"^\| `(?P<word>[^`]+)` \| `[^`]+` \| [^|]+ \| told set:(?P<line>\d+) \|$")


def _scanner() -> Scanner:
    return Scanner.from_config([ADAPTER / "scan_sources.toml"], STOP_LIST)


def _told_set_hits() -> set[tuple[str, int]]:
    text = declaration_text(scan_adapter().declaration()) + "\n"
    return {(word.lower(), text.count("\n", 0, start) + 1) for start, _, word in _scanner().find_terms(text)}


def _listed() -> set[tuple[str, int]]:
    rows = [
        ROW.match(line)
        for line in FINDINGS.read_text(encoding="utf-8").splitlines()
        if line.startswith("| `")
    ]
    assert all(rows), "a row of blind-scan-findings.md does not match the table format"
    return {(row["word"], int(row["line"])) for row in rows}


def test_told_set_hits_are_exactly_the_listed_findings():
    assert _told_set_hits() == _listed()


def test_scanner_derives_terms_from_every_kind_of_solver_file():
    terms = {name for name in _scanner().terms.values()}
    # a dictionary keyword, a patch name, a function-object name and a geometry-script name
    assert {"deltaT", "inlet", "forces", "Arc"} <= terms


def test_public_reasons_contain_no_derived_term():
    scanner = _scanner()
    for reason in PUBLIC_REASONS.values():
        assert scanner.find_terms(reason) == []
