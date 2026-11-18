"""`write_run_file` and `bfs-run-file` (design 3.11, Requirements 14.1, 14.5, 16.2; task 13.4).

Each test works in a temporary git repository. Its source record, its request and its run record are written
there with the bench's own store, so the real `sessions/build-from-spec/` folder is never used. The scan uses
the real stop list and the real body-lab scan sources, which name the repository's own paths.
"""

import dataclasses
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
from bench.record.chain import verify
from bench.record.store import Store
from bench.scan.scan import Scanner
from bench.scan.terms import ScanError

from build_from_spec import runfile
from build_from_spec.apps import APPS
from build_from_spec.request import PassRange, Request, print_request
from build_from_spec.runfile import (
    RunFileError,
    read_run_data,
    read_run_file,
    write_run_data,
    write_run_file,
)
from build_from_spec.runfile import main as run_file_command
from support import seal_record

REPO_ROOT = Path(__file__).resolve().parents[2]
STOP_LIST = REPO_ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
BODY_CONFIG = REPO_ROOT / APPS["body-lab"].scan_sources
APPS_FOR_TESTS = {"body-lab": dataclasses.replace(APPS["body-lab"], scan_sources=str(BODY_CONFIG))}
WORDS = "Move a little."
PASS_RANGE = PassRange("x", -10.0, 10.0)
H1 = "### H1: about\n\nWHEN a, THE b SHALL c.\n\n```prediction\n# relies on: none\n[[prediction]]\n```\n"
IDENTITY = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid")
TOOLS = ("register_hypothesis", "run_experiment", "record_verdict", "end_session")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with the request committed and the source record `body-2` sealed."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    requests = root / "build-from-spec" / "requests"
    requests.mkdir(parents=True)
    request = Request("probe", "body-lab", WORDS, (PASS_RANGE,))
    (requests / "probe.toml").write_text(print_request(request), encoding="utf-8")
    git(root, "add", "build-from-spec/requests/probe.toml")
    git(root, *IDENTITY, "commit", "-q", "-m", "request")
    (root / "sessions" / "body-lab").mkdir(parents=True)
    seal_record(root / "sessions" / "body-lab" / "body-2", lambda store: [])
    return root


def make_run_record(root: Path, run_id: str, frozen: str = H1, *, sealed: bool = True) -> Path:
    """A run record of setup `none` with H1 registered and one counted trial inside the pass range."""
    folder = root / "sessions" / "build-from-spec" / "body-lab" / run_id
    folder.parent.mkdir(parents=True, exist_ok=True)

    def entries(store: Store) -> list[tuple[str, dict[str, Any]]]:
        ref = store.put_blob(frozen.encode("utf-8"), "dr-kiro", "text/markdown")
        measured = {"x": 1.0, "y": 0.0, "heading": 0.0}
        return [
            ("register", {"hypothesis": "H1", "frozen": ref}),
            ("experiment", {"experiment": "E1", "hypothesis": "H1", "phase": "map", "trials": ["T1"]}),
            ("trial", {"trial": "T1", "experiment": "E1", "measurements": measured}),
            ("snapshot", {"for": "experiment", "experiment": "E1", "files": {}}),
        ]

    return seal_record(folder, entries, end="ended", sealed=sealed)


def prompt(kind: str, number: int) -> dict[str, Any]:
    return {
        "kind": kind,
        "sha256": sha(kind.encode("utf-8")),
        "time": "2026-01-01T00:00:00Z",
        "exit": 0,
        "entries_before": number,
        "entries_after": number + 3,
    }


def write_run_data_for(root: Path, run_id: str) -> Path:
    """The run data file of a run of setup `none`, as the run script writes it at preparation."""
    commit = git(root, "rev-parse", "HEAD")
    request_bytes = (root / "build-from-spec" / "requests" / "probe.toml").read_bytes()
    source_seal = verify(root / "sessions" / "body-lab" / "body-2", sealed=True)[-1]["hash"]
    data = {
        "format": 1,
        "run": run_id,
        "setup": "none",
        "request": {"id": "probe", "commit": commit, "sha256": sha(request_bytes)},
        "source": {"application": "body-lab", "session": "body-2", "seal": source_seal},
        "seed": 7,
        "adapter": "build_from_spec.wrap:reader/body-lab/probe/12",
        "kiro": {"version": "kiro-cli test", "model": "model-a", "effort": "medium"},
        "files": {"request.md": sha(WORDS.encode("utf-8"))},
        "tools": {name: sha(name.encode("utf-8")) for name in TOOLS},
        "given": {},
        "prompts": [prompt("start", 1), prompt("continue", 4)],
    }
    path = root / "bench-run" / "build-from-spec" / f"{run_id}.run-data.json"
    write_run_data(path, data)
    return path


