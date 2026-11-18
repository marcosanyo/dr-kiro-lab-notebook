"""Earlier runs of one request (design 3.12, Requirements 7.4, 7.8, 14.6; task 14.1).

The folders here hold empty files and folders only: `runs.py` reads names, and the content of a run file
is read by its own checks. Each test works in a temporary folder, never in `sessions/`.
"""

from pathlib import Path

import pytest

from build_from_spec.runs import (
    RUN_FILE_SUFFIX,
    RunId,
    RunsError,
    application_folders,
    differences,
    paired_runs,
    run_id_parts,
    runs_of_request,
)


def records(root: Path, application: str = "body-lab") -> Path:
    folder = root / "sessions" / "build-from-spec" / application
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run_dict(**changes) -> dict:
    """A run file's fields as `runfile.read_run_file` gives them, with the fields `differences` reads."""
    run = {
        "seed": 7,
        "request": {"id": "probe", "commit": "a" * 40, "sha256": "b" * 64},
        "source": {"application": "body-lab", "session": "body-2", "seal": "c" * 64},
        "kiro": {"version": "kiro-cli 1", "model": "model-a", "effort": "medium"},
        "files": {"request.md": "d" * 64, ".kiro/steering/method.md": "e" * 64},
        "tools": {"run_experiment": "f" * 64},
    }
    run.update(changes)
    return run


def test_a_run_id_with_hyphens_in_its_request_id_is_read_by_its_setup_and_number():
    assert run_id_parts("probe-none-1") == RunId("probe", "none", 1)
    assert run_id_parts("probe-x-none-1") == RunId("probe-x", "none", 1)
    assert run_id_parts("a-spec-record-12") == RunId("a-spec", "record", 12)
    assert run_id_parts("stop-ahead-spec-2") == RunId("stop-ahead", "spec", 2)


@pytest.mark.parametrize("run_id", ["probe-none-0", "probe-other-1", "probe-none", "Probe-none-1", "-none-1"])
def test_a_run_id_that_is_not_of_the_form_is_refused_naming_it(run_id):
    with pytest.raises(RunsError, match=r"is not a run id of the form"):
        run_id_parts(run_id)


def test_a_run_record_without_its_run_file_is_refused_naming_the_record(tmp_path):
    folder = records(tmp_path)
    (folder / "probe-none-1").mkdir()
    (folder / "probe-none-1.run.json").write_text("{}", encoding="utf-8")
    (folder / "probe-none-2").mkdir()

    with pytest.raises(RunsError) as refused:
        paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab")
    assert str(folder / "probe-none-2") in str(refused.value)
    assert "probe-none-2.run.json" in str(refused.value)


def test_a_run_file_without_its_run_record_is_refused_naming_the_file(tmp_path):
    folder = records(tmp_path)
    (folder / "probe-spec-1.run.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RunsError, match=r"probe-spec-1\.run\.json: the run file has no run record"):
        paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab")


def test_a_file_that_is_neither_a_run_file_nor_a_sidecar_is_refused_naming_it(tmp_path):
    folder = records(tmp_path)
    (folder / "notes.txt").write_text("x", encoding="utf-8")

    with pytest.raises(RunsError, match="notes.txt"):
        paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab")


def test_a_sidecar_without_its_run_file_is_refused_naming_it(tmp_path):
    folder = records(tmp_path)
    (folder / "probe-none-1.run.json.authors.json").write_text("{}", encoding="utf-8")

    with pytest.raises(
        RunsError, match=r"probe-none-1\.run\.json\.authors\.json: a sidecar with no run file"
    ):
        paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab")


def test_paired_runs_gives_the_run_files_by_run_id(tmp_path):
    folder = records(tmp_path)
    (folder / "probe-none-1").mkdir()
    (folder / "probe-none-1.run.json").write_text("{}", encoding="utf-8")
    (folder / "probe-none-1.run.json.authors.json").write_text("{}", encoding="utf-8")

    assert paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab") == {
        "probe-none-1": folder / "probe-none-1.run.json"
    }


