"""bfs-check-runs: verify every run file against its record, its source and its request, and derive the items
the notebook reads (design 3.12; Requirements 14.3, 14.6, 18.1).

The check reads only committed files: the run records and run files in `sessions/build-from-spec/`, the source
records the run files name, and `build-from-spec/requests/` at the commits the run files record. It never
reads `bench-run/` or a working folder, which may be gone. It refuses and repairs nothing. Every problem is
one line that names the run file and the field.
"""

import argparse
import hashlib
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.record.chain import VerifyError, verify
from bench.record.spec_copy import SpecCopyError, final_spec
from bench.scan.levels import SIDECAR_SUFFIX

from build_from_spec.apps import APPS, REQUESTS, App, AppError, require_repository_root
from build_from_spec.folder import SPEC_FILES
from build_from_spec.judge import JudgeError, Judgement, judge_record
from build_from_spec.reduced import ReducedError, plan
from build_from_spec.relied import ReliedError, allowed_ids
from build_from_spec.request import Request, RequestError, parse_request
from build_from_spec.runfile import (
    RunFileError,
    committed_request,
    limits_for,
    read_run_file,
    run_file_texts,
)
from build_from_spec.runs import (
    RECORDS,
    RunsError,
    application_folders,
    differences,
    paired_runs,
    run_id_parts,
    runs_of_request,
)
from build_from_spec.turns import CONTINUE_LINE, START_LINE

SESSIONS = Path("sessions")  # the sealed source records of the bench, one folder per application


class CheckError(Exception):
    """A run file that does not check. The message names the run file and the field that differs."""


def _fail(label: str, field: str, problem: str) -> CheckError:
    return CheckError(f"{label}: {field}: {problem}")


@contextmanager
def _field(label: str, field: str) -> Iterator[None]:
    """Name the run file and the field on a failure of a checking step. Nothing is swallowed: the failure is
    raised again as a CheckError with the original message."""
    try:
        yield
    except (JudgeError, ReducedError, ReliedError, RequestError, RunFileError, SpecCopyError) as error:
        raise _fail(label, field, str(error)) from error


def _same(label: str, field: str, expected: object, found: object) -> None:
    if expected != found:
        raise _fail(label, field, f"{expected!r} is expected, the run file has {found!r}")


def _sealed(folder: Path, label: str, field: str) -> list[dict[str, Any]]:
    try:
        return verify(folder, sealed=True)
    except VerifyError as error:
        raise _fail(label, field, f"{folder} is not a sealed record that verifies: {error}") from error


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(root: Path, *args: str) -> str:
    """One git command in the repository, stripped of its trailing newline. A failing command is refused."""
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RunFileError(f"git {' '.join(args)} failed in {root}: {done.stderr.strip()}")
    return done.stdout.strip()


@dataclass(frozen=True)
class Checked:
    """A run file that passed every check, with what the checks read."""

    run: dict[str, Any]
    request: Request
    judged: Judgement


def _check_turns(label: str, run: dict[str, Any], count: int) -> None:
    """The turns: one start line, then continue lines, each turn chained to the one before (Req. 9.6)."""
    prompts = run["prompts"]
    if not prompts:
        raise _fail(label, "prompts", "no turn is recorded")
    for index, prompt in enumerate(prompts):
        kind = "start" if index == 0 else "continue"
        _same(label, f"prompts[{index}].kind", kind, prompt["kind"])
        line = START_LINE if index == 0 else CONTINUE_LINE
        _same(label, f"prompts[{index}].sha256", _digest(line.encode("utf-8")), prompt["sha256"])
    _same(label, "prompts[0].entries_before", 1, prompts[0]["entries_before"])
    for index in range(1, len(prompts)):
        _same(
            label,
            f"prompts[{index}].entries_before",
            prompts[index - 1]["entries_after"],
            prompts[index]["entries_before"],
        )
    last = prompts[-1]["entries_after"]
    # A run that bench-stop sealed has one seal entry more than its last turn (design 3.10).
    sealed_by_bench_stop = run["record"]["end"] == "stopped" and count == last + 1
    if count != last and not sealed_by_bench_stop:
        raise _fail(
            label,
            "prompts[-1].entries_after",
            f"{last} is expected from the last turn, the record has {count} entries",
        )


