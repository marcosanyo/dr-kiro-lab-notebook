"""body-lab design 7: the four adapter tests (Requirement 6.1).

The two tests that render need an offscreen OpenGL context (MuJoCo's renderer). Where none is available they
are skipped with that reason, and the run says so; they are never replaced by something else.
"""

from pathlib import Path

import mujoco
import pytest
from bench.adapter import NotMeasured, TrialResult, check_declaration, check_result
from bench.pictures import check_picture
from bench.scan.scan import Scanner, local_paths
from bench.scan.terms import load_app, load_stop_list

from body_lab import sim
from body_lab.adapter import BodyAdapter
from body_lab.measure import PoseMeasurer
from body_lab.settings import Settings

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ROOT / "body-lab" / "adapter" / "scan_sources.toml"
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"


def _can_render() -> bool:
    try:
        model = mujoco.MjModel.from_xml_string("<mujoco><worldbody/></mujoco>")
        mujoco.Renderer(model, 8, 8).close()
    except Exception:  # noqa: BLE001 - any failure here means no offscreen context
        return False
    return True


needs_gl = pytest.mark.skipif(not _can_render(), reason="no offscreen OpenGL context for MuJoCo")


def zero_inputs(adapter: BodyAdapter) -> dict[str, tuple[float, ...]]:
    return {k.name: tuple(0.0 for _ in adapter.sample_times) for k in adapter.declaration().knobs}


@needs_gl
def test_trial_result_meets_the_contract() -> None:
    adapter = BodyAdapter(variant="a")
    result = adapter.run_trial(zero_inputs(adapter), seed=0)
    assert isinstance(result, TrialResult)
    check_result(adapter.declaration(), result)
    check_picture("image/png", result.picture.data)


@needs_gl
def test_same_inputs_give_the_same_result() -> None:
    adapter = BodyAdapter(variant="a")
    inputs = zero_inputs(adapter)
    inputs["c1"] = tuple(0.5 for _ in adapter.sample_times)
    assert adapter.run_trial(inputs, seed=1) == BodyAdapter(variant="a").run_trial(inputs, seed=2)


def test_turned_over_body_is_lost() -> None:
    settings = Settings(start_roll_deg=180.0)
    adapter = BodyAdapter(settings, variant="a")  # the declaration and simulation need no renderer
    poses = sim.run(adapter.body, settings, zero_inputs(adapter), adapter.series_times, (), lambda d: None)
    values = PoseMeasurer(settings).measure(poses)
    assert all(isinstance(v, NotMeasured) and v.outcome == "lost" for v in values.values())


def test_declaration_is_blind() -> None:
    decl = BodyAdapter(variant="a").declaration()
    check_declaration(decl)
    assert [k.name for k in decl.knobs] == [f"c{i}" for i in range(sim.channel_count())]
    assert decl.budget == 40 and decl.fake is False
    assert "not measured from a camera image" in decl.measured_by
    scanner = Scanner([load_app(SOURCES)], load_stop_list(STOP_LIST), local_paths=local_paths(STOP_LIST))
    text = " ".join([decl.goal, decl.measured_by, *(m.name for m in decl.measurements)])
    assert scanner.scan_text(text, "builder", "declaration") == []


def test_declaration_matches_golden_files() -> None:
    """lab-bench design A5, Requirement 18.8: the told text and the recorded declaration are byte for byte
    what they were before the knob description amendment. The golden files are never edited."""
    from bench.core.session import declaration_record
    from bench.frontend.describe import declaration_text
    from bench.record.canonical import canonical_json

    golden = Path(__file__).resolve().parent / "golden"
    decl = BodyAdapter(variant="a").declaration()
    assert declaration_text(decl).encode("utf-8") == (golden / "told_text.txt").read_bytes()
    assert canonical_json(declaration_record(decl)) == (golden / "declaration_record.json").read_bytes()


def test_goldens_were_changed_only_to_drop_the_engine() -> None:
    """The told text and declaration record name neither the engine nor a version (tasks 27)."""
    from bench.core.session import declaration_record
    from bench.frontend.describe import declaration_text
    from bench.record.canonical import canonical_json

    decl = BodyAdapter(variant="a").declaration()
    for text in (declaration_text(decl), canonical_json(declaration_record(decl)).decode("utf-8")):
        assert "mujoco" not in text.lower()
        assert mujoco.__version__ not in text


def test_builder_versions_name_the_engine_version() -> None:
    assert BodyAdapter(variant="a").builder_versions() == {"mujoco": mujoco.__version__}
