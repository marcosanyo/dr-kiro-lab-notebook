"""Fixtures for the run script (tests/test_run_refusals.py, tests/test_run_end_to_end.py).

A temporary git repository holds the stop list, the request `probe` for the fake application (committed), and
the source record `fake-src`: a real session of the fake application (bench.fake), sealed as ended with its
final spec.

The fake application is `bench.fake.adapter.FakeAdapter`, loaded through the module `fake_app` in this folder.
A test calls `use_test_table` so the wrapping adapter reads the test table and the request folder.

`FakeKiro` stands in for Kiro CLI. It records each command the script builds, and its `script` decides each
turn: `reader_ends` acts through the bench, and a script that does nothing lets the run stop by itself.
The real repository's `sessions/` and `bench-run/` folders are never used.
"""

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.fake.adapter import FakeAdapter
from bench.frontend import config as config_file

from build_from_spec import wrap
from build_from_spec.apps import REQUESTS, App
from build_from_spec.request import PassRange, Request, print_request
from build_from_spec.run import Arguments
from build_from_spec.runfile import dump_text

REPO = Path(__file__).resolve().parents[2]
REAL_STOP_LIST = REPO / ".kiro" / "blind-scan" / "stop-list.txt"
FAKE_SOURCES = REPO / "bench" / "src" / "bench" / "fake" / "scan_sources.toml"
FAKE = "fake"
REQUEST_ID = "probe"
WORDS = "Move the body as far as you can."
PASS = PassRange(
    "distance", 1000.0, 2000.0
)  # outside the distance of the source trial (checked in make_source)
SOURCE_SESSION = "fake-src"
SOURCE_SEED = 7
IDENTITY = ("-c", "user.name=Test", "-c", "user.email=test@example.invalid")
SPEC_DIR = ".kiro/specs/lab"
STATEMENT = "WHEN amp rises, THE distance SHALL rise."
PREDICTION = {"id": "P1", "range": [0.4, 0.6], "when": {"amp": 0.5, "gain": 1.0}}
TEST_APPS = {FAKE: App(FAKE, "fake_app:fake_adapter", str(FAKE_SOURCES), 12, False)}
# The same fake application as the rehearsal application: its runs and records go under the rehearsal folder.
TEST_REHEARSAL_APPS = {FAKE: App(FAKE, "fake_app:fake_adapter", str(FAKE_SOURCES), 12, True)}
DESIGN = """# Design

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|----|------|-------|-------------|-------------|--------|-------------|
| R1 | the distance rises with amp | all | E1 | P1 | observed | - |
"""


def hypothesis_block(hid: str, statement: str) -> str:
    """One hypothesis of the fake application, in the format `parse_hypothesis` reads."""
    p = PREDICTION
    when = "\n".join(f"{k} = {v!r}" for k, v in p["when"].items())
    prediction = (
        f'[[prediction]]\nid = "{p["id"]}"\nmeasurement = "distance"\n'
        f'range = [{p["range"][0]!r}, {p["range"][1]!r}]\nlabel = "inside"\n[prediction.when]\n{when}\n'
    )
    return f"### {hid}: about {hid}\n\n{statement}\n\n```prediction\n# relies on: none\n{prediction}```\n"


def experiment_text(hid: str) -> str:
    """One experiment of the fake application: the drive function and its trial rows."""
    return (
        f"# {hid}: experiment\n"
        'PHASE = "map"\nMODE = "compare"\nPARAMS = ["amp", "gain"]\nTRIALS = [[0.5, 1.0]]\n\n'
        "def drive(t, amp):\n    return amp\n"
    )


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def commit_paths(root: Path, *paths: str, message: str) -> None:
    git(root, "add", "--", *paths)
    git(root, *IDENTITY, "commit", "-q", "-m", message)


