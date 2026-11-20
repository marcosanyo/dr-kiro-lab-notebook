"""The reader's runs and requests on the committed files. The ids, results and the sentence asserted are
facts of the committed run files and the committed request, not results the notebook claims."""

import shutil
from pathlib import Path

import pytest

from notebook import readerrequest, readerruns
from notebook.errors import NotebookError

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
REQUESTS = ROOT / "build-from-spec" / "requests"


@pytest.fixture(scope="module")
def runs() -> list[readerruns.Run]:
    return readerruns.load(SESSIONS)


def test_the_twelve_committed_runs_load_in_request_setup_and_name_order(runs) -> None:
    assert [r.name for r in runs] == [
        "crawl-further-spec-1",
        "crawl-further-spec-2",
        "crawl-further-new-spec-3",
        "crawl-further-new-spec-4",
        "crawl-further-new-none-5",
        "crawl-further-new-none-6",
        "stop-ahead-spec-1",
        "stop-ahead-spec-2",
        "stop-ahead-record-1",
        "stop-ahead-record-2",
        "stop-ahead-none-1",
        "stop-ahead-none-2",
    ]
    assert {r.request_id for r in runs} == {"stop-ahead", "crawl-further", "crawl-further-new"}
    # The stop-ahead runs ran on the body their source session ran on; the crawl runs name body b.
    assert {r.variant for r in runs if r.request_id == "stop-ahead"} == {None}
    assert {r.variant for r in runs if r.request_id != "stop-ahead"} == {"b"}


def test_the_tally_counts_passes_per_setup(runs) -> None:
    assert readerruns.tally(runs, "stop-ahead") == [
        ("spec", 2, 2, {}),
        ("record", 1, 2, {}),
        ("none", 0, 2, {}),
    ]


def test_the_committed_request_matches_the_hash_the_runs_were_given(runs) -> None:
    requests = readerrequest.load(REQUESTS, runs)
    request = requests["stop-ahead"]
    assert request.application == "body-lab"
    assert request.words.startswith("Move ahead by about 0.45 m")
    assert [p.measurement for p in request.passes] == ["x", "heading", "y"]


def test_a_request_with_another_hash_is_refused_naming_both_hashes(runs, tmp_path: Path) -> None:
    shutil.copy(REQUESTS / "stop-ahead.toml", tmp_path / "stop-ahead.toml")
    with (tmp_path / "stop-ahead.toml").open("a", encoding="utf-8") as handle:
        handle.write("# changed after the runs\n")
    stop_ahead = [r for r in runs if r.request_id == "stop-ahead"]
    with pytest.raises(NotebookError) as caught:
        readerrequest.load(tmp_path, stop_ahead)
    assert stop_ahead[0].request_sha256 in str(caught.value)


def test_a_missing_request_is_refused_naming_the_file(runs, tmp_path: Path) -> None:
    with pytest.raises(NotebookError, match="stop-ahead.toml"):
        readerrequest.load(tmp_path, [r for r in runs if r.request_id == "stop-ahead"])


def test_a_stray_file_in_the_runs_folder_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "sessions"
    shutil.copytree(SESSIONS / "build-from-spec", folder / "build-from-spec")
    (folder / "build-from-spec" / "body-lab" / "notes.txt").write_text("x", encoding="utf-8")
    with pytest.raises(NotebookError, match="notes.txt"):
        readerruns.load(folder)


def test_a_run_file_with_another_seal_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "sessions"
    shutil.copytree(SESSIONS / "build-from-spec", folder / "build-from-spec")
    run_file = folder / "build-from-spec" / "body-lab" / "stop-ahead-none-1.run.json"
    text = run_file.read_text(encoding="utf-8")
    seal = next(r.seal for r in readerruns.load(SESSIONS) if r.name == "stop-ahead-none-1")
    assert seal in text
    run_file.write_text(text.replace(seal, "0" * 64), encoding="utf-8")
    with pytest.raises(NotebookError, match="seal"):
        readerruns.load(folder)


def test_the_folder_of_the_runs_is_optional_for_a_build_of_records_alone(tmp_path: Path) -> None:
    assert readerruns.load(tmp_path) == []


def test_every_committed_run_holds_its_budget_and_the_units_it_declares(runs) -> None:
    # The budget and the units come from each run's sealed start entry, not from the request file.
    assert {r.budget for r in runs} == {12}
    for run in runs:
        assert dict(run.units) == {
            "x": "m",
            "y": "m",
            "heading": "deg",
            "track_x": "m",
            "track_y": "m",
            "track_heading": "deg",
        }


def test_a_start_entry_without_a_budget_fails_the_notebook() -> None:
    start = {"kind": "start", "body": {"declaration": {"measurements": []}}}
    with pytest.raises(NotebookError):
        readerruns._start_limits(start, "run")
