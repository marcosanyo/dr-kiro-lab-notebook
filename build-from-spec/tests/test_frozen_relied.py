"""Task 11.3: the frozen part that the bench records for a registered H1 keeps the relied-on line
byte for byte (Requirements 10.3, 10.6). A real bench session on the fake application registers H1; the
check reads the frozen blob that the register entry points to."""

from pathlib import Path

from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.fake.adapter import FakeAdapter

from build_from_spec.relied import relied_line

ROOT = Path(__file__).resolve().parents[2]
FAKE_SOURCES = ROOT / "bench" / "src" / "bench" / "fake" / "scan_sources.toml"
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
SPEC_DIR = ".kiro/specs/lab"
LINE = "# relies on: none"
H1 = f"""### H1: about H1

WHEN amp rises, THE distance SHALL rise.

```prediction
{LINE}
[[prediction]]
id = "P1"
measurement = "distance"
range = [0.4, 0.6]
label = "inside"
[prediction.when]
amp = 0.5
gain = 1.0
```
"""


def make_config(root: Path) -> SessionConfig:
    lab = root / "lab"
    spec = lab / SPEC_DIR
    spec.mkdir(parents=True)
    (lab / "experiments").mkdir()
    (root / "state").mkdir()
    (root / "sessions").mkdir()
    (spec / "requirements.md").write_text("# Requirements\n\n## Hypotheses\n\n" + H1, encoding="utf-8")
    (spec / "design.md").write_text("# Design\n\n## Discovered spec\n", encoding="utf-8")
    (spec / "tasks.md").write_text("# Tasks\n\n- [ ] map the system\n", encoding="utf-8")
    return SessionConfig(
        session_id="s1",
        application="fake",
        adapter=FakeAdapter(budget=12),
        lab_dir=lab,
        spec_files=(f"{SPEC_DIR}/requirements.md", f"{SPEC_DIR}/design.md", f"{SPEC_DIR}/tasks.md"),
        experiments_dir="experiments",
        state_dir=root / "state",
        sessions_dir=root / "sessions",
        seed=7,
        scan_sources=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        discovered_table="required",
    )


def test_frozen_part_of_registered_h1_keeps_the_relied_on_line(tmp_path: Path) -> None:
    started = Session.start(make_config(tmp_path))
    assert isinstance(started, Ran), started
    session = started.result
    assert isinstance(session.register("H1"), Ran)

    (register,) = [e for e in session.store.entries if e["kind"] == "register"]
    frozen = session.store.read_blob(register["body"]["frozen"]).decode("utf-8")

    assert frozen == H1
    assert f"```prediction\n{LINE}\n[[prediction]]" in frozen
    assert relied_line(frozen) == LINE
    session.close()
