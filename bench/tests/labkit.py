"""Helpers for session tests. A temporary lab: Dr. Kiro's spec files, the experiments folder, and a
session config against the fake application."""

import os
import textwrap
from dataclasses import replace
from pathlib import Path

from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.fake.adapter import FakeAdapter

REPO = Path(__file__).resolve().parents[2]
FAKE_SOURCES = REPO / "bench" / "src" / "bench" / "fake" / "scan_sources.toml"
STOP_LIST = REPO / ".kiro" / "blind-scan" / "stop-list.txt"
SPEC_DIR = ".kiro/specs/lab"

DESIGN_START = "# Design\n\n## Discovered spec\n"


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


def exp_file(hid: str, rows: list[list[float]], *, mode: str = "compare", phase: str = "map",
               sweep: list[str] | None = None, body: str = "return amp") -> str:  # fmt: skip
    sweep_line = f"SWEEP = {sweep!r}\n" if sweep is not None else ""
    return (
        f"# {hid}: experiment\n"
        f'PHASE = "{phase}"\nMODE = "{mode}"\nPARAMS = ["amp", "gain"]\n{sweep_line}TRIALS = {rows!r}\n\n'
        f"def drive(t, amp):\n    {body}\n"
    )


class Lab:
    def __init__(self, root: Path, budget: int = 12) -> None:
        self.root = root
        self.lab = root / "lab"
        (self.lab / SPEC_DIR).mkdir(parents=True)
        (self.lab / "experiments").mkdir()
        (root / "state").mkdir()
        (root / "sessions").mkdir()
        self.hypotheses: list[str] = []
        self.write_requirements()
        self.write("design.md", DESIGN_START)
        self.write("tasks.md", "# Tasks\n\n- [ ] map the system\n")
        self.config = SessionConfig(
            session_id="s1",
            application="fake",
            adapter=FakeAdapter(budget=budget),
            lab_dir=self.lab,
            spec_files=(f"{SPEC_DIR}/requirements.md", f"{SPEC_DIR}/design.md", f"{SPEC_DIR}/tasks.md"),
            experiments_dir="experiments",
            state_dir=root / "state",
            sessions_dir=root / "sessions",
            seed=7,
            scan_sources=(FAKE_SOURCES,),
            stop_list=STOP_LIST,
            discovered_table="required",
        )

    def write(self, name: str, text: str) -> None:
        (self.lab / SPEC_DIR / name).write_text(text)

    def read(self, name: str) -> str:
        return (self.lab / SPEC_DIR / name).read_text()

    def write_requirements(self) -> None:
        self.write("requirements.md", "# Requirements\n\n## Hypotheses\n\n" + "\n".join(self.hypotheses))

    def add(self, block: str) -> None:
        self.hypotheses.append(block)
        self.write_requirements()

    def experiment(self, name: str, text: str) -> str:
        (self.lab / "experiments" / name).write_text(textwrap.dedent(text))
        return f"experiments/{name}"

    def start(self, **changes: object) -> Session:
        outcome = Session.start(replace(self.config, **changes))
        assert isinstance(outcome, Ran), outcome
        return outcome.result


def examples(count: int) -> int:
    """Property test example counts, multiplied by BENCH_PROPERTY_SCALE (default 1) for thorough runs."""
    return count * int(os.environ.get("BENCH_PROPERTY_SCALE", "1"))
