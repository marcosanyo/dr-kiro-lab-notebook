"""bfs-run: the run script (design 2.3, 3.9, 3.10; Requirements 4, 5, 7, 11, 13, 17).

Phases, as in design 2.3:

- A. Checks. Nothing is written. A refusal exits with code 2 and counts nothing.
- B. Prepare: the working folder, the run data file and the session config. A failure exits with code 1
  and keeps the folder.
- C. Start the bench session with the core. From here the run counts.
- D. Turns: one headless Kiro CLI process per turn, with the fixed lines only.
- E. End: the run file when the record is sealed; otherwise `bench-stop` with the reason, then the run file.

Every command runs from the repository root (design B24). `main` checks that; the functions take `root`.
Kiro CLI is reached through the `Kiro` port, so the tests run the whole script with a fake launch.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from bench.core.outcome import Ran
from bench.core.session import Session
from bench.drkiro.session import NewSessionError, open_sessions
from bench.frontend import config as config_file
from bench.frontend import stop
from bench.frontend.describe import descriptions
from bench.record.chain import VerifyError, verify
from bench.record.spec_copy import SpecCopyError, final_spec, read_end
from bench.scan.scan import Scanner
from bench.scan.terms import ScanError

from build_from_spec.apps import (
    APPS,
    App,
    AppError,
    app_for,
    check_records,
    request_folder,
    require_repository_root,
)
from build_from_spec.folder import (
    DISCOVERED_TABLE,
    SETUPS,
    SPEC_FILES,
    FolderError,
    GivenFiles,
    file_hashes,
    given_files,
    scan_folder,
    tool_hashes,
    write_folder,
)
from build_from_spec.judge import JudgeError
from build_from_spec.reduced import ReducedError
from build_from_spec.relied import ReliedError
from build_from_spec.request import STOP_LIST, Request, RequestError, check_request, parse_request
from build_from_spec.runfile import (
    FORMAT,
    RUN_DATA,
    RUN_DATA_SUFFIX,
    RunFileError,
    read_run_data,
    read_run_file,
    write_run_data,
    write_run_file,
)
from build_from_spec.runs import (
    RUN_FILE_SUFFIX,
    RUN_ID,
    RunsError,
    counted_runs_of_request,
    differences,
    records_folder,
)
from build_from_spec.turns import Prompt, TurnsEnd, kiro_command, run_turns
from build_from_spec.wrap import ReaderAdapter, WrapError, build

LAB_SPEC = ".kiro/specs/lab/"
CONFIG_SUFFIX = ".session.toml"
HOOK_LOG_SUFFIX = ".hook-log.jsonl"
STATE = "state"
KIRO = "kiro-cli"
SEED = re.compile(r"[0-9]+")
RUN_NUMBER = re.compile(r"[1-9][0-9]*")


class RunRefused(Exception):
    """A check of phase A failed. Nothing was written, and the run counts nothing (exit code 2)."""


class RunStopped(Exception):
    """A step after phase A failed. The working folder or the session is kept as the message says (exit 1)."""


@dataclass(frozen=True)
class Arguments:
    request: str  # the request file, relative to the repository root
    setup: str  # spec | none | record
    source: str  # the sealed source record, relative to the repository root
    seed: int
    run: int
    model: str
    effort: str
    sessions: str  # the records folder of the run, relative to the repository root (no default, 11.1)


@dataclass(frozen=True)
class Checked:
    """What phase A established. The later phases use these values and nothing else from the checks."""

    run_id: str
    request: Request
    records: Path  # the records folder of the run: the run record folders and run files go in it
    commit: str  # the last commit that changed the request file
    request_sha256: str
    app: App
    source: Path
    source_session: str
    source_seal: str
    version: str  # `kiro-cli --version`
    adapter: ReaderAdapter
    factory: str  # the factory name the session config names
    earlier: tuple[tuple[str, dict[str, Any]], ...]  # (run file name, its data) of the earlier runs


class Kiro(Protocol):
    """Kiro CLI as the script uses it: its version, and one turn as one process."""

    def version(self) -> str: ...

    def turn(self, command: list[str], folder: Path, env: Mapping[str, str], log: Path) -> int: ...


class SubprocessKiro:
    """The real Kiro CLI. A turn runs the command that `kiro_command` builds (design 3.10)."""

    def version(self) -> str:
        if shutil.which(KIRO) is None:
            raise RunRefused(f"{KIRO} is not on PATH; the reader cannot start without it")
        done = subprocess.run([KIRO, "--version"], capture_output=True, text=True, check=False)
        if done.returncode != 0:
            raise RunRefused(f"{KIRO} --version exited with code {done.returncode}")
        version = done.stdout.strip()
        if not version:
            raise RunRefused(f"{KIRO} --version printed nothing; the run records the version")
        return version

    def turn(self, command: list[str], folder: Path, env: Mapping[str, str], log: Path) -> int:
        with log.open("wb") as output:
            done = subprocess.run(
                command,
                cwd=folder,
                env=dict(env),
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=False,
            )
        return done.returncode


def parse_arguments(argv: list[str] | None) -> Arguments:
    """Eight arguments, all required, none with a default (Requirement 11.1). A refusal names the argument and
    its value (Requirement 11.8)."""
    parser = argparse.ArgumentParser(prog="bfs-run", description="Start one reader run.")
    helps = {
        "request": "the request file, build-from-spec/requests/<id>.toml (rehearsal: see RUN.md)",
        "setup": f"one of {', '.join(SETUPS)}",
        "source": "the sealed source record, in sessions/<application>/<session>",
        "seed": "the reader's seed, a whole number of zero or more",
        "run": "the run number, 1 or more",
        "model": "the Kiro CLI model name",
        "effort": "the Kiro CLI effort value",
        "sessions": "the records folder of the run: sessions/build-from-spec (production)",
    }
    for name in ("request", "setup", "source", "seed", "run", "model", "effort", "sessions"):
        parser.add_argument(f"--{name}", required=True, type=str, help=helps[name])
    raw = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if raw.setup not in SETUPS:
        raise RunRefused(f"--setup {raw.setup!r} is not one of {', '.join(SETUPS)}")
    if SEED.fullmatch(raw.seed) is None:
        raise RunRefused(f"--seed {raw.seed!r} is not a whole number of zero or more")
    if RUN_NUMBER.fullmatch(raw.run) is None:
        raise RunRefused(f"--run {raw.run!r} is not an integer of at least 1")
    if not raw.model.strip():
        raise RunRefused("--model is empty; a model name is required")
    if not raw.effort.strip():
        raise RunRefused("--effort is empty; an effort value is required")
    return Arguments(
        raw.request, raw.setup, raw.source, int(raw.seed), int(raw.run), raw.model, raw.effort, raw.sessions
    )


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)


def _relative(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), base.resolve())


def _run_dir(root: Path) -> Path:
    return root / RUN_DATA


def _request_tracked(root: Path, request_file: Path) -> str:
    """Check 1 (Requirement 11.2): the request is tracked and equal to HEAD, staged or not. Return its path
    in the repository."""
    if not request_file.resolve().is_relative_to(root.resolve()):
        raise RunRefused(f"{request_file} is outside the repository; the request is a file in it")
    rel = request_file.resolve().relative_to(root.resolve()).as_posix()
    if _git(root, "ls-files", "--error-unmatch", "--", rel).returncode != 0:
        raise RunRefused(f"{rel} is not tracked by git; commit the request before a run")
    diff = _git(root, "diff", "--quiet", "HEAD", "--", rel)
    if diff.returncode == 1:
        raise RunRefused(f"{rel} differs from its commit in HEAD (staged or unstaged); commit it first")
    if diff.returncode != 0:
        raise RunRefused(f"{rel}: git cannot compare it with HEAD: {diff.stderr.strip()}")
    return rel


def _declared_application(request_file: Path) -> str:
    """The `application` of a request file, before the request is parsed. The budget check (Requirement 4.7)
    needs it first. A file that is not TOML is refused here, naming the file."""
    try:
        data = tomllib.loads(request_file.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise RunRefused(f"{request_file} is not valid TOML ({error})") from error
    name = data.get("application")
    if not isinstance(name, str):
        raise RunRefused(f"{request_file}: application must be a text naming the application")
    return name


def _source_checks(records: Path, source: Path, request: Request) -> tuple[str, str]:
    """Check 4 (Requirement 5): a sealed record of the request's application, ended, with a final spec. Return
    its session id and seal hash. The source folder is the parent of the records folder (Checked.records)."""
    resolved = source.resolve()
    sessions = records.parent.resolve()
    if resolved.is_relative_to(records.resolve()):
        raise RunRefused(f"{source} is inside {records}; a run record is not a source")
    if not resolved.is_relative_to(sessions):
        raise RunRefused(f"{source} is not inside {records.parent}; the source is a sealed session record")
    ended = read_end(source)
    if ended.application != request.application:
        raise RunRefused(
            f"{source} is a {ended.application} session; request {request.id} is for {request.application}"
        )
    if resolved.parent != (sessions / ended.application).resolve():
        raise RunRefused(
            f"{source} is not in {records.parent / ended.application}; the source must sit there"
        )
    final_spec(source)  # refuses a source that is not ended, or has no end snapshot (Requirement 5.2)
    return ended.session, verify(source, sealed=True)[-1]["hash"]


def _used_paths(root: Path, records: Path, run_id: str, application: str) -> list[Path]:
    """Check 5 (Requirement 7.1): every path that already carries this run id."""
    run_dir = _run_dir(root)
    folder = records_folder(records, application)
    candidates = (
        run_dir / run_id,
        run_dir / f"{run_id}{CONFIG_SUFFIX}",
        run_dir / f"{run_id}{RUN_DATA_SUFFIX}",
        run_dir / STATE / run_id,
        folder / run_id,
        folder / f"{run_id}{RUN_FILE_SUFFIX}",
    )
    return [path for path in candidates if path.exists()]


def check(arguments: Arguments, root: Path, apps: Mapping[str, App], kiro: Kiro) -> Checked:
    """Phase A (design 3.9, steps 1-9). Writes nothing. Each refusal raises RunRefused with its reason."""
    request_file = root / arguments.request
    records = root / arguments.sessions
    if not request_file.is_file():
        raise RunRefused(f"--request {arguments.request}: no such file")
    try:
        rel = _request_tracked(root, request_file)
        declared = app_for(_declared_application(request_file), apps)
        check_records(declared, records, root)
        request = parse_request(request_file, apps)
        folder = request_folder(declared)
        if request_file.resolve() != (root / folder / f"{request.id}.toml").resolve():
            raise RunRefused(f"{rel} is not named by its id; the request file is {folder}/{request.id}.toml")
        commit = _git(root, "log", "-1", "--format=%H", "--", rel).stdout.strip()
        if not commit:
            raise RunRefused(f"{rel}: git has no commit that changed it")
        request_sha = hashlib.sha256(request_file.read_bytes()).hexdigest()
        findings = check_request(request_file, root / arguments.source, apps, root / STOP_LIST)
        if findings:
            raise RunRefused("the request has findings:\n" + "\n".join(findings))
        app = app_for(request.application, apps)
        source = root / arguments.source
        if not source.is_dir():
            raise RunRefused(f"--source {arguments.source}: not a session record folder")
        source_session, source_seal = _source_checks(records, source, request)
        run_id = f"{request.id}-{arguments.setup}-{arguments.run}"
        if RUN_ID.fullmatch(run_id) is None:
            raise RunRefused(f"{run_id!r} is not a run id of the form <request>-<spec|none|record>-<n>")
        used = _used_paths(root, records, run_id, app.name)
        if used:
            raise RunRefused(f"run id {run_id} is already used: {', '.join(map(str, used))}")
        version = kiro.version()
        name = f"reader/{app.name}/{request.id}/{app.budget}"
        adapter = build(name, apps, root)
        state = _run_dir(root) / STATE
        if state.is_dir():
            still_open = open_sessions(state)
            if still_open:
                raise RunRefused(f"session {', '.join(still_open)} in {state} is not sealed; stop it first")
        planned = {
            "seed": arguments.seed,
            "request": {"id": request.id, "commit": commit, "sha256": request_sha},
            "source": {"application": app.name, "session": source_session, "seal": source_seal},
            "kiro": {"version": version, "model": arguments.model, "effort": arguments.effort},
        }
        earlier = []
        lines: list[str] = []
        for path in counted_runs_of_request(root, app.name, request.id).values():
            data = read_run_file(path)
            earlier.append((path.name, data))
            # The hashes of the working folder are compared in phase B, after the folder is written
            # (design B19). Here they are copied from the earlier run, so this check covers the other fields.
            same_hashes = {**planned, "files": data["files"], "tools": data["tools"]}
            lines += differences("this run", same_hashes, path.name, data)
        if lines:
            raise RunRefused("the run differs from an earlier run of this request:\n" + "\n".join(lines))
    except (
        AppError,
        NewSessionError,
        RequestError,
        RunFileError,
        RunsError,
        SpecCopyError,
        VerifyError,
        WrapError,
    ) as error:
        raise RunRefused(str(error)) from error
    return Checked(
        run_id=run_id,
        request=request,
        records=records,
        commit=commit,
        request_sha256=request_sha,
        app=app,
        source=source,
        source_session=source_session,
        source_seal=source_seal,
        version=version,
        adapter=adapter,
        factory=f"build_from_spec.wrap:{name}",
        earlier=tuple(earlier),
    )


def _given_json(setup: str, given: GivenFiles) -> dict[str, Any]:
    """The `given` field of the run data file, in the shape design 4.4 gives for the setup."""
    if setup == "spec":
        return {"spec": {name: hashlib.sha256(data).hexdigest() for name, data in given.files.items()}}
    if setup == "record":
        return {"record": {"removed": [{"seq": item.seq, "hash": item.hash} for item in given.removed]}}
    return {}


def _scanner(root: Path, app: App) -> Scanner:
    try:
        return Scanner.from_config([root / app.scan_sources], root / STOP_LIST)
    except ScanError as error:
        raise RunStopped(f"the blind scan cannot be set up: {error}") from error


def _config_text(root: Path, config: Path, checked: Checked, arguments: Arguments) -> str:
    """The session config of design 4.2. Paths are relative to the config file's folder (design 4.2)."""
    base = config.parent
    values: dict[str, Any] = {
        "session_id": checked.run_id,
        "application": checked.app.name,
        "adapter": checked.factory,
        "lab_dir": checked.run_id,
        "spec_files": [f"{LAB_SPEC}{name}" for name in SPEC_FILES],
        "experiments_dir": "experiments",
        "state_dir": STATE,
        "sessions_dir": _relative(checked.records, base),
        "seed": arguments.seed,
        "scan_sources": [_relative(root / checked.app.scan_sources, base)],
        "stop_list": _relative(root / STOP_LIST, base),
        "discovered_table": DISCOVERED_TABLE,
        "resume": True,
    }
    return "".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items())


