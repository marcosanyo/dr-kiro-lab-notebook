"""Fixtures for the run checks (tests/test_check_runs.py, tests/properties/test_property_12_*.py).

A temporary repository holds the request `probe`, committed at its first commit, and the source record
`body-2`, sealed with no entries. `make_run` seals a run record of the fake experiment with the bench's store,
writes its run data file and writes its run file with `write_run_file`, the command under test's own code.
The repository's real `sessions/` and `bench-run/` folders are never used.
"""

import dataclasses
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from bench.record.chain import verify

from build_from_spec.apps import APPS
from build_from_spec.request import PassRange, Request, print_request
from build_from_spec.runfile import dump_text, write_run_data, write_run_file
from build_from_spec.turns import CONTINUE_LINE, START_LINE
from support import seal_record

REPO_ROOT = Path(__file__).resolve().parents[2]
STOP_LIST = REPO_ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
APPS_FOR_TESTS = {
    "body-lab": dataclasses.replace(
        APPS["body-lab"], scan_sources=str(REPO_ROOT / APPS["body-lab"].scan_sources)
    )
}
WORDS = "Move a little."
PASS_RANGE = PassRange("x", -10.0, 10.0)
SEED = 7
TOOLS = ("register_hypothesis", "run_experiment", "record_verdict", "end_session")
H1 = "### H1: about\n\nWHEN a, THE b SHALL c.\n\n```prediction\n# relies on: none\n[[prediction]]\n```\n"
IDENTITY = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid")
RUN_DATA = Path("bench-run") / "build-from-spec"
RECORDS = Path("sessions") / "build-from-spec" / "body-lab"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit(root: Path, *paths: str, message: str = "change") -> None:
    """Stage the named paths and commit them, one path per argument as the repository rules require."""
    git(root, "add", "--", *paths)
    git(root, *IDENTITY, "commit", "-q", "-m", message)


def make_repo(root: Path) -> Path:
    """A repository with the request `probe` committed and the source record `body-2` sealed."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    requests = root / "build-from-spec" / "requests"
    requests.mkdir(parents=True)
    (requests / "probe.toml").write_text(
        print_request(Request("probe", "body-lab", WORDS, (PASS_RANGE,))), encoding="utf-8"
    )
    (root / "sessions" / "body-lab").mkdir(parents=True)
    seal_record(root / "sessions" / "body-lab" / "body-2", lambda store: [])
    commit(root, "build-from-spec/requests/probe.toml", message="request")
    return root


def change_request(root: Path, words: str) -> None:
    """Write the request with other words and commit it, as a later change to the committed request."""
    path = root / "build-from-spec" / "requests" / "probe.toml"
    request = Request("probe", "body-lab", words, (PASS_RANGE,))
    path.write_text(print_request(request), encoding="utf-8")
    commit(root, "build-from-spec/requests/probe.toml", message="change the request")


def run_file_of(root: Path, run_id: str) -> Path:
    return root / RECORDS / f"{run_id}.run.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict[str, Any]) -> None:
    path.write_text(dump_text(data), encoding="utf-8", newline="")


def _prompt(kind: str, before: int, after: int) -> dict[str, Any]:
    line = START_LINE if kind == "start" else CONTINUE_LINE
    return {
        "kind": kind,
        "sha256": sha(line.encode("utf-8")),
        "time": "2026-01-01T00:00:00Z",
        "exit": 0,
        "entries_before": before,
        "entries_after": after,
    }


DESIGN_WITH_TABLE = """# Design

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|----|------|-------|-------------|-------------|--------|-------------|
| R1 | a rule | all | E1 | P1 | observed | - |
| R2 | another rule | all | E2 | P1 | observed | - |
"""
SPEC_TEXT = {"requirements": "# Requirements\n", "design": DESIGN_WITH_TABLE, "tasks": "# Tasks\n"}


def make_ended_source(root: Path, session: str) -> Path:
    """A source record sealed as `ended` whose end snapshot holds the three spec files of `SPEC_TEXT`."""

    def build(store) -> list[tuple[str, dict[str, Any]]]:
        files = {
            key: store.put_blob(text.encode("utf-8"), "dr-kiro", "text/markdown")
            for key, text in SPEC_TEXT.items()
        }
        start = ("start", {"session": session, "application": "body-lab", "seed": SEED, "budget": 12})
        return [start, ("snapshot", {"for": "end", "files": files})]

    return seal_record(root / "sessions" / "body-lab" / session, build, end="ended")


def make_run(
    root: Path, run_id: str, *, seed: int = SEED, setup: str = "none", source: str = "body-2"
) -> Path:
    """Seal the run record, write its run data file and its run file. Return the run file's path.

    Setup `none` gives nothing. Setup `record` gives the reduced copy of the source, which has no snapshot
    entries here, so its removed list is empty. Setup `spec` gives the hashes of the final spec of `source`,
    which must be an ended record made by `make_ended_source`. The record holds six entries: start, H1, the
    experiment, its trial, its counting snapshot and the seal. The first turn ends after the trial, and the
    second seals the record."""
    folder = root / RECORDS / run_id
    folder.parent.mkdir(parents=True, exist_ok=True)

    def entries(store) -> list[tuple[str, dict[str, Any]]]:
        ref = store.put_blob(H1.encode("utf-8"), "dr-kiro", "text/markdown")
        measured = {"x": 1.0, "y": 0.0, "heading": 0.0}
        return [
            ("start", {"session": run_id, "application": "body-lab", "seed": seed, "budget": 12}),
            ("register", {"hypothesis": "H1", "frozen": ref}),
            ("experiment", {"experiment": "E1", "hypothesis": "H1", "phase": "map", "trials": ["T1"]}),
            ("trial", {"trial": "T1", "experiment": "E1", "measurements": measured}),
            ("snapshot", {"for": "experiment", "experiment": "E1", "files": {}}),
        ]

    seal_record(folder, entries, end="ended")
    source_folder = root / "sessions" / "body-lab" / source
    if setup == "spec":
        given: dict[str, Any] = {
            "spec": {f"{key}.md": sha(text.encode("utf-8")) for key, text in SPEC_TEXT.items()}
        }
    elif setup == "record":
        given = {"record": {"removed": []}}
    else:
        given = {}
    data = {
        "format": 1,
        "run": run_id,
        "setup": setup,
        "request": {
            "id": "probe",
            "commit": git(root, "rev-parse", "HEAD"),
            "sha256": sha((root / "build-from-spec" / "requests" / "probe.toml").read_bytes()),
        },
        "source": {
            "application": "body-lab",
            "session": source,
            "seal": verify(source_folder, sealed=True)[-1]["hash"],
        },
        "seed": seed,
        "adapter": "build_from_spec.wrap:reader/body-lab/probe/12",
        "kiro": {"version": "kiro-cli test", "model": "model-a", "effort": "medium"},
        "files": {"request.md": sha(WORDS.encode("utf-8"))},
        "tools": {name: sha(name.encode("utf-8")) for name in TOOLS},
        "given": given,
        "prompts": [_prompt("start", 1, 4), _prompt("continue", 4, 6)],
    }
    write_run_data(root / RUN_DATA / f"{run_id}.run-data.json", data)
    return write_run_file(run_id, APPS_FOR_TESTS, STOP_LIST, root)