def make_source(root: Path, session: str = SOURCE_SESSION, sessions: Path | None = None) -> Path:
    """Run a real session of the fake application to its end, and return the sealed record's path. The record
    goes to `sessions` (default: root/sessions), one folder per application."""
    sessions = root / "sessions" if sessions is None else sessions
    lab = root / f"source-lab-{session}"
    spec = lab / SPEC_DIR
    spec.mkdir(parents=True)
    (lab / "experiments").mkdir()
    (root / f"state-{session}").mkdir()
    sessions.mkdir(parents=True, exist_ok=True)
    (spec / "requirements.md").write_text(
        "# Requirements\n\n## Hypotheses\n\n" + hypothesis_block("H1", STATEMENT), encoding="utf-8"
    )
    (spec / "design.md").write_text(DESIGN, encoding="utf-8")
    (spec / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    config = SessionConfig(
        session_id=session,
        application=FAKE,
        adapter=FakeAdapter(),
        lab_dir=lab,
        spec_files=(f"{SPEC_DIR}/requirements.md", f"{SPEC_DIR}/design.md", f"{SPEC_DIR}/tasks.md"),
        experiments_dir="experiments",
        state_dir=root / f"state-{session}",
        sessions_dir=sessions,
        seed=SOURCE_SEED,
        scan_sources=(FAKE_SOURCES,),
        stop_list=REAL_STOP_LIST,
        discovered_table="not-required",
    )
    outcome = Session.start(config)
    assert isinstance(outcome, Ran), outcome
    session = outcome.result
    assert isinstance(session.register("H1"), Ran)
    (lab / "experiments" / "e1.py").write_text(experiment_text("H1"), encoding="utf-8")
    assert isinstance(session.run("experiments/e1.py"), Ran)
    session.verdict("E1", "supported", "held")
    assert isinstance(session.end(), Ran)
    assert session.sealed_path is not None
    session.close()
    return session.sealed_path


def make_repo(root: Path) -> Path:
    """The repository of the tests: the stop list, the source record, and the committed request."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    (root / ".kiro" / "blind-scan").mkdir(parents=True)
    shutil.copy2(REAL_STOP_LIST, root / ".kiro" / "blind-scan" / "stop-list.txt")
    (root / REQUESTS).mkdir(parents=True)
    request = Request(REQUEST_ID, FAKE, WORDS, (PASS,))
    (root / REQUESTS / f"{REQUEST_ID}.toml").write_text(print_request(request), encoding="utf-8")
    make_source(root)
    commit_paths(root, f"{REQUESTS}/{REQUEST_ID}.toml", message="request")
    return root


def change_words(root: Path, words: str) -> None:
    """Change the request's words and commit the change."""
    request = Request(REQUEST_ID, FAKE, words, (PASS,))
    (root / REQUESTS / f"{REQUEST_ID}.toml").write_text(print_request(request), encoding="utf-8")
    commit_paths(root, f"{REQUESTS}/{REQUEST_ID}.toml", message="change the request")


def use_test_table(monkeypatch: pytest.MonkeyPatch, root: Path, apps: dict = TEST_APPS) -> None:
    """Point the wrapping adapter at the test table and the repository root `root`, for one test. The request
    folder of each application is found under `root`."""
    monkeypatch.setattr(wrap, "APPS", apps)
    monkeypatch.setattr(wrap, "ROOT", root)
    monkeypatch.chdir(root)


class FakeKiro:
    """Kiro CLI for the tests: records each command and its environment, and decides each turn with `script`.

    `script(command, folder, env, number)` returns the exit code of turn `number` (1-based). Without a script,
    each turn exits 0 and does nothing."""

    def __init__(self, script: Callable[..., int] | None = None, version: str = "kiro-cli fake 0.0") -> None:
        self.script = script
        self._version = version
        self.commands: list[list[str]] = []
        self.envs: list[dict[str, str]] = []

    def version(self) -> str:
        return self._version

    def turn(self, command: list[str], folder: Path, env, log: Path) -> int:
        self.commands.append(list(command))
        self.envs.append(dict(env))
        log.write_text(f"fake turn {len(self.commands)}\n", encoding="utf-8")
        if self.script is None:
            return 0
        return self.script(command, folder, env, len(self.commands))


def reader_ends(command: list[str], folder: Path, env, number: int) -> int:
    """The fake reader's ending turn: it registers H1 in its own lab spec, runs the experiment, gives the
    verdict and ends the session. Each bench call goes through the session that the config named in the
    environment names. The first turn is the start line; every later turn resumes with the continue line."""
    assert ("--resume" in command) == (number > 1), command
    cfg = config_file.load(Path(env["BENCH_SESSION_CONFIG"]))
    session = Session.open(cfg.session)
    spec = folder / SPEC_DIR / "requirements.md"
    spec.write_text(
        spec.read_text(encoding="utf-8") + "\n" + hypothesis_block("H1", STATEMENT), encoding="utf-8"
    )
    assert isinstance(session.register("H1"), Ran)
    (folder / "experiments" / "e1.py").write_text(experiment_text("H1"), encoding="utf-8")
    assert isinstance(session.run("experiments/e1.py"), Ran)
    session.verdict("E1", "supported", "held")
    assert isinstance(session.end(), Ran)
    session.close()
    return 0


def run_args(
    setup: str = "spec",
    run: int = 1,
    seed: int = 3,
    *,
    source: str = SOURCE_SESSION,
    request: str = REQUEST_ID,
    model: str = "model-a",
    effort: str = "medium",
    sessions: str = "sessions/build-from-spec",
) -> Arguments:
    """The arguments of one run, as the command line gives them, for the test table."""
    return Arguments(
        request=f"{REQUESTS}/{request}.toml",
        setup=setup,
        source=f"sessions/{source}" if "/" in source else f"sessions/{FAKE}/{source}",
        seed=seed,
        run=run,
        model=model,
        effort=effort,
        sessions=sessions,
    )


def save(path: Path, data: dict) -> None:
    """Write a run file's text in the serialisation the run file reader expects."""
    path.write_text(dump_text(data), encoding="utf-8", newline="")


def start_only(session: str, application: str = FAKE):
    """The entries of a record that holds only its start, for `seal_record`."""

    def build(store):
        return [("start", {"session": session, "application": application, "seed": 1, "budget": 12})]

    return build
