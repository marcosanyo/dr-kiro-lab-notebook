"""Run bands on the committed records (task 15.1; Requirements 8.9, 9.1-9.7).

The facts asserted (body-2 R13 cites E10 and E11 with two parameter groups; wt-004 declares four number knobs)
are read from the sealed records listed in the requirements' introduction. They are checks of the drawing, not
results the notebook claims.
"""

from pathlib import Path

import pytest
from bench.specfiles.discovered import Row, Table

from notebook import bands, cli, records, tables, text, views
from notebook.bands import ABOVE, Hatch
from real.test_milestone_1_real import SESSIONS, _argv, _parse


@pytest.fixture(scope="module")
def by_session() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


def _table(record: records.RecordModel) -> Table:
    table = tables.read(record, tables.end_snapshot(record))
    assert isinstance(table, Table)
    return table


def _row(record: records.RecordModel, row_id: str) -> Row:
    (row,) = [r for r in _table(record).rows if r.id == row_id]
    return row


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("bands") / "site"
    assert cli.main(_argv(out)) == 0
    return out


def test_body_2_r13_has_two_parameter_groups_and_never_merges_them(by_session):
    body_2 = by_session["body-2"]
    groups = bands.row_bands(views.full(body_2), _row(body_2, "R13"))
    assert [g.names for g in groups] == [("a1", "s3", "f"), ("a1", "s3", "f", "sq")]
    assert [g.experiment.id for g in groups] == ["E10", "E11"]
    # `sq` is not one parameter of the first group: its bands are drawn only in the second.
    assert [b.name.text for b in groups[0].bands] == ["a1", "s3", "f"]
    assert [b.name.text for b in groups[1].bands] == ["a1", "s3", "f", "sq"]


def test_body_2_r13_ticks_are_the_recorded_values_of_each_group(by_session):
    body_2 = by_session["body-2"]
    groups = bands.row_bands(views.full(body_2), _row(body_2, "R13"))
    for group in groups:
        names = frozenset(group.names)
        session_trials = [t for t in body_2.trials if frozenset(p.name.text for p in t.params) == names]
        for band in group.bands:
            recorded = {p.value for t in session_trials for p in t.params if p.name.text == band.name.text}
            assert [tick.value for tick in band.ticks] == sorted(recorded)


def test_wt_004_number_knob_bands_span_the_declared_range(by_session):
    wt_004 = by_session["wt-004"]
    declared = {k.name: (k.low, k.high) for k in wt_004.declaration.knobs if k.kind == "number"}
    assert len(declared) == 4
    view = views.full(wt_004)
    checked = 0
    for row in _table(wt_004).rows:
        for group in bands.row_bands(view, row):
            for band in group.bands:
                assert band.knob == declared[band.name.text]
                assert band.span == declared[band.name.text]
                for hatch in band.hatched:
                    assert not any(hatch.holds(tick.value) for tick in band.ticks)
                checked += 1
    assert checked == 6 * 4


def test_wt_004_angle_has_its_untried_part_hatched_above_the_highest_tick(by_session):
    wt_004 = by_session["wt-004"]
    (group,) = bands.row_bands(views.full(wt_004), _row(wt_004, "R5"))
    (angle,) = [b for b in group.bands if b.name.text == "angle"]
    assert angle.hatched == (Hatch(8.0, 15.0, ABOVE),)


def test_a_row_with_no_cited_trial_has_no_group(by_session):
    body_2 = by_session["body-2"]
    row = _row(body_2, "R13")
    empty = Row(row.line, row.id, row.rule, row.scope, (), (), row.status, row.replaced_by)
    assert bands.row_bands(views.full(body_2), empty) == ()


def test_the_session_page_draws_the_bands_inside_the_scope_cell(site):
    page = _parse(site / "body-lab-body-2.html")
    (tr,) = [n for n in page.walk() if n.tag == "tr" and n.attrs.get("id") == "row-R13"]
    cells = [n for n in tr.elements() if n.tag == "td"]
    scope = cells[2]
    assert scope.text().startswith("a1 = -1, f 2")
    figure = scope.find("figure", "bands")
    assert text.BANDS_GROUP in figure.text()
    svgs = figure.find_all("svg", "band")
    assert len(svgs) == 7  # E10 declares 3 names and E11 declares 4
    for svg in svgs:
        assert "xmlns" not in svg.attrs
        assert not svg.find_all("text") and not svg.find_all("title")
        assert svg.attrs["aria-hidden"] == "true"
    links = figure.find_all("a")
    assert {a.attrs["href"] for a in links} == {"#E10-file", "#E11-file"}
    # Each parameter name keeps Dr. Kiro's ink (Requirement 9.7).
    by_name = {a.text(): a for a in links}
    assert set(by_name) == {"a1", "s3", "f", "sq"}
    for name, link in by_name.items():
        assert [n for n in link.elements() if "ink-k" in n.classes], name
    # Each link has its anchor on the same page.
    anchors = {n.attrs["id"] for n in page.walk() if "id" in n.attrs}
    assert {"E10-file", "E11-file"} <= anchors


def test_the_scope_cell_text_is_not_changed_by_the_bands(by_session, site):
    body_2 = by_session["body-2"]
    row = _row(body_2, "R13")
    page = _parse(site / "body-lab-body-2.html")
    (tr,) = [n for n in page.walk() if n.tag == "tr" and n.attrs.get("id") == "row-R13"]
    scope = [n for n in tr.elements() if n.tag == "td"][2]
    # The scope text is the first element of its cell, in Dr. Kiro's ink, exactly as written.
    assert scope.elements()[0].text() == row.scope