def run_file_path(root: Path, run_id: str) -> Path:
    return root / "sessions" / "build-from-spec" / "body-lab" / f"{run_id}.run.json"


def write(root: Path, run_id: str = "probe-none-1", *, supersede: bool = False) -> Path:
    return write_run_file(
        run_id,
        APPS_FOR_TESTS,
        STOP_LIST,
        root,
        root / "sessions" / "build-from-spec",
        supersede=supersede,
    )


def tree_bytes(folder: Path) -> dict[str, bytes]:
    """Every file under `folder`, by its path relative to it, with its bytes."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def superseded_names(root: Path) -> list[str]:
    return sorted(path.name for path in (root / "bench-run" / "build-from-spec" / "superseded").iterdir())


def test_writes_the_run_file_and_its_sidecar_and_nothing_else(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")

    path = write(repo)

    assert path == run_file_path(repo, "probe-none-1")
    run = read_run_file(path)
    assert run["result"] == "pass"
    assert run["relied_on"] == {"ids": ["none"], "problem": None}
    assert run["last_trial"] == {"trial": "T1", "phase": "map"}
    assert run["continue_lines"] == 1
    records = sorted(os.listdir(path.parent))
    assert records == ["probe-none-1", "probe-none-1.run.json", "probe-none-1.run.json.authors.json"]
    assert Scanner.from_config([BODY_CONFIG], STOP_LIST).scan_file(path) == []


def test_an_existing_run_file_is_refused_by_name_and_kept(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    path = write(repo)
    before = path.read_bytes()

    with pytest.raises(RunFileError, match=r"probe-none-1\.run\.json: already exists"):
        write(repo)
    assert path.read_bytes() == before


def test_supersede_moves_the_old_pair_and_writes_the_new_one(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    path = write(repo)
    old_run = path.read_bytes()
    old_sidecar = path.with_name(path.name + ".authors.json").read_bytes()
    record_before = tree_bytes(path.parent / "probe-none-1")

    written = write(repo, supersede=True)

    assert written == path
    assert read_run_file(path)["result"] == "pass"
    superseded = repo / "bench-run" / "build-from-spec" / "superseded"
    names = superseded_names(repo)
    run_names = [n for n in names if re.fullmatch(r"probe-none-1\.run\.json\.\d{8}-\d{6}", n)]
    sidecar_pattern = r"probe-none-1\.run\.json\.authors\.json\.\d{8}-\d{6}"
    sidecar_names = [n for n in names if re.fullmatch(sidecar_pattern, n)]
    assert len(names) == 2 and len(run_names) == 1 and len(sidecar_names) == 1
    assert (superseded / run_names[0]).read_bytes() == old_run
    assert (superseded / sidecar_names[0]).read_bytes() == old_sidecar
    assert path.with_name(path.name + ".authors.json").is_file()
    assert tree_bytes(path.parent / "probe-none-1") == record_before


def test_supersede_refuses_when_there_is_no_run_file_and_writes_nothing(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")

    with pytest.raises(RunFileError, match=r"probe-none-1\.run\.json: no run file to supersede"):
        write(repo, supersede=True)
    assert not run_file_path(repo, "probe-none-1").exists()
    assert not (repo / "bench-run" / "build-from-spec" / "superseded").exists()


def test_supersede_refuses_a_run_file_without_its_sidecar_and_moves_nothing(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    path = write(repo)
    path.with_name(path.name + ".authors.json").unlink()

    with pytest.raises(RunFileError, match="has no sidecar to supersede"):
        write(repo, supersede=True)
    assert path.is_file()


def test_supersede_refuses_an_unsealed_record_and_moves_nothing(repo):
    make_run_record(repo, "probe-none-2", sealed=False)
    write_run_data_for(repo, "probe-none-2")
    path = run_file_path(repo, "probe-none-2")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("old run file\n", encoding="utf-8")
    sidecar = path.with_name(path.name + ".authors.json")
    sidecar.write_text("old sidecar\n", encoding="utf-8")

    with pytest.raises(RunFileError, match="not sealed or does not verify"):
        write(repo, "probe-none-2", supersede=True)
    assert path.read_text(encoding="utf-8") == "old run file\n"
    assert sidecar.read_text(encoding="utf-8") == "old sidecar\n"
    assert not (repo / "bench-run" / "build-from-spec" / "superseded").exists()


def test_without_supersede_an_existing_run_file_is_refused_and_nothing_moves(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    path = write(repo)
    before = tree_bytes(path.parent)

    with pytest.raises(RunFileError, match="already exists"):
        write(repo)
    assert tree_bytes(path.parent) == before
    assert not (repo / "bench-run" / "build-from-spec" / "superseded").exists()


def test_a_record_that_is_not_sealed_is_refused(repo):
    make_run_record(repo, "probe-none-2", sealed=False)
    write_run_data_for(repo, "probe-none-2")

    with pytest.raises(RunFileError, match="not sealed or does not verify"):
        write(repo, "probe-none-2")
    assert not run_file_path(repo, "probe-none-2").exists()


def test_a_planted_path_in_the_reader_text_fails_the_scan_and_writes_nothing(repo):
    planted = H1 + f"\nSee {REPO_ROOT / 'body-lab' / 'model'} for the rest.\n"
    record = make_run_record(repo, "probe-none-3", frozen=planted)
    write_run_data_for(repo, "probe-none-3")
    log_before = (record / "log.jsonl").read_bytes()

    with pytest.raises(RunFileError, match=r"(?s)blind scan finds items.*blobs/[0-9a-f]{64}:10: path"):
        write(repo, "probe-none-3")

    assert not run_file_path(repo, "probe-none-3").exists()
    assert sorted(p.name for p in run_file_path(repo, "probe-none-3").parent.iterdir()) == ["probe-none-3"]
    assert (record / "log.jsonl").read_bytes() == log_before


def test_a_run_file_without_its_sidecar_fails_the_bench_scan(repo):
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    path = write(repo)
    path.with_name(path.name + ".authors.json").unlink()

    with pytest.raises(ScanError, match="no level source"):
        Scanner.from_config([BODY_CONFIG], STOP_LIST).scan_file(path)


def test_a_request_that_differs_from_its_commit_is_refused(repo):
    make_run_record(repo, "probe-none-1")
    data_path = write_run_data_for(repo, "probe-none-1")
    data = read_run_data(data_path)
    data["request"]["sha256"] = sha(b"another request")
    write_run_data(data_path, data)

    with pytest.raises(RunFileError, match="has SHA-256"):
        write(repo)
    assert not run_file_path(repo, "probe-none-1").exists()


def test_a_source_with_another_seal_is_refused(repo):
    make_run_record(repo, "probe-none-1")
    data_path = write_run_data_for(repo, "probe-none-1")
    data = read_run_data(data_path)
    data["source"]["seal"] = sha(b"another seal")
    write_run_data(data_path, data)

    with pytest.raises(RunFileError, match="its seal is"):
        write(repo)


def test_a_run_id_that_is_not_of_the_form_is_refused_before_any_path_is_built(repo):
    with pytest.raises(RunFileError, match="is not a run id"):
        write(repo, "../probe-none-1")


def test_the_command_refuses_outside_the_repository_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit, match="repository root"):
        run_file_command(["probe-none-1", "--sessions", "sessions/build-from-spec"])


def test_the_command_writes_the_run_file_in_the_repository_root(repo, monkeypatch, capsys):
    # The command reads the application table and the stop list of its repository. The temporary
    # repository has neither, so both names are pointed at the real files of this checkout.
    monkeypatch.setattr(runfile, "APPS", APPS_FOR_TESTS)
    monkeypatch.setattr(runfile, "STOP_LIST", STOP_LIST)
    make_run_record(repo, "probe-none-1")
    write_run_data_for(repo, "probe-none-1")
    monkeypatch.chdir(repo)

    run_file_command(["probe-none-1", "--sessions", "sessions/build-from-spec"])

    assert run_file_path(repo, "probe-none-1").is_file()
    assert "bfs-run-file: wrote" in capsys.readouterr().out
    assert json.loads(run_file_path(repo, "probe-none-1").read_text(encoding="utf-8"))["setup"] == "none"
