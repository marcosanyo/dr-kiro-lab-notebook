"""Unit tests for the relied-on line (design 3.7, Requirement 10), on the sealed sample record body-2 and on
small sealed records made in a temporary folder."""

from pathlib import Path
from typing import Any

import pytest
from bench.record.chain import BLOB_DIR, verify
from bench.record.store import Store, authored

from build_from_spec.relied import (
    PREFIX,
    PROBLEMS,
    Relied,
    ReliedError,
    allowed_ids,
    format_ids,
    parse_ids,
    relied_line,
    relied_on,
)

ROOT = Path(__file__).resolve().parents[2]
BODY2 = ROOT / "sessions" / "body-lab" / "body-2"
LINE = "# relies on: none"
PREDICTION_OPEN = "```prediction\n"
DESIGN_WITH_TABLE = """# Design

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|----|------|-------|-------------|-------------|--------|-------------|
| R1 | a rule | all | E1 | P1 | observed | - |
| R2 | another rule | all | E2 | P1 | observed | - |
"""


def sample_entries() -> list[dict[str, Any]]:
    return verify(BODY2, sealed=True)


def h1_frozen(entries: list[dict[str, Any]], folder: Path) -> str:
    register = next(e for e in entries if e["kind"] == "register" and e["body"]["hypothesis"] == "H1")
    return (folder / BLOB_DIR / register["body"]["frozen"]["blob"]).read_text(encoding="utf-8")


def with_line(frozen: str, line: str) -> str:
    """The frozen part with one line placed first inside its prediction block."""
    assert PREDICTION_OPEN in frozen
    return frozen.replace(PREDICTION_OPEN, PREDICTION_OPEN + line + "\n", 1)


def sealed_record(
    folder: Path,
    design: str,
    *,
    ended: bool = True,
    requirements: str = "# Requirements\n",
    tasks: str = "# Tasks\n",
) -> Path:
    """A sealed record whose end snapshot holds the three given spec files. Without `ended`, no snapshot."""
    store = Store.create(folder)
    if ended:
        files = {
            key: store.put_blob(text.encode("utf-8"), "dr-kiro", "text/markdown")
            for key, text in (
                ("requirements", requirements),
                ("design", design),
                ("tasks", tasks),
            )
        }
        store.append("snapshot", {"for": "end", "files": files})
    store.append(
        "seal",
        {"end": "ended" if ended else "stopped", "reason": authored("bench", "test"), "budget_remaining": 0},
    )
    store.close()
    (folder / ".lock").unlink()  # the lock file of this temporary record; a sealed record has none
    return folder


def test_spec_setup_allows_none_and_the_rule_rows_of_the_final_spec() -> None:
    allowed = allowed_ids("spec", BODY2)
    assert {f"R{n}" for n in range(1, 15)} <= allowed
    assert "none" in allowed
    assert all(identifier == "none" or identifier[0] in "RHE" for identifier in allowed)


def test_record_setup_allows_the_registered_hypotheses_and_the_experiments_and_none() -> None:
    expected = {"none", *(f"H{n}" for n in range(1, 12)), *(f"E{n}" for n in range(1, 12))}
    assert allowed_ids("record", BODY2) == frozenset(expected)


def test_none_setup_allows_only_none_and_reads_no_source() -> None:
    assert allowed_ids("none", Path("/does/not/exist")) == frozenset({"none"})


def test_unknown_setup_fails_by_name(tmp_path: Path) -> None:
    with pytest.raises(ReliedError, match="unknown setup 'both'"):
        allowed_ids("both", sealed_record(tmp_path / "source", DESIGN_WITH_TABLE))


def test_spec_source_without_end_snapshot_fails(tmp_path: Path) -> None:
    source = sealed_record(tmp_path / "source", DESIGN_WITH_TABLE, ended=False)
    with pytest.raises(ReliedError, match="no end snapshot"):
        allowed_ids("spec", source)


def test_spec_source_allows_the_ids_that_appear_in_the_three_given_files(tmp_path: Path) -> None:
    source = sealed_record(
        tmp_path / "source",
        DESIGN_WITH_TABLE,  # R1, R2 and E1, E2 in the table
        requirements="The rule R3 and the hypothesis H2 hold.\n",
        tasks="Check E9 and R10, and R10 again.\n",
    )
    assert allowed_ids("spec", source) == frozenset({"none", "R1", "R2", "R3", "R10", "H2", "E1", "E2", "E9"})


def test_spec_source_matches_ids_only_as_whole_words(tmp_path: Path) -> None:
    source = sealed_record(
        tmp_path / "source",
        "# Design\n\nXR5 and ER1 and R0 and E01 are not ids. R7x and R7.2 are: R7 and H12.\n",
    )
    assert allowed_ids("spec", source) == frozenset({"none", "R7", "H12"})