def prepare(arguments: Arguments, checked: Checked, root: Path) -> Path:
    """Phase B (design 3.9, steps 1-6). Return the session config's path. A failure keeps the folder."""
    run_dir = _run_dir(root)
    folder = run_dir / checked.run_id
    try:
        (run_dir / STATE).mkdir(parents=True, exist_ok=True)
        checked.records.mkdir(parents=True, exist_ok=True)
        given = given_files(arguments.setup, checked.source)
        write_folder(folder, checked.request, given)
    except (FolderError, ReducedError, SpecCopyError) as error:
        kept = f"; the working folder {folder} is kept" if folder.exists() else ""
        raise RunStopped(f"{error}{kept}") from error
    files = file_hashes(folder)
    tools = tool_hashes(checked.adapter)
    data = {
        "format": FORMAT,
        "run": checked.run_id,
        "setup": arguments.setup,
        "request": {"id": checked.request.id, "commit": checked.commit, "sha256": checked.request_sha256},
        "source": {
            "application": checked.app.name,
            "session": checked.source_session,
            "seal": checked.source_seal,
        },
        "seed": arguments.seed,
        "adapter": checked.factory,
        "kiro": {"version": checked.version, "model": arguments.model, "effort": arguments.effort},
        "files": files,
        "tools": tools,
        "given": _given_json(arguments.setup, given),
        "prompts": [],
    }
    lines: list[str] = []
    for name, earlier in checked.earlier:
        lines += differences("this run", data, name, earlier)
    if lines:
        raise RunStopped(
            "the working folder differs from an earlier run of this request; "
            f"the folder {folder} is kept:\n" + "\n".join(lines)
        )
    scanner = _scanner(root, checked.app)
    findings = scan_folder(scanner, folder)
    for name, text in descriptions(checked.adapter.declaration(), DISCOVERED_TABLE).items():
        findings += scanner.scan_text(text, "builder", f"tool {name}")
    if findings:
        listed = "\n".join(str(finding) for finding in findings)
        raise RunStopped(f"the blind scan finds items in the working folder {folder}; it is kept:\n{listed}")
    write_run_data(run_dir / f"{checked.run_id}{RUN_DATA_SUFFIX}", data)
    config = run_dir / f"{checked.run_id}{CONFIG_SUFFIX}"
    config.write_text(_config_text(root, config, checked, arguments), encoding="utf-8")
    return config


