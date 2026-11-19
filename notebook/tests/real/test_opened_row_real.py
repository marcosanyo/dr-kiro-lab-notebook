"""The opened row of the discovered spec table, on the committed records (task 12.2).

One full build of `sessions/` through the command line into `tmp_path`, once for this module. The ids asserted
(wt-004 R5 `partly` citing H5.P3, R6 `observed`) are facts of the sealed record listed in the requirements'
introduction, not results the notebook claims.
"""

from pathlib import Path

import pytest

from notebook import cli, records, text
from notebook.pages.session import UNTRIED_CLASSES
from real.test_milestone_1_real import SESSIONS, Node, _argv, _parse

# Requirement 8.6, word for word.
OBSERVED_CHECK = "seen in experiments; no cited prediction missed; Dr. Kiro does not claim validated"


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("opened-row") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def wt_004() -> records.RecordModel:
    (record,) = [r for r in records.load(SESSIONS) if r.session == "wt-004"]
    return record


def _body(site: Path, record: records.RecordModel) -> list[Node]:
    page = _parse(site / f"{record.application}-{record.session}.html")
    # One `tbody.spec-row` per row (a card); the rows of all of them, in table order.
    return [tr for tbody in page.find_all("tbody") for tr in tbody.elements() if tr.tag == "tr"]


def _opened(site: Path, record: records.RecordModel) -> dict[str, Node]:
    """Each row id -> the `<details class="evidence">` of the table row that follows it (after its note)."""
    out: dict[str, Node] = {}
    current = None
    for tr in _body(site, record):
        if tr.attrs.get("id", "").startswith("row-"):
            current = tr.attrs["id"][4:]
        elif "row-evidence" in tr.classes:
            assert current is not None and current not in out
            out[current] = tr.find("details", "evidence")
    return out


def _items(details: Node) -> list[Node]:
    return details.find("ul", "cited-predictions").find_all("li")


def test_every_row_has_one_opened_row_and_is_drawn_once(site, wt_004):
    trs = _body(site, wt_004)
    rows = [tr for tr in trs if tr.attrs.get("id", "").startswith("row-")]
    assert [tr.attrs["id"] for tr in rows] == [f"row-R{n}" for n in range(1, 7)]
    opened = _opened(site, wt_004)
    assert list(opened) == [f"R{n}" for n in range(1, 7)]
    for tr in trs:
        if "row-evidence" in tr.classes:
            assert "row-rejected" not in tr.classes
            assert not tr.find_all(cls="stamp")


def test_the_partly_row_shows_its_miss_h5_p3_in_miss_red(site, wt_004):
    details = _opened(site, wt_004)["R5"]
    items = _items(details)
    assert [li.find_all("a")[0].text() for li in items] == ["H5.P3", "H5.P4"]
    (miss,) = [o for o in wt_004.outcomes if o.prediction == "H5.P3"]
    assert miss.outcome == "miss"
    first, second = items
    assert first.find_all("a")[0].attrs["href"] == f"#{miss.experiment}-H5.P3"
    (word,) = first.find_all("span", "miss")
    assert word.text() == "miss"
    assert len(first.find_all("span", "miss-value")) == 1
    # The hit beside it has no miss red.
    assert not second.find_all(cls="miss") and not second.find_all(cls="miss-value")
    # Range, condition class and Dr. Kiro's label of the prediction are shown.
    shown = first.text()
    assert (
        text.PREDICTION_RANGE in shown and text.PREDICTION_CLASS in shown and text.PREDICTION_LABEL in shown
    )


def test_the_observed_row_shows_the_fixed_text(site, wt_004):
    assert text.STATUS_OBSERVED == OBSERVED_CHECK
    details = _opened(site, wt_004)["R6"]
    (note,) = details.find_all("p", "evidence-observed")
    assert note.text() == text.EVIDENCE_OBSERVED + OBSERVED_CHECK
    # R6 cites no prediction.
    assert text.EVIDENCE_PREDICTIONS_NONE in details.text()
    # No other row of wt-004 is `observed`, so no other row shows the text.
    others = [d for rid, d in _opened(site, wt_004).items() if rid != "R6"]
    assert all(not d.find_all("p", "evidence-observed") for d in others)


def test_validated_rows_list_exactly_their_untried_hits(site, wt_004):
    predictions = {p.id: p for h in wt_004.hypotheses for p in h.predictions}
    hits = {o.prediction for o in wt_004.outcomes if o.outcome == "hit"}
    for rid in ("R1", "R2", "R3", "R4"):
        details = _opened(site, wt_004)[rid]
        cited = [li.find_all("a")[0].text() for li in _items(details)]
        expected = [p for p in cited if p in hits and predictions[p].condition_class in UNTRIED_CLASSES]
        found = details.find_all("ul", "untried-hits")
        listed = [li.find_all("a")[0].text() for li in found[0].find_all("li")] if found else []
        assert listed == expected, rid
        if not expected:
            assert text.EVIDENCE_UNTRIED_NONE in details.text()
