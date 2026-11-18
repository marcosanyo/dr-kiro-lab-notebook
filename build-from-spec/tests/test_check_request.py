"""bfs-check-request: the format, the blind scan and the source check (Requirement 3, task 6.4).

The committed requests are checked against the sealed record sessions/body-lab/body-2. The test
reads that record and never writes it. The fake application's records are made in a temporary
folder with the bench's own store.
"""

from pathlib import Path

import pytest
from bench.record.store import Store, authored

from build_from_spec.apps import APPS, App
from build_from_spec.request import (
    RequestError,
    check_main,
    check_request,
    parse_request,
    source_trials_inside,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUESTS = REPO_ROOT / "build-from-spec" / "requests"
BODY_2 = REPO_ROOT / "sessions" / "body-lab" / "body-2"
STOP_LIST = Path(".kiro/blind-scan/stop-list.txt")
FAKE = {
    "fake": App("fake", "bench.fake.adapter:FakeAdapter", "bench/src/bench/fake/scan_sources.toml", 5, False)
}
# A blind-scan term of the fake application that is not on the stop list, and not a declared name.
PLANTED = "wobbet"

EXPECTED_BODY_2 = {
    "stop-ahead": [],
    "straight-ahead": ["T31", "T34", "T35", "T37", "T38", "T39"],
    "turn-right": ["T19", "T25", "T29"],
}


@pytest.fixture
def at_root(monkeypatch):
    monkeypatch.chdir(REPO_ROOT)


def fake_record(state: Path, trials: list[dict], counted: tuple[str, ...]) -> Path:
    """A sealed record made with the bench's own store. `counted` lists the experiments that have
    the snapshot that counts."""
    state.mkdir(parents=True, exist_ok=True)
    folder = state / "record"
    store = Store.create(folder)
    for body in trials:
        store.append("trial", body)
    for experiment in counted:
        store.append("snapshot", {"for": "experiment", "experiment": experiment, "files": {}})
    store.append("seal", {"end": "ended", "budget_remaining": 0, "reason": authored("bench", "ended")})
    store.close()
    (folder / ".lock").unlink()  # the lock file is state only; a sealed record does not hold it
    return folder


def trial(number: str, experiment: str, distance, turn) -> dict:
    return {
        "trial": number,
        "experiment": experiment,
        "measurements": {"distance": distance, "turn": turn},
    }


def write_request(folder: Path, name: str, passes: str, words: str = "Move a little.") -> Path:
    path = folder / f"{name}.toml"
    path.write_text(
        f'id = "{name}"\napplication = "fake"\nwords = "{words}"\n\n{passes}',
        encoding="utf-8",
    )
    return path


DISTANCE_TURN = (
    '[[pass]]\nmeasurement = "distance"\nrange = [0.5, 1.0]\n\n'
    '[[pass]]\nmeasurement = "turn"\nrange = [-0.2, 0.2]\n'
)


@pytest.mark.parametrize("name", sorted(EXPECTED_BODY_2))
def test_committed_request_results_against_body_2(at_root, name):
    request = parse_request(REQUESTS / f"{name}.toml", APPS)
    assert source_trials_inside(request, BODY_2) == EXPECTED_BODY_2[name]


@pytest.mark.parametrize("name", sorted(EXPECTED_BODY_2))
def test_check_request_lists_each_trial_of_each_committed_request(at_root, name):
    lines = check_request(REQUESTS / f"{name}.toml", BODY_2, APPS, STOP_LIST)
    assert len(lines) == len(EXPECTED_BODY_2[name])
    for number in EXPECTED_BODY_2[name]:
        assert any(f"trial {number} of" in line and f"{name}.toml" in line for line in lines)


def test_stop_ahead_passes_and_changes_no_file(at_root, capsys):
    request = REQUESTS / "stop-ahead.toml"
    log = BODY_2 / "log.jsonl"
    before = (request.read_bytes(), log.read_bytes(), sorted(p.name for p in BODY_2.iterdir()))
    check_main([str(request), "--source", str(BODY_2)])
    assert capsys.readouterr().out == "no findings\n"
    after = (request.read_bytes(), log.read_bytes(), sorted(p.name for p in BODY_2.iterdir()))
    assert after == before


def test_straight_ahead_is_refused_with_its_six_trials(at_root, capsys):
    with pytest.raises(SystemExit) as exited:
        check_main([str(REQUESTS / "straight-ahead.toml"), "--source", str(BODY_2)])
    assert exited.value.code == 1
    out = capsys.readouterr().out
    for number in EXPECTED_BODY_2["straight-ahead"]:
        assert f"trial {number} of" in out
    assert "no findings" not in out


def test_source_argument_is_required(at_root, capsys):
    with pytest.raises(SystemExit) as exited:
        check_main([str(REQUESTS / "stop-ahead.toml")])
    assert exited.value.code == 2
    assert "--source" in capsys.readouterr().err


def test_source_that_does_not_verify_is_refused_naming_the_path(at_root, tmp_path):
    with pytest.raises(RequestError) as refused:
        source_trials_inside(parse_request(REQUESTS / "stop-ahead.toml", APPS), tmp_path)
    assert str(tmp_path) in str(refused.value)
    assert "does not verify" in str(refused.value)


def test_a_trial_inside_every_range_of_a_fake_source_is_refused(at_root, tmp_path):
    source = fake_record(
        tmp_path / "state",
        [
            trial("T1", "E1", 0.6, 0.1),  # counted, inside both ranges
            trial("T2", "E2", 0.7, 0.1),  # not counted: no experiment snapshot
            trial("T3", "E1", 0.9, {"not_measured": "lost", "reason": "x"}),  # not measured: outside
            trial("T4", "E1", 0.2, 0.1),  # distance outside
        ],
        counted=("E1",),
    )
    path = write_request(tmp_path, "fake-go", DISTANCE_TURN)
    assert source_trials_inside(parse_request(path, FAKE), source) == ["T1"]


def test_a_request_with_no_trial_inside_passes_the_source_check(at_root, tmp_path):
    source = fake_record(tmp_path / "state", [trial("T1", "E1", 0.1, 0.0)], counted=("E1",))
    path = write_request(tmp_path, "fake-far", DISTANCE_TURN)
    assert check_request(path, source, FAKE, STOP_LIST) == []


def test_a_counted_trial_missing_a_named_measurement_fails_naming_it(at_root, tmp_path):
    body = {"trial": "T9", "experiment": "E1", "measurements": {"distance": 0.6}}
    source = fake_record(tmp_path / "state", [body], counted=("E1",))
    path = write_request(tmp_path, "fake-go", DISTANCE_TURN)
    with pytest.raises(RequestError) as refused:
        source_trials_inside(parse_request(path, FAKE), source)
    assert "trial T9" in str(refused.value)
    assert "'turn'" in str(refused.value)


def test_a_planted_term_in_words_is_found_at_its_line(at_root, tmp_path):
    path = write_request(tmp_path, "fake-go", DISTANCE_TURN, words=f"Move {PLANTED} a little.")
    source = fake_record(tmp_path / "state", [trial("T1", "E1", 0.1, 0.0)], counted=("E1",))
    lines = check_request(path, source, FAKE, REPO_ROOT / STOP_LIST)
    assert lines == [f"{path}:3: term: {PLANTED}"]


def test_a_planted_term_in_the_id_is_found_at_its_line(at_root, tmp_path):
    name = f"{PLANTED}-go"
    path = write_request(tmp_path, name, DISTANCE_TURN)
    source = fake_record(tmp_path / "state", [trial("T1", "E1", 0.1, 0.0)], counted=("E1",))
    lines = check_request(path, source, FAKE, REPO_ROOT / STOP_LIST)
    assert lines == [f"{path}:1: term: {PLANTED}"]


def test_a_format_error_fails_naming_the_field(at_root, tmp_path):
    reversed_range = DISTANCE_TURN.replace("range = [0.5, 1.0]", "range = [1.0, 0.5]")
    path = write_request(tmp_path, "fake-go", reversed_range)
    source = fake_record(tmp_path / "state", [trial("T1", "E1", 0.1, 0.0)], counted=("E1",))
    with pytest.raises(RequestError) as refused:
        check_request(path, source, FAKE, REPO_ROOT / STOP_LIST)
    assert "pass[1].range" in str(refused.value)
