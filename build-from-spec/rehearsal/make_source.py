"""Make the rehearsal's source record: one sealed, ended session of the fake application (RUN.md, step a).

The session is made with the bench's own API: start, register, run, verdict, end. The application is the fake
one, not body-lab. Its numbers are not results; they only give the reader a record to read.

Run from the repository root:
    uv run --project build-from-spec python build-from-spec/rehearsal/make_source.py

Everything is written under bench-run/build-from-spec/rehearsal/ (git-ignored, builder side). The
script refuses to run when the session already exists, so a second run never overwrites a record.

Layout, relative to the repository root (REHEARSAL = bench-run/build-from-spec/rehearsal):
    REHEARSAL/sessions/fake/rehearsal-src/   the sealed source record; REHEARSAL/sessions is sessions_dir
    REHEARSAL/state/rehearsal-src/           the bench's state of the session
    REHEARSAL/lab/rehearsal-src/             the lab of the session (spec files and experiments)
"""

import argparse
import sys
from pathlib import Path

from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.fake.adapter import FakeAdapter

from build_from_spec.apps import REHEARSAL_ROOT, AppError, require_repository_root

SESSION = "rehearsal-src"
SEED = 7
SPEC_DIR = ".kiro/specs/lab"
SPEC_FILES = (f"{SPEC_DIR}/requirements.md", f"{SPEC_DIR}/design.md", f"{SPEC_DIR}/tasks.md")
FAKE_SOURCES = "bench/src/bench/fake/scan_sources.toml"
STOP_LIST = ".kiro/blind-scan/stop-list.txt"

# One hypothesis about the fake application, with one prediction that the experiment below meets. The
# prediction's range (0.4 to 0.6) contains the measured distance 0.5, so the verdict is supported.
STATEMENT = "WHEN the drive rises, THE distance SHALL rise."
HYPOTHESIS = (
    "### H1: about H1\n\n"
    f"{STATEMENT}\n\n"
    "```prediction\n# relies on: none\n"
    '[[prediction]]\nid = "P1"\nmeasurement = "distance"\nrange = [0.4, 0.6]\nlabel = "inside"\n'
    "[prediction.when]\namp = 0.5\ngain = 1.0\n```\n"
)
EXPERIMENT = (
    "# H1: experiment\n"
    'PHASE = "map"\nMODE = "compare"\nPARAMS = ["amp", "gain"]\nTRIALS = [[0.5, 1.0]]\n\n'
    "def drive(t, amp):\n    return amp\n"
)


def fail(message: str) -> None:
    sys.exit(f"make_source: {message}")


def checked(outcome):
    """The result of a bench call that must run. A refusal stops the script with the bench's own words."""
    if not isinstance(outcome, Ran):
        fail(f"the bench refused a step: {outcome.message.plain()}")
    return outcome.result


def main(argv: list[str] | None = None) -> None:
    # No arguments: the parser exists so that --help describes the script without making a record.
    parser = argparse.ArgumentParser(
        prog="make_source",
        description="Make the rehearsal's source record: one sealed session of the fake application.",
    )
    parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        require_repository_root()
    except AppError as error:
        fail(str(error))
    root = Path.cwd()
    rehearsal = root / REHEARSAL_ROOT
    sessions = rehearsal / "sessions"
    state = rehearsal / "state"
    lab = rehearsal / "lab" / SESSION
    record = sessions / "fake" / SESSION
    for existing in (state / SESSION, lab, record):
        if existing.exists():
            fail(f"{existing} already exists; the source is made once. Remove it by hand to make it again.")
    for folder in (sessions, state):
        folder.mkdir(parents=True, exist_ok=True)
    spec = lab / SPEC_DIR
    spec.mkdir(parents=True)
    (lab / "experiments").mkdir()
    (spec / "requirements.md").write_text(
        "# Requirements\n\n## Hypotheses\n\n" + HYPOTHESIS, encoding="utf-8"
    )
    (spec / "design.md").write_text("# Design\n", encoding="utf-8")
    (spec / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    config = SessionConfig(
        session_id=SESSION,
        application="fake",
        adapter=FakeAdapter(),
        lab_dir=lab,
        spec_files=SPEC_FILES,
        experiments_dir="experiments",
        state_dir=state,
        sessions_dir=sessions,
        seed=SEED,
        scan_sources=(root / FAKE_SOURCES,),
        stop_list=root / STOP_LIST,
        discovered_table="not-required",
    )
    session = checked(Session.start(config))
    assert isinstance(session, Session)
    checked(session.register("H1"))
    (lab / "experiments" / "e1.py").write_text(EXPERIMENT, encoding="utf-8")
    checked(session.run("experiments/e1.py"))
    checked(session.verdict("E1", "supported", "the distance rose with the drive; the prediction held"))
    checked(session.end())
    sealed = session.sealed_path
    session.close()
    if sealed is None or Path(sealed).resolve() != record.resolve():
        fail(f"the record was sealed at {sealed}, not at {record}")
    print(f"make_source: sealed the rehearsal source at {sealed}")


if __name__ == "__main__":
    main()
