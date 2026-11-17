"""The prediction chart on the committed records (task 17.1; Requirements 5.4, 17.1-17.5).

The facts asserted (body-2 has 24 prediction outcomes; wt-004 has 17 registered predictions with one
miss, in E5) are read from the sealed records listed in the requirements' introduction. They check the chart,
not a result the notebook claims.
"""

from pathlib import Path

import pytest

from notebook import addresses, chart, cli, records, text, views
from real.test_milestone_1_real import SESSIONS, _argv, _parse


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("chart") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


def _progress(site: Path, record: records.RecordModel):
    page = _parse(site / f"{record.application}-{record.session}.html")
    (progress,) = [n for n in page.find_all("section", "progress")]
    return progress


def _figure(site: Path, record: records.RecordModel):
    (figure,) = _progress(site, record).find_all("figure", "chart")
    return figure


def _items(record: records.RecordModel) -> list[chart.Item]:
    return chart.items(views.full(record))


def test_body_2_has_24_outcomes_and_one_mark_for_each_hit_or_miss(loaded):
    record = loaded["body-2"]
    view = views.full(record)
    assert len(view.outcomes) == 24
    items = chart.items(view)
    kinds = [item.kind for item in items]
    assert sum(k in ("hit", "miss") for k in kinds) == sum(
        o.kind in ("hit", "miss") for o in view.state.outcomes.values()
    )
    assert len(items) == len(chart.registered(view))


def test_body_2_chart_shows_every_registered_range_and_one_mark_per_hit_or_miss(site, loaded):
    record = loaded["body-2"]
    figure = _figure(site, record)
    items = figure.find_all("li", "chart-item")
    assert len(items) == len(_items(record))
    assert len(figure.find_all("line", "range")) == len(items)
    marked = [item for item in _items(record) if item.value is not None]
    assert len(marked) == 24
    assert len(figure.find_all("circle", "mark")) == 24
    misses = [item for item in items if item.find_all("circle", "miss-mark")]
    assert len(misses) == sum(item.kind == "miss" for item in _items(record))


def test_body_2_chart_lists_predictions_in_registration_order(loaded):
    record = loaded["body-2"]
    expected = [p.id for h in record.hypotheses for p in h.predictions]
    assert [item.prediction.id for item in _items(record)] == expected


def test_wt_004_chart_has_17_predictions_with_one_miss_in_e5(site, loaded):
    record = loaded["wt-004"]
    items = _items(record)
    assert len(items) == 17
    misses = [item for item in items if item.kind == "miss"]
    assert len(misses) == 1
    (miss,) = misses
    assert miss.prediction.id == "H5.P3"
    assert miss.target.startswith("E5-")
    figure = _figure(site, record)
    (miss_mark,) = figure.find_all("circle", "miss-mark")
    assert miss_mark is not None
    word = [n for n in figure.walk() if n.tag == "span" and "miss" in n.classes and n.text() == "miss"]
    assert word, "the miss is shown with the word miss"


def test_a_prediction_never_run_is_drawn_as_its_range_only_and_links_to_its_address(loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        for item in _items(record):
            if item.kind == "not-run":
                assert item.outcome is None
                assert item.value is None
                assert item.target == addresses.never_run(item.prediction.id, "check")
            else:
                assert item.outcome is not None
                assert item.target == addresses.outcome(item.outcome.experiment, item.prediction.id, "check")


def test_every_measurement_scale_spans_its_bounds_and_its_values(loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        items = _items(record)
        for item in items:
            name = item.prediction.measurement
            same = [i for i in items if i.prediction.measurement == name]
            values = [i.prediction.low for i in same] + [i.prediction.high for i in same]
            values += [i.value for i in same if i.value is not None]
            assert item.scale == (min(values), max(values)), record.name


def test_the_chart_is_in_the_progress_section_and_shows_no_text_element(site, loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        figure = _figure(site, record)
        assert figure.find_all("text") == []
        assert figure.find_all("svg", "chart-mark"), record.name
        assert text.CHART_INTRO in figure.text()
        assert text.CHART_HEADING not in figure.text()


def test_body_1_has_no_table_but_its_chart_still_shows_its_predictions(site, loaded):
    record = loaded["body-1"]
    assert len(_items(record)) == len([p for h in record.hypotheses for p in h.predictions])
    assert len(_figure(site, record).find_all("li", "chart-item")) == len(_items(record))