def check_run(run_file: Path, root: Path, apps: Mapping[str, App]) -> Checked:
    """Check one run file against its run record, its source record, its committed request and a new judgement
    (design 3.12, step 2). Raise CheckError at the first field that differs."""
    run_file = Path(run_file)
    label = str(run_file)
    application = run_file.parent.name
    run = read_run_file(run_file)
    run_id = run["run"]
    record = run_file.parent / run_id
    if not record.is_dir():
        raise _fail(label, "run", f"there is no run record {record}")

    entries = _sealed(record, label, "record")
    _same(label, "record.seal", entries[-1]["hash"], run["record"]["seal"])
    start = entries[0]
    if start["kind"] != "start":
        raise _fail(label, "record", "the first entry of the run record is not the start of the session")
    _same(label, "run", run_id, start["body"]["session"])
    _same(label, "seed", start["body"]["seed"], run["seed"])
    _same(label, "record", application, start["body"]["application"])

    source = run["source"]
    _same(label, "source.application", application, source["application"])
    session = source["session"]
    if "/" in session or session in (".", ".."):
        raise _fail(label, "source.session", f"{session!r} is not the name of a session")
    source_folder = root / SESSIONS / source["application"] / session
    source_seal = _sealed(source_folder, label, "source.session")[-1]["hash"]
    _same(label, "source.seal", source_seal, source["seal"])

    request_id = run["request"]["id"]
    commit = run["request"]["commit"]
    with _field(label, "request.commit"):
        request_bytes = committed_request(root, commit, request_id, REQUESTS)
    _same(label, "request.sha256", _digest(request_bytes), run["request"]["sha256"])
    request_path = (REQUESTS / f"{request_id}.toml").as_posix()
    with _field(label, "request.commit"):
        # The run file's own commit is the commit that added it, or HEAD while it is not committed.
        added = _git(
            root, "log", "-1", "--format=%H", "--diff-filter=A", "--", run_file.relative_to(root).as_posix()
        )
        before_run = added or _git(root, "rev-parse", "HEAD")
        last_change = _git(root, "log", "-1", "--format=%H", before_run, "--", request_path)
    _same(label, "request.commit", last_change, commit)

    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory) / f"{request_id}.toml"
        copy.write_bytes(request_bytes)
        with _field(label, "request"):
            request = parse_request(copy, apps)
    _same(label, "request.application", application, request.application)

    setup = run["setup"]
    with _field(label, "relied_on"):
        allowed = allowed_ids(setup, source_folder)
    with _field(label, "record"):
        judged = judge_record(record, request, allowed)
    _same(
        label,
        "relied_on",
        {
            "ids": None if judged.relied.ids is None else list(judged.relied.ids),
            "problem": judged.relied.problem,
        },
        run["relied_on"],
    )
    _same(label, "record.end", judged.end, run["record"]["end"])
    _same(label, "result", judged.result, run["result"])
    _same(label, "first_in_range", judged.first_in_range, run["first_in_range"])
    last = None if judged.last_trial is None else {"trial": judged.last_trial, "phase": judged.last_phase}
    _same(label, "last_trial", last, run["last_trial"])

    given = run["given"]
    if setup == "spec":
        with _field(label, "given.spec"):
            final = final_spec(source_folder)
        for name in SPEC_FILES:
            _same(label, f"given.spec.{name}", _digest(final.files[name]), given["spec"][name])
    if setup == "record":
        with _field(label, "given.record"):
            removed = plan(source_folder).removed
        _same(
            label,
            "given.record.removed",
            [{"seq": item.seq, "hash": item.hash} for item in removed],
            given["record"]["removed"],
        )

    _check_turns(label, run, len(entries))
    _same(label, "limits", limits_for(setup), run["limits"])

    # The run file holds exactly the text that its fields give, and its sidecar the authors of that text.
    text, sidecar = run_file_texts(run)
    if run_file.read_text(encoding="utf-8") != text:
        raise _fail(
            label, "file", "the text is not the one its fields give; the run file was changed by hand"
        )
    sidecar_path = run_file.with_name(run_file.name + SIDECAR_SUFFIX)
    if not sidecar_path.is_file():
        raise _fail(label, "sidecar", f"{sidecar_path} is missing")
    _same(label, "sidecar", sidecar, sidecar_path.read_text(encoding="utf-8"))
    return Checked(run, request, judged)


def derive_run(run_file: Path, root: Path, apps: Mapping[str, App]) -> dict[str, Any]:
    """The items of Requirement 18.1 for one run. The run is checked first, so no item comes from a run that
    fails: an item that cannot be derived fails the check of its run file, naming the field."""
    run_file = Path(run_file)
    checked = check_run(run_file, root, apps)
    run = checked.run
    request = checked.request
    own_setup = run_id_parts(run["run"]).setup
    others = sorted(
        run_id
        for run_id in runs_of_request(root / RECORDS, run_file.parent.name, request.id)
        if run_id_parts(run_id).setup != own_setup
    )
    last = checked.judged.last_trial
    return {
        "run": run["run"],
        "setup": run["setup"],
        "request": {
            "id": request.id,
            "application": request.application,
            "commit": run["request"]["commit"],
            "words": request.words,
            "passes": [{"measurement": p.measurement, "low": p.low, "high": p.high} for p in request.passes],
        },
        "relied_on": run["relied_on"],
        "last_trial": None
        if last is None
        else {
            "trial": last,
            "phase": checked.judged.last_phase,
            "measured": dict(checked.judged.last_values),
        },
        "result": run["result"],
        "first_in_range": run["first_in_range"],
        "end": run["record"]["end"],
        "other_setups": others,
    }


def check_all(root: Path, apps: Mapping[str, App]) -> tuple[list[str], list[str]]:
    """Check every run of every application under `root`. Return the lines of the runs that pass and the
    problems, one line each. Refuse, with RunsError, when a run record and its run file do not pair."""
    passed: list[str] = []
    problems: list[str] = []
    for application in application_folders(root / RECORDS):
        runs = paired_runs(root / RECORDS, application)
        for path in runs.values():
            try:
                item = derive_run(path, root, apps)
            except (CheckError, RunFileError) as error:
                problems.append(str(error))
                continue
            passed.append(f"{path}: ok: result {item['result']}, end {item['end']}")
        for request_id in sorted({run_id_parts(run_id).request for run_id in runs}):
            loaded = []
            for path in runs_of_request(root / RECORDS, application, request_id).values():
                try:
                    loaded.append((path, read_run_file(path)))
                except RunFileError as error:
                    problems.append(str(error))
            # Requirement 14.6: every run of one request is compared with the first of them.
            if len(loaded) > 1:
                first_path, first = loaded[0]
                for path, run in loaded[1:]:
                    problems += differences(str(first_path), first, str(path), run)
    return passed, problems


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bfs-check-runs", description="Check every run file against its record, source and request."
    )
    parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        require_repository_root()
        passed, problems = check_all(Path.cwd(), APPS)
    except (AppError, RunsError) as error:
        sys.exit(f"bfs-check-runs: {error}")
    if passed:
        print("\n".join(passed))
    if problems:
        sys.exit("\n".join(problems))
    if not passed:
        print("bfs-check-runs: no runs")
