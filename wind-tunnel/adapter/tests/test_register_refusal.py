"""A normal refusal stays a refusal with the real wind-tunnel scan (wind-tunnel Decision 44).

Session wt-003 ended at its first action: the refusal for a point range `[1, 1]` said "empty", a word the
solver files use, and `Session._finish` scans every outcome at builder level, so a normal refusal became a
bench failure. This test drives the real Session with the real WindAdapter (fake runner, no Docker),
the real `scan_sources.toml` and the real stop list.
"""

import sys
from pathlib import Path

from bench.core.outcome import Ran, Refused
from bench.core.session import Session, SessionConfig
from bench.drkiro.lab import FILES, TEMPLATES, make_lab

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_runner import FakeRunner, fake_docker, small_settings, write_lock  # noqa: E402
from wind_tunnel_model.mesh import FakeMesher  # noqa: E402

from wind_tunnel.adapter import WindAdapter  # noqa: E402

ADAPTER = Path(__file__).resolve().parents[1]
ROOT = ADAPTER.parents[1]
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
SPEC = ".kiro/specs/lab"
KNOBS = ("aspect", "corner", "splitter", "angle")


def _block(hid: str, pid: str, low: float, high: float) -> str:
    when = "\n".join(f"{k} = {v!r}" for k, v in zip(KNOBS, (1.5, 0.5, 1.0, 10.0), strict=True))
    return (
        f"### {hid}: point range\n\nWHEN the knobs are set, THE system SHALL give a shedding value.\n\n"
        f'```prediction\n[[prediction]]\nid = "{pid}"\nmeasurement = "shedding"\n'
        f'range = [{low!r}, {high!r}]\nlabel = "inside"\n[prediction.when]\n{when}\n```\n'
    )


def _start(tmp_path: Path) -> tuple[Session, Path]:
    settings = small_settings()
    adapter = WindAdapter(
        settings,
        runner=FakeRunner(settings),
        mesher=FakeMesher(),
        command=fake_docker(settings),
        lock_path=write_lock(tmp_path),
        record_path=tmp_path / "environment.jsonl",
        case_base=tmp_path / "cases",
    )
    lab = tmp_path / "lab"
    lab.mkdir()
    make_lab(lab)
    for source, target in TEMPLATES.items():
        (lab / target).parent.mkdir(parents=True, exist_ok=True)
        (lab / target).write_bytes((FILES / source).read_bytes())
    for name in ("state", "sessions"):
        (tmp_path / name).mkdir()
    config = SessionConfig(
        session_id="t1",
        application="wind-tunnel",
        adapter=adapter,
        lab_dir=lab,
        spec_files=(f"{SPEC}/requirements.md", f"{SPEC}/design.md", f"{SPEC}/tasks.md"),
        experiments_dir="experiments",
        state_dir=tmp_path / "state",
        sessions_dir=tmp_path / "sessions",
        seed=1,
        scan_sources=(ADAPTER / "scan_sources.toml",),
        stop_list=STOP_LIST,
        discovered_table="required",
    )
    started = Session.start(config)
    assert isinstance(started, Ran), started
    return started.result, lab


def test_a_point_range_is_a_refusal_not_a_bench_failure(tmp_path: Path) -> None:
    session, lab = _start(tmp_path)
    requirements = lab / SPEC / "requirements.md"
    requirements.write_text(requirements.read_text(encoding="utf-8") + "\n" + _block("H1", "P1", 1, 1))
    outcome = session.register("H1")
    assert isinstance(outcome, Refused), outcome
    assert "strictly below high" in outcome.message.plain()
    assert "a single value is not accepted as a range" in outcome.message.plain()
    assert "[0.5, 1.5] for the value 1" in outcome.message.plain()
    assert session.state.sealed is None
    assert session.last_failure_detail is None
    # the session is still open: a corrected hypothesis is accepted
    requirements.write_text(
        requirements.read_text(encoding="utf-8") + "\n" + _block("H2", "P2", 0.5, 1.5), encoding="utf-8"
    )
    assert isinstance(session.register("H2"), Ran)
