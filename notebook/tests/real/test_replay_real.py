"""The replay steps and their pages on the committed records.

Task 18.1; Requirements 16.1-16.10, 16.12 and 22.3.

One full build of `sessions/` through the command line into `tmp_path`, once for this module. The step counts
and the table rows asserted are facts of the sealed records (the requirements' introduction), not results the
notebook claims.
"""

from pathlib import Path

import pytest
from bench.specfiles.discovered import TableError, parse_table

from notebook import addresses, cli, records, tables, text, views
from real.test_milestone_1_real import SESSIONS, _argv, _parse

# Requirement 16.1 on the real records: one step per verdict snapshot, plus the accepted end snapshot.
STEP_COUNTS = {
    ("body-lab", "body-1"): 11,  # 11 verdicts, no end snapshot
    ("body-lab", "body-2"): 12,  # 11 verdicts and the end snapshot
    ("wind-tunnel", "wt-002"): 1,  # one verdict, stopped
    ("wind-tunnel", "wt-003"): 0,  # no snapshot
    ("wind-tunnel", "wt-004"): 7,  # 6 verdicts and the end snapshot
}


# The replay pages are not in this version (Decision 48): tests that read a replay page are skipped.
NOT_IN_THIS_VERSION = pytest.mark.skip(reason="not in this version, Decision 48")


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("replay-real") / "site"
    assert cli.main(_argv(out)) == 0
    return out


@pytest.fixture(scope="module")
def loaded() -> dict[tuple[str, str], records.RecordModel]:
    return {(r.application, r.session): r for r in records.load(SESSIONS)}


def _step_path(site: Path, record: records.RecordModel, number: int) -> Path:
    return site / addresses.replay(record.application, record.session, number, record.name)


def _labels(page) -> set[str]:
    return {node.text() for node in page.find_all("span", "stamp-label")}


def test_the_steps_of_the_real_records_are_as_the_requirements_count_them(loaded):
    assert {key: len(views.steps(r)) for key, r in loaded.items()} == STEP_COUNTS


def test_every_real_step_table_is_the_bench_readers_table_of_its_snapshot(loaded):
    for record in loaded.values():
        for step in views.steps(record):
            snapshot = step.snapshot
            read = tables.read(record, snapshot)
            source = snapshot.design.text().text
            if isinstance(read, tables.Unreadable):
                with pytest.raises(TableError):
                    parse_table(source, tables.design_file(record))
            else:
                assert read.rows == parse_table(source, tables.design_file(record)).rows, record.name


@NOT_IN_THIS_VERSION
def test_every_step_page_is_a_replay_of_a_sealed_record_with_its_controls(site, loaded):
    for record in loaded.values():
        steps = views.steps(record)
        session_page = addresses.session(record.application, record.session, record.name)
        for step in steps:
            page = _parse(_step_path(site, record, step.number))
            assert text.REPLAY_LABEL in page.text()
            back = page.find_all("a", **{"data-replay": "back"})
            assert len(back) == 1
            expected_back = (
                session_page
                if step.number == 1
                else addresses.replay(record.application, record.session, step.number - 1, record.name)
            )
            assert back[0].attrs["href"] == expected_back
            forward = page.find_all("a", **{"data-replay": "forward"})
            if step.number == len(steps):
                assert forward == []
            else:
                nxt = addresses.replay(record.application, record.session, step.number + 1, record.name)
                assert forward[0].attrs["href"] == nxt
                assert page.find_all("a", **{"data-replay": "play"})[0].attrs["href"] == nxt + "?play=1"


@NOT_IN_THIS_VERSION
def test_the_session_page_links_every_step(site, loaded):
    for record in loaded.values():
        if not views.steps(record):
            continue
        shown = (site / addresses.session(record.application, record.session, record.name)).read_text(
            encoding="utf-8"
        )
        for step in views.steps(record):
            name = addresses.replay(record.application, record.session, step.number, record.name)
            assert f'href="{name}"' in shown, (record.name, step.number)


@NOT_IN_THIS_VERSION
def test_body_2_has_the_refusals_of_the_end_step_only_after_e11(site, loaded):
    record = loaded[("body-lab", "body-2")]
    before_end = _parse(_step_path(site, record, 11))
    end = _parse(_step_path(site, record, 12))
    # The register refusal (entry 2) is an event of step 1, the first step after it, and of no later
    # step. The two end refusals (entries 122 and 123) come after the E11 verdict step (entry 121), so
    # they are events of the end step only (Requirement 16.12, Property 9).
    first = _parse(_step_path(site, record, 1))
    assert len(first.find_all("li", "refusal")) == 1
    assert len(before_end.find_all("li", "refusal")) == 0
    assert len(end.find_all("li", "refusal")) == 2


@NOT_IN_THIS_VERSION
def test_body_2_middle_steps_are_not_yet_checked_and_the_end_step_is_checked(site, loaded):
    record = loaded[("body-lab", "body-2")]
    middle = _parse(_step_path(site, record, 1))
    assert _labels(middle) == {text.NOT_YET_CHECKED}
    assert text.UNREADABLE in middle.text()
    end = _parse(_step_path(site, record, 12))
    assert _labels(end) == {text.CHECKED}
    assert len(end.find_all("td", "status")) == 14


@NOT_IN_THIS_VERSION
def test_wt_004_end_step_has_its_six_rows_checked_and_its_middle_steps_not_yet(site, loaded):
    record = loaded[("wind-tunnel", "wt-004")]
    assert len(_parse(_step_path(site, record, 7)).find_all("td", "status")) == 6
    assert _labels(_parse(_step_path(site, record, 7))) == {text.CHECKED}
    assert _labels(_parse(_step_path(site, record, 1))) == {text.NOT_YET_CHECKED}


@NOT_IN_THIS_VERSION
def test_chosen_items_not_yet_run_are_left_out_with_their_commentary(site, loaded):
    record = loaded[("body-lab", "body-2")]
    first = _parse(_step_path(site, record, 1))
    end = _parse(_step_path(site, record, 12))
    assert text.REPLAY_NOT_RUN in first.text()
    assert text.REPLAY_NOT_RUN not in end.text()