def test_runs_of_request_takes_only_the_runs_of_that_request(tmp_path):
    folder = records(tmp_path)
    for run_id in ("probe-none-1", "probe-spec-1", "probe-x-none-1"):
        (folder / run_id).mkdir()
        (folder / f"{run_id}{RUN_FILE_SUFFIX}").write_text("{}", encoding="utf-8")

    found = runs_of_request(tmp_path / "sessions" / "build-from-spec", "body-lab", "probe")

    assert sorted(found) == ["probe-none-1", "probe-spec-1"]
    assert runs_of_request(tmp_path / "sessions" / "build-from-spec", "body-lab", "probe-x") == {
        "probe-x-none-1": folder / "probe-x-none-1.run.json"
    }


def test_an_application_folder_that_is_not_a_folder_is_refused(tmp_path):
    (tmp_path / "sessions" / "build-from-spec").mkdir(parents=True)
    (tmp_path / "sessions" / "build-from-spec" / "README.md").write_text("x", encoding="utf-8")

    with pytest.raises(RunsError, match="only application folders belong"):
        application_folders(tmp_path / "sessions" / "build-from-spec")


def test_no_runs_folder_means_no_runs(tmp_path):
    assert application_folders(tmp_path / "sessions" / "build-from-spec") == []
    assert paired_runs(tmp_path / "sessions" / "build-from-spec", "body-lab") == {}


def test_equal_runs_have_no_differences():
    assert differences("a.run.json", run_dict(), "b.run.json", run_dict()) == []


@pytest.mark.parametrize(
    ("changes", "field", "left", "right"),
    [
        ({"seed": 8}, "seed", "7", "8"),
        (
            {"request": {"id": "probe", "commit": "1" * 40, "sha256": "b" * 64}},
            "request.commit",
            "'" + "a" * 40 + "'",
            "'" + "1" * 40 + "'",
        ),
        (
            {"request": {"id": "probe", "commit": "a" * 40, "sha256": "2" * 64}},
            "request.sha256",
            "'" + "b" * 64 + "'",
            "'" + "2" * 64 + "'",
        ),
        (
            {"source": {"application": "body-lab", "session": "body-3", "seal": "c" * 64}},
            "source.session",
            "'body-2'",
            "'body-3'",
        ),
        (
            {"source": {"application": "body-lab", "session": "body-2", "seal": "3" * 64}},
            "source.seal",
            "'" + "c" * 64 + "'",
            "'" + "3" * 64 + "'",
        ),
        (
            {"kiro": {"version": "kiro-cli 2", "model": "model-a", "effort": "medium"}},
            "kiro.version",
            "'kiro-cli 1'",
            "'kiro-cli 2'",
        ),
        (
            {"kiro": {"version": "kiro-cli 1", "model": "model-b", "effort": "medium"}},
            "kiro.model",
            "'model-a'",
            "'model-b'",
        ),
        (
            {"kiro": {"version": "kiro-cli 1", "model": "model-a", "effort": "high"}},
            "kiro.effort",
            "'medium'",
            "'high'",
        ),
        (
            {"files": {"request.md": "4" * 64, ".kiro/steering/method.md": "e" * 64}},
            "files[request.md]",
            "'" + "d" * 64 + "'",
            "'" + "4" * 64 + "'",
        ),
        (
            {"tools": {"run_experiment": "5" * 64}},
            "tools[run_experiment]",
            "'" + "f" * 64 + "'",
            "'" + "5" * 64 + "'",
        ),
    ],
)
def test_each_differing_field_is_named_with_both_values(changes, field, left, right):
    lines = differences("a.run.json", run_dict(), "b.run.json", run_dict(**changes))

    assert len(lines) == 1
    assert lines[0].startswith("a.run.json and b.run.json differ in " + field + ": ")
    assert lines[0].endswith(f": {left} vs {right}")


def test_a_file_that_one_run_lacks_is_a_difference_named_as_absent():
    other = run_dict(files={"request.md": "d" * 64})

    lines = differences("a.run.json", run_dict(), "b.run.json", other)

    assert lines == [
        "a.run.json and b.run.json differ in files[.kiro/steering/method.md]: "
        "'" + "e" * 64 + "' vs '(absent)'"
    ]
