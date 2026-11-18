"""Run data file, run file and author sidecar (design 3.13, 4.3-4.5, task 13.1).

The files are written to a temporary folder and read back. The sidecar is checked with the bench's own reader,
`bench.scan.levels.sidecar_pieces`, so a pair this module writes is one the blind scan accepts.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from bench.scan.levels import sidecar_pieces

from build_from_spec.runfile import (
    RunFileError,
    check_run_file,
    read_run_data,
    read_run_file,
    run_file_texts,
    write_run_data,
)

RUN = "probe-none-1"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
PROMPT_TIME = "2026-01-01T00:00:00Z"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompts() -> list[dict[str, Any]]:
    start = {
        "kind": "start",
        "sha256": digest("start line"),
        "time": PROMPT_TIME,
        "exit": 0,
        "entries_before": 1,
        "entries_after": 4,
    }
    again = {**start, "kind": "continue", "sha256": digest("continue line"), "entries_before": 4}
    return [start, {**again, "entries_after": 6}]


def run_file(ids: list[str] | None, problem: str | None) -> dict[str, Any]:
    """A valid run file for setup `none`, with the relied-on ids and problem given."""
    return {
        "format": 1,
        "run": RUN,
        "setup": "none",
        "request": {"id": "probe", "commit": COMMIT, "sha256": digest("request file")},
        "source": {"application": "body-lab", "session": "body-2", "seal": digest("source seal")},
        "record": {"seal": digest("run seal"), "end": "ended"},
        "seed": 7,
        "kiro": {"version": "kiro-cli 0.0.1", "model": "model-a", "effort": "medium"},
        "files": {".kiro/steering/reader.md": digest("reader steering")},
        "tools": {"run_experiment": digest("run_experiment text")},
        "given": {},
        "relied_on": {"ids": ids, "problem": problem},
        "result": "not-counted" if problem else "pass",
        "first_in_range": None,
        "last_trial": None,
        "prompts": prompts(),
        "continue_lines": 1,
    }


def write_pair(folder: Path, data: dict[str, Any]) -> tuple[Path, str]:
    """Write the run file and its sidecar under the names of design 4.4 and 3.13; return the run file path."""
    text, sidecar = run_file_texts(data)
    path = folder / f"{RUN}.run.json"
    path.write_text(text, encoding="utf-8", newline="")
    (folder / f"{RUN}.run.json.authors.json").write_text(sidecar, encoding="utf-8", newline="")
    return path, text


def test_null_ids_are_all_bench_and_the_pair_is_accepted(tmp_path):
    data = run_file(None, "no-h1")
    path, text = write_pair(tmp_path, data)
    pieces = sidecar_pieces(path, text)
    assert all(piece.level == "builder" for piece in pieces)
    assert "null" in text
    assert read_run_file(path) == data


def test_none_as_an_id_is_marked_as_the_reader_text(tmp_path):
    data = run_file(["none"], None)
    path, text = write_pair(tmp_path, data)
    dr_kiro = [piece.text for piece in sidecar_pieces(path, text) if piece.level == "dr-kiro"]
    assert dr_kiro == ['"none"']
    assert read_run_file(path) == data


def test_ids_with_quotes_and_non_ascii_are_marked_token_by_token(tmp_path):
    ids = ['R"1', "前へ\\進む", "a, b"]
    data = run_file(ids, "unknown-id")
    path, text = write_pair(tmp_path, data)
    dr_kiro = [piece.text for piece in sidecar_pieces(path, text) if piece.level == "dr-kiro"]
    assert dr_kiro == [json.dumps(identifier, ensure_ascii=False) for identifier in ids]
    assert read_run_file(path) == data


def test_writing_twice_gives_the_same_bytes():
    data = run_file(["R1", "R2"], None)
    assert run_file_texts(data) == run_file_texts(json.loads(json.dumps(data)))


def test_a_missing_field_is_refused_by_name():
    data = run_file(["none"], None)
    del data["result"]
    with pytest.raises(RunFileError, match="missing result"):
        check_run_file(data, "run.json")


def test_an_extra_field_is_refused_by_name():
    data = run_file(["none"], None)
    data["adapter"] = "x"
    with pytest.raises(RunFileError, match="unexpected adapter"):
        check_run_file(data, "run.json")


def test_null_ids_are_refused_only_for_the_three_marked_problems():
    with pytest.raises(RunFileError, match="relied_on.ids"):
        check_run_file(run_file(["R1"], "bad-syntax"), "run.json")
    with pytest.raises(RunFileError, match="relied_on.ids"):
        check_run_file(run_file(None, "unknown-id"), "run.json")


def test_continue_lines_must_count_the_continue_turns():
    data = run_file(["none"], None)
    data["continue_lines"] = 2
    with pytest.raises(RunFileError, match="continue_lines"):
        check_run_file(data, "run.json")


def test_a_run_id_that_does_not_match_its_request_and_setup_is_refused():
    data = run_file(["none"], None)
    data["run"] = "other-none-1"
    with pytest.raises(RunFileError, match="run id of its request"):
        check_run_file(data, "run.json")


def test_given_must_match_the_setup():
    data = run_file(["none"], None)
    data["given"] = {"spec": {"requirements.md": digest("x")}}
    with pytest.raises(RunFileError, match="setup none gives nothing"):
        check_run_file(data, "run.json")


def test_run_file_not_valid_json_is_refused_naming_the_file(tmp_path):
    path = tmp_path / "bad.run.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(RunFileError, match="bad.run.json: not valid JSON"):
        read_run_file(path)


def run_data() -> dict[str, Any]:
    spec = {name: digest(name) for name in ("requirements.md", "design.md", "tasks.md")}
    return {
        "format": 1,
        "run": "probe-spec-1",
        "setup": "spec",
        "request": {"id": "probe", "commit": COMMIT, "sha256": digest("request file")},
        "source": {"application": "body-lab", "session": "body-2", "seal": digest("source seal")},
        "seed": 7,
        "adapter": "build_from_spec.wrap:reader/body-lab/probe/12",
        "kiro": {"version": "kiro-cli 0.0.1", "model": "model-a", "effort": "medium"},
        "files": {"request.md": digest("request words")},
        "tools": {"run_experiment": digest("run_experiment text")},
        "given": {"spec": spec},
        "prompts": [],
    }


def test_run_data_round_trips_through_its_file(tmp_path):
    data = run_data()
    path = tmp_path / "bench-run" / "probe-spec-1.run-data.json"
    write_run_data(path, data)
    assert read_run_data(path) == data
    assert path.read_text(encoding="utf-8").endswith("}\n")


def test_run_data_spec_setup_must_name_the_three_spec_files(tmp_path):
    data = run_data()
    del data["given"]["spec"]["tasks.md"]
    path = tmp_path / "run-data.json"
    with pytest.raises(RunFileError, match="missing tasks.md"):
        write_run_data(path, data)
    assert not path.exists()


def test_run_data_paths_must_stay_inside_the_working_folder(tmp_path):
    data = run_data()
    data["files"] = {"../outside.md": digest("x")}
    with pytest.raises(RunFileError, match="not a path inside the working folder"):
        write_run_data(tmp_path / "run-data.json", data)
