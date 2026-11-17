"""A real session through `bench.core.session.Session` with the bench's fake application (design, Testing
Strategy, "Session fixture"). The set-up follows `bench/tests/labkit.py`; the pattern is copied, the bench
test module is not imported.

Every record made here is labelled fake (the fake application's declaration and every trial say so), lives in
a temporary folder and is never built into a site. The fake application's numbers are not results.

`accepted_session(root)` runs the session and ends it with an accepted table. The steps, in order:

1. run E1, verdict E1 (verdict snapshot 1, table: the start table only, no rows);
2. run E2, verdict E2 (verdict snapshot 2);
3. end with the accepted table.

`accepted_session(root, middle_steps=True)` (task 18.2) changes the two verdict snapshots: before verdict E1,
`design.md` holds a table where R1 is `rejected` and replaced by R2, and R2 is `observed` (the replay's first
step strikes R1); before verdict E2, `design.md` holds a table with a header and no rows, which the bench's
reader does not accept (the replay's second step is unreadable). The end table is the same in both variants.
`Lab.write("design.md", ...)` before a verdict sets the table that the verdict snapshot holds.
"""

import textwrap
from dataclasses import dataclass, replace
from pathlib import Path

import bench.fake
from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.fake.adapter import FakeAdapter

REPO = Path(__file__).resolve().parents[3]
FAKE_SOURCES = Path(bench.fake.__file__).resolve().parent / "scan_sources.toml"
STOP_LIST = REPO / ".kiro" / "blind-scan" / "stop-list.txt"
SPEC_DIR = ".kiro/specs/lab"
APPLICATION = "fake"
SESSION_ID = "s1"

DESIGN_START = "# Design\n\n## Discovered spec\n"

END_TABLE = """
| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | distance grows with amp | gain 1 | E1 | H1.P1 | observed | |
| R2 | the best point stays below 2.5 | amp 1, gain 3 | E2 | H2.P1 | rejected | R3 |
| R3 | distance at amp 1 and gain 3 is the highest seen | amp 1, gain 3 | E2 | | observed | |
"""

# Task 18.2: the table of the first verdict snapshot (a `rejected` row and the row that replaces it).
MIDDLE_TABLE = """
| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | distance grows with amp | gain 1 | E1 | H1.P1 | rejected | R2 |
| R2 | distance grows with amp at gain 1 | gain 1 | E1 | H1.P1 | observed | |
"""

# Task 18.2: the table of the second verdict snapshot. A header and no rows: the bench's reader refuses it
# ("the discovered spec table has no rules"), so the replay step shows it as unreadable (Requirement 16.6).
UNREADABLE_TABLE = """
| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
"""


def ok(outcome: object) -> object:
    assert isinstance(outcome, Ran), outcome
    return outcome.result


def hyp_block(hid: str, statement: str, *predictions: dict) -> str:
    """A hypothesis block. Each prediction: id, measurement, range, label, when."""
    blocks = []
    for p in predictions:
        when = "\n".join(f"{k} = {v!r}" for k, v in p["when"].items())
        blocks.append(
            f'[[prediction]]\nid = "{p["id"]}"\nmeasurement = "{p.get("measurement", "distance")}"\n'
            f'range = [{p["range"][0]!r}, {p["range"][1]!r}]\nlabel = "{p.get("label", "inside")}"\n'
            f"[prediction.when]\n{when}\n"
        )
    return f"### {hid}: about {hid}\n\n{statement}\n\n```prediction\n" + "".join(blocks) + "```\n"


def exp_file(
    hid: str,
    rows: list[list[float]],
    *,
    mode: str = "compare",
    phase: str = "map",
    sweep: list[str] | None = None,
) -> str:
    sweep_line = f"SWEEP = {sweep!r}\n" if sweep is not None else ""
    return (
        f"# {hid}: experiment\n"
        f'PHASE = "{phase}"\nMODE = "{mode}"\nPARAMS = ["amp", "gain"]\n{sweep_line}TRIALS = {rows!r}\n\n'
        "def drive(t, amp):\n    return amp\n"
    )


