"""The session page's sections after the table, on the committed records (task 12.1).

One full build of `sessions/` through the command line into `tmp_path`, once for this module. The assertions
read the written HTML. The ids, counts and texts asserted are facts of the sealed records listed in the
requirements' introduction and of the approved choice files (Decision 37), not results the notebook claims.
"""

from pathlib import Path

import pytest

from notebook import cli, numbers, records, text
from real.test_milestone_1_real import SESSIONS, Node, _argv, _parse

# Requirement 10.1: these sections first, in this order; the others follow.
SECTION_ORDER = ["table", "highlight", "progress", "plan", "experiments", "never-run", "refusals", "replay"]

# wt-003 (stopped, no snapshot) has the page of Requirement 14.6 instead of these sections, so the tests of
# the sections below leave it out; its page is checked in `test_stopped_real.py`.


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("session-page") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[str, records.RecordModel]:
    return {r.session: r for r in records.load(SESSIONS)}


def _page(site: Path, record: records.RecordModel) -> Node:
    return _parse(site / f"{record.application}-{record.session}.html")


def _sections(page: Node) -> list[str]:
    main = page.find("main", "page")
    return [n.attrs["id"] for n in main.elements() if n.tag == "section" and "id" in n.attrs]


def test_the_sections_come_in_the_order_of_requirement_10_1(site, loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        assert _sections(_page(site, record)) == SECTION_ORDER, record.name


def test_body_2_e5_shows_the_bench_flag_with_hit_0_and_miss_1(site, loaded):
    entry = _page(site, loaded["body-2"]).find("details", "entry", id="E5")
    (note,) = entry.find_all("aside", "bench-note")
    shown = note.text()
    assert shown.startswith(text.FLAG_NOTE)
    assert "hit 0" in shown and "miss 1" in shown
    verdict = entry.find("p", "verdict")
    assert verdict.text() == text.VERDICT_ON + "H5" + text.VERDICT_COLON + "partly"
    assert "ink-k" in verdict.elements()[-1].classes
    # No other entry of body-2 has a flag.
    assert len(_page(site, loaded["body-2"]).find_all("aside", "bench-note")) == 1


def test_the_wt_004_trial_with_five_not_settled_values_shows_names_and_reasons_and_no_number(site, loaded):
    record = loaded["wt-004"]
    (trial,) = [
        t
        for t in record.trials
        if sum(
            isinstance(v, records.NotMeasuredValue) and v.outcome == "not_settled" for _, v in t.measurements
        )
        == 5
    ]
    entry = _page(site, record).find("section", "trial", id=f"{trial.experiment}-{trial.id}")
    lists = entry.find_all("ul", "values")
    rounded, params_full, measured_full = lists
    for shown in (rounded, measured_full):
        items = [li.text() for li in shown.find_all("li")]
        assert len(items) == 5
        for (name, value), item in zip(trial.measurements, items, strict=True):
            assert (
                item
                == name + text.VALUE_SEPARATOR + "not_settled" + text.NOT_MEASURED_REASON + value.reason.text
            )
            assert not any(c.isdigit() for c in item.replace(name, ""))
    # The parameter values are numbers and are shown in full.
    assert [li.text() for li in params_full.find_all("li")] == [
        p.name.text + text.VALUE_SEPARATOR + numbers.full(p.value, "test") for p in trial.params
    ]
    assert entry.find_all("figure", "photo")


def test_every_experiment_trial_and_outcome_has_its_address(site, loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        page = _page(site, record)
        ids = {n.attrs["id"] for n in page.walk() if "id" in n.attrs}
        for experiment in record.experiments:
            entry = page.find("details", "entry", id=experiment.id)
            inner = {n.attrs["id"] for n in entry.walk() if "id" in n.attrs}
            assert f"{experiment.id}-file" in inner
            for tid in experiment.trials:
                assert f"{experiment.id}-{tid}" in inner
        for outcome in record.outcomes:
            assert f"{outcome.experiment}-{outcome.prediction}" in ids
        figures = page.find("section", "entries", id="experiments").find_all("figure", "photo")
        assert len(figures) == len(record.trials), record.name


def test_wt_002_predictions_never_run_have_their_own_addresses(site, loaded):
    page = _page(site, loaded["wt-002"])
    section = page.find("section", id="never-run")
    inner = {n.attrs["id"] for n in section.walk() if "id" in n.attrs and n is not section}
    assert inner == {"H2.P1", "H2.P2"}


def test_highlight_pictures_show_their_measured_values(site, loaded):
    record = loaded["body-2"]
    highlight = _page(site, record).find("section", "highlight", id="highlight")
    by_id = {t.id: t for t in record.trials}
    shown = highlight.find_all("section", "highlight-trial")

    # The approved choices (Decision 37): contrast T25 and T30, best T36.
    def trial_id(section: Node) -> str:
        return section.find("figure", "photo").find("figcaption").find("span", "ink-p").text()

    assert [trial_id(s) for s in shown] == ["T25", "T30", "T36"]
    for section in shown:
        trial = by_id[trial_id(section)]
        items = [li.text() for li in section.find("ul", "values").find_all("li")]
        expected = []
        for name, value in trial.measurements:
            if isinstance(value, tuple):
                expected.append(
                    name + text.VALUE_SEPARATOR + text.SERIES_OF + str(len(value)) + text.SERIES_SAMPLES
                )
            else:
                expected.append(name + text.VALUE_SEPARATOR + numbers.short(value, "test"))
        assert items == expected
    assert [n.text() for n in highlight.find_all("span", "block-label")] == [text.CHOSEN_BY_A_PERSON] * 2


def test_wt_002_highlight_shows_none_with_its_reason(site, loaded):
    highlight = _page(site, loaded["wt-002"]).find("section", "highlight", id="highlight")
    texts = [p.text() for p in highlight.find_all("p")]
    assert text.HIGHLIGHT_NONE + "no trial without shedding" in texts


def test_every_refusal_message_is_shown_with_its_quote_note(site, loaded):
    for record in loaded.values():
        if record.session == "wt-003":
            continue
        section = _page(site, record).find("section", id="refusals")
        items = section.find_all("li", "refusal")
        assert len(items) == len(record.refusals), record.name
        for item, refusal in zip(items, record.refusals, strict=True):
            notes = item.find_all("p", "quote-note")
            has_quote = any(p.is_quote for p in refusal.message)
            assert [n.text() for n in notes] == ([text.REFUSAL_QUOTE_NOTE] if has_quote else [])
            assert "".join(p.text.text for p in refusal.message) in item.text()


def test_progress_shows_budget_used_and_outcome_counts(site, loaded):
    record = loaded["body-2"]
    progress = _page(site, record).find("section", "progress", id="progress")
    assert progress.find_all("p")[0].text() == text.PROGRESS_BUDGET + "39" + text.BUDGET_OF + "40"
    counts = dict(
        li.text().split(text.VALUE_SEPARATOR) for li in progress.find("ul", "outcome-counts").find_all("li")
    )
    hits = sum(o.outcome == "hit" for o in record.outcomes)
    misses = sum(o.outcome == "miss" for o in record.outcomes)
    assert counts["hit"] == str(hits) and counts["miss"] == str(misses)
    assert hits + misses == 24


def test_every_fragment_link_of_the_real_site_resolves(site):
    """Every `#fragment` link of every page names an element id on its target page (Requirements 11.1-11.3):
    the cover's link to body-2's H4.P1 outcome, body-1's list of misses, the sticky notes, the progress."""
    pages = sorted(p.name for p in site.glob("*.html"))
    ids = {name: {n.attrs["id"] for n in _parse(site / name).walk() if "id" in n.attrs} for name in pages}
    checked = 0
    problems = []
    for name in pages:
        for a in _parse(site / name).find_all("a"):
            href = a.attrs.get("href", "")
            if "#" not in href:
                continue
            target, fragment = href.split("#", 1)
            target = target or name
            checked += 1
            if target not in ids or fragment not in ids[target]:
                problems.append(f"{name}: {href}")
    assert problems == []
    assert checked > 0
    # The opened rows' links (task 12.2) are among the links checked: every page with a readable table has
    # them, and they point into the experiment entries.
    for name in ("body-lab-body-2.html", "wind-tunnel-wt-004.html"):
        opened = [
            a.attrs["href"]
            for details in _parse(site / name).find_all("details", "evidence")
            for a in details.find_all("a")
        ]
        assert opened and all(h.startswith("#E") for h in opened), name
    assert "body-lab-body-2.html#E4-H4.P1" in {
        a.attrs.get("href") for a in _parse(site / "index.html").find_all("a")
    }
