import pytest

from bench.core.outcome import Quote
from bench.specfiles.discovered import Evidence, check_table, parse_table

FILE = "design.md"
EVIDENCE = Evidence(
    experiments=frozenset({"E1", "E2", "E3"}),
    predictions={
        "H1.P1": ("hit", "inside"),
        "H1.P2": ("hit", "not-comparable"),
        "H2.P1": ("hit", "outside"),
        "H2.P2": ("hit", "new-combination"),
        "H3.P1": ("miss", "outside"),
        "H3.P2": ("miss", "inside"),
        "H4.P1": ("not-run", "outside"),
        "H4.P2": ("not-checkable", "inside"),
    },
)

HEAD = "# Design\n\n## Notes\n\nSome notes.\n\n## Discovered spec\n\nRules found.\n\n"
HEADER = (
    "| id | rule | scope | experiments | predictions | status | replaced by |\n"
    "|---|---|---|---|---|---|---|\n"
)


def doc(*rows: str, tail: str = "") -> str:
    return HEAD + HEADER + "".join(r + "\n" for r in rows) + tail


def problems(*rows: str) -> list[str]:
    return [m.plain() for m in check_table(doc(*rows), EVIDENCE, FILE)]


def test_parse() -> None:
    text = doc("| R1 | a \\| b | everywhere | E1, E2 | H2.P1 | validated |  |")
    (row,) = parse_table(text, FILE).rows
    assert row.rule == "a | b" and row.experiments == ("E1", "E2") and row.predictions == ("H2.P1",)
    assert (
        row.line
        == text.split("\n").index("| R1 | a \\| b | everywhere | E1, E2 | H2.P1 | validated |  |") + 1
    )


@pytest.mark.parametrize(
    "row",
    [
        "| R1 | r | s | E1 | | observed | |",
        "| R1 | r | s | E1 | H1.P1, H1.P2 | observed | |",
        "| R1 | r | s | E1 | H4.P2 | observed | |",
        "| R1 | r | s | E1 | H2.P1 | validated | |",
        "| R1 | r | s | E1 | H1.P1, H2.P2 | validated | |",
        "| R1 | r | s | E1 | H2.P1, H3.P1 | partly | |",
        "| R1 | r | s | E1 | H1.P1, H3.P2 | partly | |",
    ],
)
def test_rows_that_agree_with_the_record(row: str) -> None:
    assert problems(row) == []


def test_rejected_with_replacement() -> None:
    assert (
        problems(
            "| R1 | r | s | E1 | H3.P1 | rejected | R2 |",
            "| R2 | r2 | s | E2 | H2.P1 | validated | |",
        )
        == []
    )


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("| R1 | r | s | E1 | H1.P1 | validated | |", "new combination or outside"),
        ("| R1 | r | s | E1 | H1.P2 | validated | |", "new combination or outside"),
        ("| R1 | r | s | E1 | H1.P1, H1.P2 | validated | |", "new combination or outside"),
        ("| R1 | r | s | E1 | | validated | |", "at least one prediction"),
        ("| R1 | r | s | E1 | H2.P1, H4.P1 | validated | |", "must be a hit"),
        ("| R1 | r | s | E1 | H2.P1, H3.P1 | validated | |", "must be a hit"),
        ("| R1 | r | s | E1 | H2.P1 | observed | |", "cannot cite a prediction on untried conditions"),
        ("| R1 | r | s | E1 | H4.P1 | observed | |", "cannot cite a prediction on untried conditions"),
        ("| R1 | r | s | E1 | H3.P2 | observed | |", "missed prediction"),
        ("| R1 | r | s | E1 | H2.P1, H2.P2 | partly | |", "at least one hit and at least one miss"),
        ("| R1 | r | s | E1 | H2.P1 | rejected | R1 |", "at least one miss"),
        ("| R1 | r | s | E1 | H3.P1 | rejected | |", "names the id"),
        ("| R1 | r | s | E1 | H3.P1 | rejected | R1 |", "not another row"),
        ("| R1 | r | s | E1 | H3.P1 | rejected | R9 |", "not another row"),
        ("| R1 | r | s | E1 | H2.P1 | validated | R2 |", "only a rejected rule"),
        ("| R1 | r | s | E9 | | observed | |", "experiment E9 is not in the record"),
        ("| R1 | r | s | | | observed | |", "experiments cell is empty"),
        ("| R1 | r | s | E1 | H9.P1 | observed | |", "H9.P1 is not in the record"),
        ("| R1 | r | s | E1 | P1 | observed | |", "not an id like H1.P1"),
        ("| R1 | | s | E1 | | observed | |", "rule cell is empty"),
        ("| R1 | r | | E1 | | observed | |", "scope cell is empty"),
        ("| R1 | r | s | E1 | | true | |", "status must be one of"),
        ("| 1 | r | s | E1 | | observed | |", "id must be R<n>"),
        ("| R1 | r | s | E1 | observed | |", "needs 7 cells"),
    ],
)
def test_rows_that_disagree(row: str, expected: str) -> None:
    found = problems(row)
    assert any(expected in p for p in found), found
    assert all(p.startswith(f"{FILE} line ") for p in found)


def test_duplicate_row_ids() -> None:
    assert problems("| R1 | r | s | E1 | | observed | |") == []
    found = problems("| R1 | r | s | E1 | | observed | |", "| R1 | r | s | E2 | | observed | |")
    assert any("used twice" in p for p in found)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Design\n\n## Notes\n", "must end with a `## Discovered spec` section"),
        (HEAD + HEADER + "| R1 | r | s | E1 | | observed | |\n\n## After\n", "must end with"),
        (HEAD + "No table yet.\n", "has no table"),
        (HEAD + HEADER, "has no rules"),
        (doc("| R1 | r | s | E1 | | observed | |", tail="\nMore text.\n"), "nothing but white space"),
        (
            HEAD + "| id | rule | scope | experiments | predictions | status |\n|---|---|---|---|---|---|\n",
            "columns",
        ),
        (HEAD + HEADER.split("\n")[0] + "\n| R1 | r | s | E1 | | observed | |\n", "separator"),
    ],
)
def test_table_shape(text: str, expected: str) -> None:
    (only,) = check_table(text, EVIDENCE, FILE)
    assert expected in only.plain()


def test_headings_in_code_fences_do_not_count() -> None:
    text = doc("| R1 | r | s | E1 | | observed | |")
    fenced = text.replace("Rules found.", "```\n## Not a heading\n```")
    assert check_table(fenced, EVIDENCE, FILE) == []
    trailing = HEAD + HEADER + "| R1 | r | s | E1 | | observed | |\n\n   \n"
    assert check_table(trailing, EVIDENCE, FILE) == []


def test_dr_kiro_ids_are_quoted() -> None:
    (msg,) = check_table(doc("| R1 | r | s | E9 | | observed | |"), EVIDENCE, FILE)
    quoted = {s.text for s in msg.spans if isinstance(s, Quote)}
    assert quoted == {"R1", "E9"}