class Lab:
    """A temporary lab: Dr. Kiro's spec files, the experiments folder, and a session config against the fake
    application."""

    def __init__(self, root: Path, budget: int = 12) -> None:
        self.root = root
        self.lab = root / "lab"
        (self.lab / SPEC_DIR).mkdir(parents=True)
        (self.lab / "experiments").mkdir()
        (root / "state").mkdir()
        self.sessions = root / "sessions"
        self.sessions.mkdir()
        self.hypotheses: list[str] = []
        self.write_requirements()
        self.write("design.md", DESIGN_START)
        self.write("tasks.md", "# Tasks\n\n- [ ] map the system\n")
        self.config = SessionConfig(
            session_id=SESSION_ID,
            application=APPLICATION,
            adapter=FakeAdapter(budget=budget),
            lab_dir=self.lab,
            spec_files=(f"{SPEC_DIR}/requirements.md", f"{SPEC_DIR}/design.md", f"{SPEC_DIR}/tasks.md"),
            experiments_dir="experiments",
            state_dir=root / "state",
            sessions_dir=self.sessions,
            seed=7,
            scan_sources=(FAKE_SOURCES,),
            stop_list=STOP_LIST,
        )

    def write(self, name: str, text: str) -> None:
        (self.lab / SPEC_DIR / name).write_text(text)

    def write_requirements(self) -> None:
        self.write("requirements.md", "# Requirements\n\n## Hypotheses\n\n" + "\n".join(self.hypotheses))

    def add(self, block: str) -> None:
        self.hypotheses.append(block)
        self.write_requirements()

    def experiment(self, name: str, text: str) -> str:
        (self.lab / "experiments" / name).write_text(textwrap.dedent(text))
        return f"experiments/{name}"

    def start(self, **changes: object) -> Session:
        session = ok(Session.start(replace(self.config, **changes)))
        assert isinstance(session, Session)
        return session


@dataclass(frozen=True)
class SessionFixture:
    session: Session  # the live session after sealing; its state is the state at the end
    sealed: Path  # the sealed record folder, `<root>/sessions/fake/s1`
    sessions: Path  # the sessions folder that holds it
    name: str  # the record name `records.load_record` is given


def accepted_session(root: Path, *, middle_steps: bool = False) -> SessionFixture:
    """A fake session of two experiments that ends with an accepted discovered spec table.

    `middle_steps=True` (task 18.2) sets the table of each verdict snapshot as the module docstring describes;
    the default is the fixture of every earlier task, unchanged."""
    lab = Lab(root)
    session = lab.start()

    # E1: a sweep of amp at gain 1; H1.P1 is a hit.
    lab.add(
        hyp_block(
            "H1",
            "WHEN amp rises at gain 1, THE distance SHALL rise.",
            {"id": "P1", "range": [0.25, 0.35], "label": "not-comparable", "when": {"amp": 0.3, "gain": 1.0}},
        )
    )
    ok(session.register("H1"))
    sweep = [[a, 1.0] for a in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)]
    ok(session.run(lab.experiment("e1_sweep_amp.py", exp_file("H1", sweep, mode="sweep", sweep=["amp"]))))
    lab.write("tasks.md", "# Tasks\n\n- [x] map the system\n- [ ] predict the best point\n")
    if middle_steps:
        lab.write("design.md", DESIGN_START + MIDDLE_TABLE)
    ok(session.verdict("E1", "supported", "distance rose with amp"))

    # E2: one trial at amp 1, gain 3; H2.P1 is a miss.
    lab.add(
        hyp_block(
            "H2",
            "WHEN amp is 1 and gain is 3, THE distance SHALL stay below 2.5.",
            {"id": "P1", "range": [2.0, 2.5], "label": "outside", "when": {"amp": 1.0, "gain": 3.0}},
        )
    )
    ok(session.register("H2"))
    ok(session.run(lab.experiment("e2_best.py", exp_file("H2", [[1.0, 3.0]], phase="best"))))
    if middle_steps:
        lab.write("design.md", DESIGN_START + UNREADABLE_TABLE)
    ok(session.verdict("E2", "rejected", "it went further than predicted"))

    lab.write("design.md", DESIGN_START + END_TABLE)
    ok(session.end())
    assert session.sealed_path is not None
    return SessionFixture(
        session=session,
        sealed=session.sealed_path,
        sessions=lab.sessions,
        name=f"sessions/{APPLICATION}/{SESSION_ID}",
    )
