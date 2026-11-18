"""The reader's runs (`build-from-spec`), read from `sessions/build-from-spec/<application>/`.

Each run is one sealed record folder `<run>/` and the run file `<run>.run.json` that the bench's reader tool
wrote beside it, with the sidecar `<run>.run.json.authors.json`. This module reads only those files. It checks
that the run file has exactly the keys of format 1, that its name is the folder's name, and that the seal in
the run file is the seal of the sealed record. A folder without a run file, a run file without a folder, and
any other file are refused, naming the path. The reader's request and the spec documents are not read here.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.record.chain import VerifyError, verify

from notebook.errors import NotebookError

FOLDER = "build-from-spec"
SETUPS = ("spec", "record", "none")
RESULTS = ("pass", "fail", "no-trial", "not-counted")
_SUFFIX = ".run.json"
_SIDECAR = ".authors.json"
_KEYS = frozenset(
    {
        "continue_lines",
        "files",
        "first_in_range",
        "format",
        "given",
        "kiro",
        "last_trial",
        "limits",
        "prompts",
        "record",
        "relied_on",
        "request",
        "result",
        "run",
        "seed",
        "setup",
        "source",
        "tools",
    }
)


@dataclass(frozen=True)
class Run:
    """One reader run, as its run file records it."""

    name: str
    application: str
    where: str  # `sessions/build-from-spec/<application>/<run>` for messages
    request_id: str
    setup: str
    result: str
    seed: int
    source_application: str
    source_session: str
    seal: str
    end: str
    first_in_range: str | None
    last_trial: str
    last_phase: str
    relied_ids: tuple[str, ...]
    relied_problem: str | None
    limits: tuple[str, ...]


def _fail(where: str, problem: str) -> NotebookError:
    return NotebookError(where, problem)


def _shape(value: Any, where: str, what: str, expected: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise _fail(where, f"{what} does not have exactly the keys {sorted(expected)}")
    return value


def _string(value: Any, where: str, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(where, f"{what} is not a text")
    return value


def _read(folder: Path, file: Path, where: str) -> Run:
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise _fail(where, f"the run file cannot be read as JSON ({error})") from error
    data = _shape(data, where, "the run file", set(_KEYS))
    if data["format"] != 1:
        raise _fail(where, f"the run file has format {data['format']!r}, not 1")
    if data["run"] != folder.name:
        raise _fail(where, f"the run file names run {data['run']!r}, not {folder.name!r}")
    setup = _string(data["setup"], where, "setup")
    if setup not in SETUPS:
        raise _fail(where, f"setup {setup!r} is not one of {list(SETUPS)}")
    result = _string(data["result"], where, "result")
    if result not in RESULTS:
        raise _fail(where, f"result {result!r} is not one of {list(RESULTS)}")
    seed = data["seed"]
    if type(seed) is not int:
        raise _fail(where, "seed is not a whole number")
    request = _shape(data["request"], where, "request", {"commit", "id", "sha256"})
    source = _shape(data["source"], where, "source", {"application", "seal", "session"})
    record = _shape(data["record"], where, "record", {"end", "seal"})
    last = _shape(data["last_trial"], where, "last_trial", {"phase", "trial"})
    relied = _shape(data["relied_on"], where, "relied_on", {"ids", "problem"})
    ids = relied["ids"]
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise _fail(where, "relied_on.ids is not a list of texts")
    problem = relied["problem"]
    if problem is not None and not isinstance(problem, str):
        raise _fail(where, "relied_on.problem is neither null nor a text")
    limits = data["limits"]
    if not isinstance(limits, list) or not all(isinstance(i, str) for i in limits):
        raise _fail(where, "limits is not a list of texts")
    first = data["first_in_range"]
    if first is not None and not isinstance(first, str):
        raise _fail(where, "first_in_range is neither null nor a text")
    try:
        sealed = verify(folder, sealed=True)
    except VerifyError as error:
        raise _fail(f"{where}/{error.where}", error.problem) from error
    seal = _string(record["seal"], where, "record.seal")
    if sealed[-1]["hash"] != seal:
        raise _fail(where, f"the record's seal is {sealed[-1]['hash']}, the run file has {seal}")
    return Run(
        name=folder.name,
        application=folder.parent.name,
        where=where,
        request_id=_string(request["id"], where, "request.id"),
        setup=setup,
        result=result,
        seed=seed,
        source_application=_string(source["application"], where, "source.application"),
        source_session=_string(source["session"], where, "source.session"),
        seal=seal,
        end=_string(record["end"], where, "record.end"),
        first_in_range=first,
        last_trial=_string(last["trial"], where, "last_trial.trial"),
        last_phase=_string(last["phase"], where, "last_trial.phase"),
        relied_ids=tuple(ids),
        relied_problem=problem,
        limits=tuple(limits),
    )


def load(sessions: Path) -> list[Run]:
    """Every run of `sessions/build-from-spec/`, ordered by (request id, setup, run name). Empty when the
    folder is absent: a build of records without any reader run shows no reader section."""
    root = Path(sessions) / FOLDER
    if not root.exists():
        return []
    runs: list[Run] = []
    for app in sorted(root.iterdir(), key=lambda p: p.name):
        where_app = f"{Path(sessions).name}/{FOLDER}/{app.name}"
        if not app.is_dir():
            raise _fail(where_app, "not an application folder")
        names = {p.name for p in app.iterdir()}
        folders = {n for n in names if (app / n).is_dir()}
        run_files = {n[: -len(_SUFFIX)] for n in names if n.endswith(_SUFFIX)}
        sidecars = {n[: -len(_SUFFIX + _SIDECAR)] for n in names if n.endswith(_SUFFIX + _SIDECAR)}
        others = (
            names - folders - {f + _SUFFIX for f in run_files} - {f + _SUFFIX + _SIDECAR for f in sidecars}
        )
        if others:
            raise _fail(f"{where_app}/{sorted(others)[0]}", "unexpected file in the reader's runs folder")
        if folders != run_files or sidecars != run_files:
            odd = sorted((folders ^ run_files) | (sidecars ^ run_files))[0]
            raise _fail(
                f"{where_app}/{odd}", "a run needs its record folder, its run file and the run file's sidecar"
            )
        for name in sorted(run_files):
            runs.append(_read(app / name, app / (name + _SUFFIX), f"{where_app}/{name}"))
    return sorted(runs, key=lambda r: (r.request_id, SETUPS.index(r.setup), r.name))


def tally(runs: list[Run], request_id: str) -> list[tuple[str, int, int, dict[str, int]]]:
    """For one request: per setup in `SETUPS` order, (setup, passes, runs, other results by name).
    A setup with no run of the request is left out."""
    out = []
    for setup in SETUPS:
        mine = [r for r in runs if r.request_id == request_id and r.setup == setup]
        if not mine:
            continue
        passes = sum(1 for r in mine if r.result == "pass")
        other: dict[str, int] = {}
        for r in mine:
            if r.result not in ("pass", "fail"):
                other[r.result] = other.get(r.result, 0) + 1
        out.append((setup, passes, len(mine), other))
    return out
