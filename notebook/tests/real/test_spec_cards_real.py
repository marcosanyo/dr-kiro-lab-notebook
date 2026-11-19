"""The discovered spec table as cards, on the committed records.

One full build of `sessions/` through the command line into `tmp_path`, once for this module. The row ids and
counts asserted (body-2: 14 rows, 8 of them `rejected`; wt-004: 6 rows) are facts of the sealed records.
"""

from pathlib import Path

import pytest
from bench.specfiles.discovered import COLUMNS

from notebook import cli, text
from real.test_milestone_1_real import _argv, _parse

BODY_2_REJECTED = ["R2", "R3", "R4", "R6", "R8", "R10", "R12", "R14"]


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("spec-cards") / "site"
    assert cli.main(_argv(out)) == 0
    return out


def _cards(site: Path, page: str):
    root = _parse(site / page)
    return root, root.find_all("tbody", "spec-row")


def test_every_row_of_body_2_is_in_exactly_one_card_with_its_evidence_inside(site):
    root, cards = _cards(site, "body-lab-body-2.html")
    assert len(cards) == 14
    # Every tbody of the page is a card, and each card holds exactly one drawn row.
    assert len(root.find_all("tbody")) == 14
    assert [c.find_all("tr")[0].attrs["id"] for c in cards] == [f"row-R{n}" for n in range(1, 15)]
    for card in cards:
        drawn = [tr for tr in card.find_all("tr") if tr.attrs.get("id", "").startswith("row-")]
        assert len(drawn) == 1
        (evidence_row,) = card.find_all("tr", "row-evidence")
        assert len(evidence_row.find_all("details", "evidence")) == 1
        assert len(card.find_all("details", "evidence")) == 1
        # The row, then its note (if any), then its opened row: in this order, nothing else.
        kinds = [("row" if "id" in tr.attrs else next(iter(tr.classes))) for tr in card.elements()]
        assert kinds in (["row", "row-evidence"], ["row", "row-note", "row-evidence"])
    # The refused-end note is part of the card of R13 and of no other.
    assert [c.find_all("tr")[0].attrs["id"] for c in cards if c.find_all("tr", "row-note")] == ["row-R13"]


def test_the_card_carries_the_bench_state_word_as_its_class_and_rejected_cards_are_the_rejected_rows(site):
    _, cards = _cards(site, "body-lab-body-2.html")
    for card in cards:
        (stamp,) = [s for s in card.find_all("span") if "stamp" in s.classes]
        (state,) = [c for c in card.classes if c.startswith("st-")]
        assert state == "st-" + stamp.text()
        assert "rule-card" in card.classes
        assert "row-rejected" not in card.classes
    rejected = [c.find_all("tr")[0].attrs["id"][4:] for c in cards if "st-rejected" in c.classes]
    assert rejected == BODY_2_REJECTED
    for card in cards:
        row = card.find_all("tr")[0]
        assert ("row-rejected" in row.classes) == ("st-rejected" in card.classes)


def test_each_cell_caption_is_the_header_word_of_the_benchs_table(site):
    root, cards = _cards(site, "body-lab-body-2.html")
    headers = [th.text() for th in root.find("thead").find_all("th")]
    assert headers == list(COLUMNS)
    for card in cards:
        row = card.find_all("tr")[0]
        cells = [c for c in row.elements() if c.tag == "td"]
        assert [c.attrs["data-label"] for c in cells] == headers


def test_the_stamp_and_its_label_are_never_inside_the_struck_text(site):
    _, cards = _cards(site, "body-lab-body-2.html")
    struck = [c for c in cards if "st-rejected" in c.classes]
    assert len(struck) == 8
    for card in struck:
        row = card.find_all("tr")[0]
        assert "row-rejected" in row.classes
        for td in [c for c in row.elements() if c.tag == "td"]:
            held = td.find_all(cls="stamp") + td.find_all(cls="stamp-label")
            if "status" in td.classes:
                assert [n.text() for n in td.find_all(cls="stamp-label")] == [text.CHECKED]
                assert len(held) == 2
            else:
                assert held == [], "the stamp label is outside the struck cells"
        assert card.find_all("tr", "row-evidence")[0].find_all("td")[0].attrs["colspan"] == "7"


def test_each_rejected_card_has_one_open_replaced_by_tab_as_its_last_line(site):
    _, cards = _cards(site, "body-lab-body-2.html")
    for card in cards:
        tabs = card.find_all("details", "tab")
        if "st-rejected" not in card.classes:
            assert tabs == []
            continue
        (tab,) = tabs
        assert tab.attrs.get("open") == "open"
        cell = card.find_all("td")[6]
        assert cell.attrs["data-label"] == "replaced by" and "has-tab" in cell.classes
        assert cell.find_all("details", "tab") == [tab]
    empty = [c for c in cards if "st-rejected" not in c.classes]
    assert all("cell-empty" in c.find_all("td")[6].classes for c in empty)


def test_wt_004_draws_its_six_rows_as_six_cards(site):
    root, cards = _cards(site, "wind-tunnel-wt-004.html")
    assert len(cards) == len(root.find_all("tbody")) == 6
    assert [c.find_all("tr")[0].attrs["id"] for c in cards] == [f"row-R{n}" for n in range(1, 7)]
    for card in cards:
        assert len(card.find_all("details", "evidence")) == 1
        assert [n.text() for n in card.find_all(cls="stamp-label")] == [text.CHECKED]


def test_pages_without_a_table_have_no_card(site):
    for page in ("body-lab-body-1.html", "wind-tunnel-wt-002.html", "wind-tunnel-wt-003.html"):
        root = _parse(site / page)
        assert root.find_all("tbody") == [] and root.find_all("table") == []
