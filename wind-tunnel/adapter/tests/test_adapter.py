"""Unit tests for the adapter and its pipeline (wind-tunnel task 11.1). No Docker and no Gmsh are used."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest
from bench.adapter import (
    NotMeasured,
    TrialFailure,
    TrialResult,
    check_declaration,
    check_result,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fake_runner import FakeRunner, fake_docker, small_settings, write_lock  # noqa: E402
from wind_tunnel_model.mesh import FakeMesher, MeshError, MeshTimeout  # noqa: E402

from wind_tunnel import adapter as adapter_module  # noqa: E402
from wind_tunnel import environment  # noqa: E402
from wind_tunnel.adapter import NOT_SETTLED_REASON, NOT_SHEDDING_REASON, WindAdapter  # noqa: E402
from wind_tunnel.environment import EnvironmentFailure  # noqa: E402
from wind_tunnel.failures import PUBLIC_REASONS, FailureKind  # noqa: E402
from wind_tunnel.runner import SolverFailure  # noqa: E402

KNOBS = {"aspect": 2.0, "corner": 0.3, "splitter": 0.5, "angle": 10.0}


@pytest.fixture
def settings():
    return small_settings()


def make(settings, tmp_path, runner=None, mesher=None):
    runner = runner if runner is not None else FakeRunner(settings)
    adapter = WindAdapter(
        settings,
        runner=runner,
        mesher=mesher if mesher is not None else FakeMesher(),
        command=fake_docker(settings),
        lock_path=write_lock(tmp_path),
        record_path=tmp_path / "environment.jsonl",
        case_base=tmp_path / "cases",
    )
    return adapter, runner


def test_declaration_is_the_declared_one(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    check_declaration(adapter.declaration())


def test_a_case_folder_that_already_exists_stops_the_trial_and_is_left_alone(settings, tmp_path):
    """No fallback (rules 2): a leftover folder of the same name is an error, never deleted or renamed. The
    bench turns the exception into a bench failure (session stops); the builder moves the folder aside."""
    adapter, runner = make(settings, tmp_path)
    leftover = tmp_path / "cases" / "0000000000000007"
    leftover.mkdir(parents=True)
    (leftover / "marker").write_text("kept", encoding="utf-8")
    with pytest.raises(FileExistsError):
        adapter.run_trial(KNOBS, 7)
    assert (leftover / "marker").read_text(encoding="utf-8") == "kept"
    assert runner.calls == []


def test_settled_run_passes_check_result_and_moves_the_case_to_the_trash(settings, tmp_path):
    adapter, runner = make(settings, tmp_path)
    result = adapter.run_trial(KNOBS, 7)
    assert isinstance(result, TrialResult)
    check_result(adapter.declaration(), result)
    assert result.values["shedding"] == 1.0
    assert result.values["strouhal"] == pytest.approx(0.17, rel=0.01)
    assert result.values["cd"] == pytest.approx(1.2, rel=1e-6)
    assert result.values["cl_amp"] == pytest.approx(0.4, rel=0.01)
    assert not (tmp_path / "cases" / "0000000000000007").exists()
    assert (tmp_path / "cases" / "trash" / "0000000000000007").is_dir()  # deleted before the next trial
    (case_dir, deadline) = runner.calls[0]
    assert case_dir.name == "0000000000000007"


def test_the_seed_does_not_change_the_result(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    assert adapter.run_trial(KNOBS, 1) == adapter.run_trial(KNOBS, 2)


def test_not_shedding_is_a_not_measured_outcome(settings, tmp_path):
    adapter, _ = make(settings, tmp_path, FakeRunner(settings, amp=0.005))
    result = adapter.run_trial(KNOBS, 1)
    assert isinstance(result, TrialResult)
    check_result(adapter.declaration(), result)
    assert result.values["strouhal"] == NotMeasured("not_shedding", NOT_SHEDDING_REASON)
    assert result.values["shedding"] == 0.0


def assert_failure(result, kind, tmp_path, seed):
    assert isinstance(result, TrialFailure)
    assert result.public_reason == PUBLIC_REASONS[kind]
    assert f"kind: {kind.value}" in result.detail
    assert (tmp_path / "cases" / f"{seed:016x}").is_dir()  # kept on failure


@pytest.mark.parametrize("kind", list(FailureKind))
def test_each_solver_failure_kind(settings, tmp_path, kind):
    failure = SolverFailure(kind, "the cause", "log tail text")
    adapter, _ = make(settings, tmp_path, FakeRunner(settings, fail=failure))
    result = adapter.run_trial(KNOBS, 3)
    assert_failure(result, kind, tmp_path, 3)
    assert "the cause" in result.detail
    assert "log tail text" in result.detail
    assert "aspect=2.0" in result.detail


def test_a_run_that_does_not_settle_is_a_result_with_five_not_settled_and_the_sheet(settings, tmp_path):
    """Requirements 4.5 and 8.3: a result, not a failure; the picture is the sheet of a settled run."""
    adapter, _ = make(settings, tmp_path, FakeRunner(settings, drift=0.05))
    result = adapter.run_trial(KNOBS, 4)
    assert isinstance(result, TrialResult)
    check_result(adapter.declaration(), result)
    expected = NotMeasured("not_settled", NOT_SETTLED_REASON)
    assert dict(result.values) == dict.fromkeys(("cd", "cl_mean", "cl_amp", "strouhal", "shedding"), expected)
    assert result.picture.kind == "image/png"
    (tmp_path / "settled").mkdir()
    settled_adapter, _ = make(settings, tmp_path / "settled")
    assert (
        result.picture == settled_adapter.run_trial(KNOBS, 4).picture
    )  # the same sheet code and the same flow
    assert not (tmp_path / "cases" / "0000000000000004").exists()
    assert (tmp_path / "cases" / "trash" / "0000000000000004").is_dir()  # a result, so the folder is trashed
    assert adapter.run_trial(KNOBS, 5) == result  # deterministic, the seed is not used


def test_the_not_settled_reason_is_one_fixed_line_without_a_number():
    assert NOT_SETTLED_REASON.isprintable()
    assert not any(ch.isdigit() for ch in NOT_SETTLED_REASON)
    assert "longer" not in NOT_SETTLED_REASON


def test_a_run_that_does_not_settle_and_does_not_shed_is_still_not_settled_for_strouhal(settings, tmp_path):
    adapter, _ = make(settings, tmp_path, FakeRunner(settings, amp=0.005, drift=0.05))
    result = adapter.run_trial(KNOBS, 1)
    assert isinstance(result, TrialResult)
    check_result(adapter.declaration(), result)
    assert result.values["strouhal"] == NotMeasured("not_settled", NOT_SETTLED_REASON)


class Short(FakeRunner):
    """A run whose force history stops early: an incomplete run."""

    def run(self, case_dir, deadline):
        output = super().run(case_dir, deadline)
        lines = output.force_file.read_text().splitlines()
        output.force_file.write_text("\n".join(lines[: len(lines) // 2]) + "\n")
        return output


def test_mesh_error_is_incomplete(settings, tmp_path):
    class Broken:
        def build(self, outline, settings, dest, *, timeout_s=None):
            raise MeshError("no mesh", "the detail")

    adapter, runner = make(settings, tmp_path, mesher=Broken())
    result = adapter.run_trial(KNOBS, 5)
    assert_failure(result, FailureKind.INCOMPLETE, tmp_path, 5)
    assert "no mesh" in result.detail
    assert runner.calls == []


def test_mesh_timeout_is_a_timeout(settings, tmp_path):
    class Slow:
        def build(self, outline, settings, dest, *, timeout_s=None):
            raise MeshTimeout("the mesh was still being built at the time limit", "the detail")

    adapter, runner = make(settings, tmp_path, mesher=Slow())
    result = adapter.run_trial(KNOBS, 5)
    assert_failure(result, FailureKind.TIMEOUT, tmp_path, 5)
    assert runner.calls == []


def test_mesher_gets_the_time_left(settings, tmp_path):
    seen = []

    class Watching(FakeMesher):
        def build(self, outline, settings, dest, *, timeout_s=None):
            seen.append(timeout_s)
            super().build(outline, settings, dest)

    adapter, _ = make(settings, tmp_path, mesher=Watching())
    adapter.run_trial(KNOBS, 5)
    assert 0 < seen[0] <= settings.run.timeout_s


def test_unreadable_output_is_incomplete(settings, tmp_path):
    class Truncated(FakeRunner):
        def run(self, case_dir, deadline):
            output = super().run(case_dir, deadline)
            output.sample_files[0].write_text("1 2 3\n")
            return output

    adapter, _ = make(settings, tmp_path, Truncated(settings))
    assert_failure(adapter.run_trial(KNOBS, 6), FailureKind.INCOMPLETE, tmp_path, 6)


def test_force_history_that_stops_early_is_incomplete(settings, tmp_path):
    adapter, _ = make(settings, tmp_path, Short(settings))
    assert_failure(adapter.run_trial(KNOBS, 8), FailureKind.INCOMPLETE, tmp_path, 8)


def test_failed_run_keeps_only_log_settings_mesh_file_and_force_file(settings, tmp_path):
    class Leaves(Short):
        def run(self, case_dir, deadline):
            for name in ("processor0/0.5/U", "constant/polyMesh/points", "12/U", "solver.log"):
                (case_dir / name).parent.mkdir(parents=True, exist_ok=True)
                (case_dir / name).write_text("x")
            return super().run(case_dir, deadline)

    adapter, _ = make(settings, tmp_path, Leaves(settings))
    result = adapter.run_trial(KNOBS, 10)
    assert_failure(result, FailureKind.INCOMPLETE, tmp_path, 10)
    case = tmp_path / "cases" / "000000000000000a"
    files = {str(p.relative_to(case)) for p in case.rglob("*") if p.is_file()}
    assert "solver.log" in files
    assert "postProcessing/forces/0/force.dat" in files
    assert not (case / "processor0").exists()
    assert not (case / "constant" / "polyMesh").exists()
    assert not (case / "12").exists()
    assert not (case / "postProcessing" / "vorticityFrames").exists()
    for name in files:
        assert name in ("solver.log", "case.msh", "postProcessing/forces/0/force.dat") or name.startswith(
            ("system/", "constant/", "0/")
        )


def test_prune_failure_stops_the_run_loudly(settings, tmp_path, monkeypatch):
    def refuse(path):
        raise PermissionError("cannot prune")

    monkeypatch.setattr(adapter_module, "prune_case_folder", refuse)
    adapter, _ = make(settings, tmp_path, Short(settings))
    with pytest.raises(PermissionError):
        adapter.run_trial(KNOBS, 11)


def test_deadline_is_the_limit_from_the_start(settings, tmp_path):
    adapter, runner = make(settings, tmp_path)
    adapter._clock = lambda: 1000.0
    adapter.run_trial(KNOBS, 9)
    assert runner.calls[0][1] == 1000.0 + settings.run.timeout_s


class SteppedClock:
    """A clock that returns the given times one by one, then stays at the last."""

    def __init__(self, *times):
        self.times = list(times)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.times.pop(0) if len(self.times) > 1 else self.times[0]


def test_deadline_is_checked_after_the_solver_too(settings, tmp_path):
    """The clock reads: start, then (after the solver and everything up to the picture) past the limit."""
    adapter, _ = make(settings, tmp_path)
    adapter._clock = SteppedClock(0.0, settings.run.timeout_s + 0.5)
    result = adapter.run_trial(KNOBS, 12)
    assert_failure(result, FailureKind.TIMEOUT, tmp_path, 12)
    assert "after the solver" in result.detail
    assert not (tmp_path / "cases" / "trash").exists()  # a failed run is pruned and kept, not trashed


def test_a_run_just_inside_the_limit_is_a_result(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    adapter._clock = SteppedClock(0.0, settings.run.timeout_s - 0.001)
    assert isinstance(adapter.run_trial(KNOBS, 13), TrialResult)


def test_a_late_run_that_also_did_not_settle_is_a_timeout(settings, tmp_path):
    adapter, _ = make(settings, tmp_path, FakeRunner(settings, drift=0.05))
    adapter._clock = SteppedClock(0.0, settings.run.timeout_s + 1.0)
    result = adapter.run_trial(KNOBS, 14)
    assert_failure(result, FailureKind.TIMEOUT, tmp_path, 14)
    assert "the part found: a result" in result.detail  # a late result is a time-out, whatever it holds


def test_the_trash_is_deleted_before_the_clock_starts_and_the_next_trial_does_not_see_it(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    assert isinstance(adapter.run_trial(KNOBS, 1), TrialResult)
    trash = tmp_path / "cases" / "trash"
    assert (trash / "0000000000000001").is_dir()
    seen = []

    def clock():
        seen.append(trash.exists())
        return 0.0

    adapter._clock = clock
    assert isinstance(adapter.run_trial(KNOBS, 2), TrialResult)
    assert seen[0] is False  # the first reading of the clock comes after the deletion
    assert not (trash / "0000000000000001").exists()
    assert (trash / "0000000000000002").is_dir()  # at most the last success is in the trash


def test_trash_that_cannot_be_deleted_stops_the_next_trial_loudly(settings, tmp_path, monkeypatch):
    adapter, runner = make(settings, tmp_path)
    assert isinstance(adapter.run_trial(KNOBS, 1), TrialResult)

    def refuse(base):
        raise PermissionError("cannot delete the trash")

    monkeypatch.setattr(adapter_module, "empty_trash", refuse)
    with pytest.raises(PermissionError):
        adapter.run_trial(KNOBS, 2)
    assert len(runner.calls) == 1


@pytest.mark.parametrize(
    "inputs",
    [
        {"aspect": 2.0, "corner": 0.3, "splitter": 0.5},
        {**KNOBS, "extra": 1.0},
        {**KNOBS, "aspect": float("nan")},
        {**KNOBS, "aspect": float("inf")},
        {**KNOBS, "aspect": 0.49},
        {**KNOBS, "corner": 1.01},
        {**KNOBS, "splitter": -0.01},
        {**KNOBS, "angle": 15.5},
        {**KNOBS, "angle": True},
        {**KNOBS, "angle": "10"},
    ],
)
def test_invalid_inputs_are_refused_without_a_case(settings, tmp_path, inputs):
    adapter, runner = make(settings, tmp_path)
    with pytest.raises(ValueError):
        adapter.run_trial(inputs, 1)
    assert runner.calls == []
    assert list((tmp_path / "cases").iterdir()) == []  # the mount probe leaves the base empty


def test_range_ends_are_accepted(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    low = {"aspect": 0.5, "corner": 0.0, "splitter": 0.0, "angle": 0.0}
    high = {"aspect": 3.0, "corner": 1.0, "splitter": 3.0, "angle": 15.0}
    for seed, inputs in enumerate((low, high), start=1):
        assert isinstance(adapter.run_trial(inputs, seed), TrialResult)


def test_an_unexpected_exception_is_not_caught(settings, tmp_path):
    class Boom:
        def run(self, case_dir, deadline):
            raise RuntimeError("programming error")

    adapter, _ = make(settings, tmp_path, Boom())
    with pytest.raises(RuntimeError, match="programming error"):
        adapter.run_trial(KNOBS, 1)


def test_missing_lock_stops_construction(settings, tmp_path):
    with pytest.raises(EnvironmentFailure, match="image lock missing"):
        WindAdapter(
            settings,
            command=fake_docker(settings),
            lock_path=tmp_path / "absent.toml",
            record_path=tmp_path / "environment.jsonl",
        )


@pytest.mark.skipif(environment.LOCK_PATH.exists(), reason="the image lock exists (task 14.1 has run)")
def test_default_construction_fails_while_the_lock_is_absent():
    with pytest.raises(EnvironmentFailure, match="image lock missing"):
        WindAdapter()


def test_constructor_has_no_reynolds_argument():
    import inspect

    names = inspect.signature(WindAdapter.__init__).parameters
    assert not [name for name in names if "reynolds" in name.lower()]


def _identifiers(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        for field in ("id", "attr", "name", "arg", "asname"):
            value = getattr(node, field, None)
            if isinstance(value, str):
                found.add(value)
    return found


def test_reynolds_is_reachable_only_from_the_circle_check():
    adapter_src = Path(adapter_module.__file__).resolve().parent
    model_src = adapter_src.parents[2] / "model" / "src" / "wind_tunnel_model"
    assert model_src.is_dir()
    files = sorted(adapter_src.glob("*.py")) + sorted(model_src.glob("*.py"))
    assert len(files) > 10
    # settings.py defines the parameter and casegen.py reads the value into the viscosity; neither sets it.
    definers = {"settings.py", "casegen.py", "circle_check.py"}
    for path in files:
        names = _identifiers(path)
        if path.name not in definers:
            assert not [n for n in names if "reynolds" in n.lower()], path
        if path.name not in {"settings.py", "circle_check.py"}:
            assert "with_reynolds" not in names, path


# The corner rule (Requirement 6.11; lab-bench Requirement 19).
def test_check_inputs_accepts_and_refuses_by_the_corner_rule(settings, tmp_path):
    from bench.adapter import check_input_refusal, input_refusal

    adapter, _ = make(settings, tmp_path)
    assert input_refusal(adapter, KNOBS) is None
    refused = input_refusal(adapter, {**KNOBS, "aspect": 1.75, "corner": 0.01})
    assert refused == check_input_refusal(refused)
    assert "corner must be 0, 1, or between 0.04 and 0.997 when aspect is 1.75" in refused
    for ends in (0.0, 1.0):
        assert input_refusal(adapter, {**KNOBS, "corner": ends}) is None


def test_check_inputs_ignores_the_plate_and_the_angle(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    for splitter in (0.0, 0.001, 3.0):
        for angle in (0.0, 15.0):
            inputs = {**KNOBS, "splitter": splitter, "angle": angle}
            assert adapter.check_inputs(inputs) is None
            refused = adapter.check_inputs({**inputs, "corner": 0.001})
            assert refused == adapter.check_inputs({**KNOBS, "corner": 0.001})


def test_a_refused_corner_that_reaches_run_trial_fails_loudly(settings, tmp_path):
    from wind_tunnel_model.input_rule import InputRuleError

    adapter, runner = make(settings, tmp_path)
    with pytest.raises(InputRuleError, match="corner must be"):
        adapter.run_trial({**KNOBS, "corner": 0.999}, 1)
    assert runner.calls == []
    assert list((tmp_path / "cases").iterdir()) == []  # the mount probe leaves the base empty


# The splitter floor (Requirement 6.11, Decision 45).
@pytest.mark.parametrize("splitter", [0.0, 1e-6, 2e-6, 3.0])
def test_check_inputs_accepts_zero_the_floor_and_larger_splitters(settings, tmp_path, splitter):
    adapter, _ = make(settings, tmp_path)
    assert adapter.check_inputs({**KNOBS, "splitter": splitter}) is None


@pytest.mark.parametrize("splitter", [1e-9, 1e-8, 9.99e-7])
def test_check_inputs_refuses_a_positive_splitter_below_the_floor(settings, tmp_path, splitter):
    adapter, _ = make(settings, tmp_path)
    refused = adapter.check_inputs({**KNOBS, "splitter": splitter})
    assert refused == f"splitter {splitter:.12g} is not accepted: splitter must be 0 or at least 1e-06"


def test_a_refused_splitter_that_reaches_run_trial_fails_loudly(settings, tmp_path):
    from wind_tunnel_model.input_rule import InputRuleError

    adapter, runner = make(settings, tmp_path)
    with pytest.raises(InputRuleError, match="splitter must be 0 or at least"):
        adapter.run_trial({**KNOBS, "splitter": 1e-9}, 1)
    assert runner.calls == []


def test_two_refused_knobs_are_both_named(settings, tmp_path):
    adapter, _ = make(settings, tmp_path)
    refused = adapter.check_inputs({**KNOBS, "aspect": 1.75, "corner": 0.01, "splitter": 1e-9})
    assert refused.startswith("corner 0.01 is not accepted")
    assert "; splitter 1e-09 is not accepted" in refused