def start(config: Path) -> None:
    """Phase C (design 3.9): load the config, start the session with the core, and close it again. A refusal
    stops the run before the reader starts (Requirement 11.7)."""
    try:
        loaded = config_file.load(config)
    except config_file.ConfigError as error:
        raise RunStopped(str(error)) from error
    outcome = Session.start(loaded.session)
    if not isinstance(outcome, Ran):
        raise RunStopped(f"the bench refused to start the session: {outcome.message.plain()}")
    outcome.result.close()


def _stop_session(config: Path, run_id: str, reason: str) -> None:
    """`bench-stop` with the reason (Requirement 11.9). The reason is sealed in the record."""
    if stop.main([str(config), "--reason", reason]) != 0:
        raise RunStopped(
            f"bench-stop could not seal run {run_id} as stopped; the session is still open and "
            "the user must stop it by hand"
        )


def execute(
    arguments: Arguments, checked: Checked, root: Path, apps: Mapping[str, App], kiro: Kiro, config: Path
) -> Path:
    """Phases D and E (design 3.9, 3.10). Return the run file's path."""
    run_dir = _run_dir(root)
    run_id = checked.run_id
    data_path = run_dir / f"{run_id}{RUN_DATA_SUFFIX}"
    data = read_run_data(data_path)
    folder = (run_dir / run_id).resolve()
    state = run_dir / STATE / run_id
    env = {
        **os.environ,
        "BENCH_SESSION_CONFIG": str(config.resolve()),
        "BENCH_HOOK_LOG": str((run_dir / f"{run_id}{HOOK_LOG_SUFFIX}").resolve()),
    }
    prompts: list[Prompt] = []

    def launch(kind: str) -> int:
        number = len(prompts) + 1
        command = kiro_command(kind, arguments.model, arguments.effort)
        return kiro.turn(command, folder, env, run_dir / f"{run_id}.turn-{number}.log")

    def entries() -> tuple[int, bool]:
        found = verify(state, sealed=False)
        return len(found), found[-1]["kind"] == "seal"

    def save(recorded: tuple[Prompt, ...]) -> None:
        prompts[:] = list(recorded)
        write_run_data(data_path, {**data, "prompts": [asdict(p) for p in recorded]})

    ended: TurnsEnd | None = None
    failure: str | None = None
    try:
        ended = run_turns(launch, entries, save)
    # The session has started, so the failure becomes the stop reason (11.9). It is not hidden: it is printed,
    # sealed, and raised again as RunStopped after the run file is written.
    except Exception as error:  # noqa: BLE001
        failure = " ".join(str(error).split()) or type(error).__name__
        print(f"bfs-run: {error}", file=sys.stderr)
    if failure is not None:
        _stop_session(config, run_id, failure)
    elif ended is not None and not ended.sealed:
        _stop_session(config, run_id, str(ended.stop_reason))
    destination = checked.records / checked.app.name / run_id
    if not destination.is_dir():
        raise RunStopped(
            f"sealing failed for run {run_id}: the record stayed in {state}; "
            f"read {state / 'builder.log'}. No run file was written (Requirement 13.5)."
        )
    try:
        run_file = write_run_file(run_id, apps, root / STOP_LIST, root, checked.records)
    except (JudgeError, ReliedError, RequestError, RunFileError, ScanError) as error:
        raise RunStopped(
            f"{error}; run {run_id} is sealed, so its run file can be written with "
            f"bfs-run-file {run_id} once the cause is fixed"
        ) from error
    if failure is not None:
        raise RunStopped(
            f"run {run_id} stopped after the session started: {failure}; the run file is {run_file}"
        )
    return run_file


def run_script(arguments: Arguments, root: Path, apps: Mapping[str, App], kiro: Kiro) -> Path:
    """The whole run: phases A to E. Return the run file's path. Raises RunRefused or RunStopped."""
    checked = check(arguments, root, apps, kiro)
    config = prepare(arguments, checked, root)
    start(config)
    return execute(arguments, checked, root, apps, kiro, config)


def main(argv: list[str] | None = None) -> None:
    try:
        require_repository_root()
        arguments = parse_arguments(argv)
        run_file = run_script(arguments, Path.cwd(), APPS, SubprocessKiro())
    except (AppError, RunRefused) as error:
        print(f"bfs-run: refused: {error}", file=sys.stderr)
        raise SystemExit(2) from error
    except RunStopped as error:
        print(f"bfs-run: stopped: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    end = read_run_file(run_file)["record"]["end"]
    print(
        f"bfs-run: run {run_file.name.removesuffix(RUN_FILE_SUFFIX)} is sealed as {end}; run file {run_file}"
    )
