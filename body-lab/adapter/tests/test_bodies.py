"""body-lab design 10 and Requirement 7: the second body, its variant labels and its scan sources."""

import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import pytest
from bench.adapter import check_result

from body_lab import sim
from body_lab.adapter import BodyAdapter
from body_lab.settings import BODIES, MODEL_DIR, WIRING_FILE, Settings

ADAPTER_DIR = Path(__file__).resolve().parents[1]


def _can_render() -> bool:
    """The same check as test_adapter.py: a trial that renders needs an offscreen OpenGL context."""
    try:
        model = mujoco.MjModel.from_xml_string("<mujoco><worldbody/></mujoco>")
        mujoco.Renderer(model, 8, 8).close()
    except Exception:  # noqa: BLE001 - any failure here means no offscreen context
        return False
    return True


needs_gl = pytest.mark.skipif(not _can_render(), reason="no offscreen OpenGL context for MuJoCo")


def actuator_names(path: Path) -> set[str]:
    return {a.get("name") for a in ET.parse(path).getroot().iter("position")} | {
        a.get("name") for a in ET.parse(path).getroot().iter("velocity")
    }


def test_wiring_actuators_exist_in_both_bodies() -> None:
    import json

    wired = {c["actuator"] for c in json.loads(WIRING_FILE.read_text(encoding="utf-8"))["channels"]}
    for label, path in BODIES.items():
        assert wired <= actuator_names(path), label


def test_scan_sources_name_every_model_file() -> None:
    with (ADAPTER_DIR / "scan_sources.toml").open("rb") as f:
        named = tomllib.load(f)["source"]
    resolved = {(ADAPTER_DIR / s["path"]).resolve() for s in named}
    model_files = {p.resolve() for p in MODEL_DIR.iterdir() if p.suffix in (".xml", ".json")}
    assert model_files <= resolved, sorted(p.name for p in model_files - resolved)


def test_both_bodies_tell_the_same_declaration() -> None:
    assert BodyAdapter(variant="a").declaration() == BodyAdapter(variant="b").declaration()


def test_no_variant_gives_the_declaration_but_no_trial() -> None:
    adapter = BodyAdapter()
    assert adapter.declaration() == BodyAdapter(variant="a").declaration()
    inputs = {k.name: tuple(0.0 for _ in adapter.sample_times) for k in adapter.declaration().knobs}
    with pytest.raises(RuntimeError, match="without a variant"):
        adapter.run_trial(inputs, seed=0)


def test_unknown_variant_is_refused() -> None:
    with pytest.raises(ValueError, match="one of a, b"):
        BodyAdapter(variant="c")


def test_axle_touches_nothing_and_stays_above_the_floor() -> None:
    model = sim.build(Settings(), "b").model
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "wheel")
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    geoms = [g for g in range(model.ngeom) if model.geom_bodyid[g] == body]
    assert len(geoms) == 1, "the wheel keeps only its axle"
    g = geoms[0]
    assert model.geom_contype[g] == 0 and model.geom_conaffinity[g] == 0
    lowest = data.geom_xpos[g][2] - model.geom_size[g][0]  # a capsule along y: its radius is the lowest reach
    assert lowest > 0


@needs_gl
def test_trial_on_body_b_meets_the_contract() -> None:
    adapter = BodyAdapter(variant="b")
    inputs = {k.name: tuple(0.0 for _ in adapter.sample_times) for k in adapter.declaration().knobs}
    result = adapter.run_trial(inputs, seed=0)
    check_result(adapter.declaration(), result)