def test_spec_id_in_the_given_files_is_accepted_and_an_absent_one_is_refused(tmp_path: Path) -> None:
    source = sealed_record(tmp_path / "source", DESIGN_WITH_TABLE, tasks="see E9\n")
    allowed = allowed_ids("spec", source)
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), "# relies on: E9, R99")
    assert relied_on(entries, frozen, allowed) == Relied(("E9", "R99"), "unknown-id")
    frozen_ok = with_line(h1_frozen(entries, BODY2), "# relies on: E9, R2")
    assert relied_on(entries, frozen_ok, allowed) == Relied(("E9", "R2"), None)


def test_first_line_that_is_not_the_relied_on_line_means_no_line() -> None:
    frozen = with_line(h1_frozen(sample_entries(), BODY2), "# uses: none")
    assert relied_line(frozen) is None
    assert relied_on(sample_entries(), frozen, frozenset({"none"})) == Relied(None, "no-line")


def test_relied_line_is_read_byte_for_byte() -> None:
    frozen = with_line(h1_frozen(sample_entries(), BODY2), LINE)
    assert relied_line(frozen) == LINE


def test_frozen_part_without_a_prediction_fence_has_no_line() -> None:
    assert relied_line("### H1: title\n\nWHEN a thing, THE system SHALL respond.\n") is None


def test_parse_ids_reads_none_and_lists_of_ids() -> None:
    assert parse_ids("# relies on: none") == ("none",)
    assert parse_ids("# relies on: R1") == ("R1",)
    assert parse_ids("# relies on: R1,R2") == ("R1", "R2")
    assert parse_ids("# relies on: H1,  E2,E3") == ("H1", "E2", "E3")


@pytest.mark.parametrize(
    "line",
    [
        "# relies on",
        "# relies on:",
        "# relies on: ",
        "# relies on:none",
        "# relies on: none, R1",
        "# relies on: R1,R1",
        "# relies on: R1,",
        "# relies on: R1 ,R2",
        "# relies on: R1 ",
        "# relies on: R1 R2",
        "# depends on: R1",
        " # relies on: R1",
    ],
)
def test_parse_ids_refuses_bad_syntax(line: str) -> None:
    assert parse_ids(line) is None


def test_format_ids_is_the_inverse_of_parse_ids() -> None:
    assert format_ids(("none",)) == PREFIX + "none"
    assert format_ids(("R1", "R2")) == "# relies on: R1, R2"
    assert parse_ids(format_ids(("H1", "E2"))) == ("H1", "E2")


def test_no_registered_h1_is_the_first_problem() -> None:
    entries = [e for e in sample_entries() if e["kind"] != "register" or e["body"]["hypothesis"] != "H1"]
    assert relied_on(entries, "# relies on: R99\n", frozenset({"none"})) == Relied(None, "no-h1")


def test_missing_line_problem_is_no_line() -> None:
    entries = sample_entries()
    frozen = h1_frozen(entries, BODY2)
    assert relied_on(entries, frozen, frozenset({"none"})) == Relied(None, "no-line")


def test_bad_syntax_problem() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), "# relies on: none, R1")
    assert relied_on(entries, frozen, frozenset({"none", "R1"})) == Relied(None, "bad-syntax")


def test_unknown_id_keeps_the_ids_found() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), "# relies on: R1, R99")
    assert relied_on(entries, frozen, frozenset({"none", "R1"})) == Relied(("R1", "R99"), "unknown-id")


def test_late_problem_when_an_experiment_comes_before_h1() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), LINE)
    early = [dict(e, seq=0) if e["kind"] == "experiment" else e for e in entries]
    assert relied_on(early, frozen, frozenset({"none"})) == Relied(("none",), "late")


def test_unknown_id_is_reported_before_late() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), "# relies on: R99")
    early = [dict(e, seq=0) if e["kind"] == "experiment" else e for e in entries]
    assert relied_on(early, frozen, frozenset({"none"})) == Relied(("R99",), "unknown-id")


def test_valid_line_gives_no_problem() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), LINE)
    assert relied_on(entries, frozen, frozenset({"none"})) == Relied(("none",), None)


def test_valid_line_naming_allowed_rows_gives_no_problem() -> None:
    entries = sample_entries()
    frozen = with_line(h1_frozen(entries, BODY2), "# relies on: R1, R3")
    allowed = allowed_ids("spec", BODY2)
    assert relied_on(entries, frozen, allowed) == Relied(("R1", "R3"), None)


def test_registered_h1_without_frozen_text_fails() -> None:
    with pytest.raises(ReliedError, match="frozen part was not given"):
        relied_on(sample_entries(), None, frozenset({"none"}))


def test_problems_are_in_the_design_order() -> None:
    assert PROBLEMS == ("no-h1", "no-line", "bad-syntax", "unknown-id", "late")
