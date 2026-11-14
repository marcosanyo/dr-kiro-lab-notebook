"""wind-tunnel task 10.2: the runner and the case folder (Requirements 8.1, 8.2, 8.7, 8.8, 10.5, 10.6)."""

import subprocess

import pytest

from wind_tunnel.failures import FailureKind
from wind_tunnel.runner import (
    DockerRunner,
    SolverFailure,
    case_folder_name,
    create_case_folder,
    remove_case_folder,
)

IMAGE = "example/image@sha256:" + "0" * 64


class FakeProcess:
    """Stands in for subprocess.run. Records every call; `behaviour` decides what a `docker run` does."""

    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((list(args), kwargs))
        if args[1] == "kill":
            return subprocess.CompletedProcess(args, 0, stdout="killed\n")
        return self.behaviour(args, kwargs)


def write_outputs(case_dir):
    forces = case_dir / "postProcessing" / "forces" / "0"
    forces.mkdir(parents=True)
    (forces / "force.dat").write_text("# fake\n")
    for time in ("10", "9", "100"):
        folder = case_dir / "postProcessing" / "vorticityFrames" / time
        folder.mkdir(parents=True)
        (folder / "grid_vorticity.xy").write_text("")


def runner_with(behaviour, now=0.0):
    process = FakeProcess(behaviour)
    return DockerRunner(IMAGE, process=process, clock=lambda: now), process


def test_command_line(tmp_path):
    def ok(args, kwargs):
        write_outputs(tmp_path)
        return subprocess.CompletedProcess(args, 0, stdout="done\n")

    runner, process = runner_with(ok)
    output = runner.run(tmp_path, 140.0)
    args, kwargs = process.calls[0]
    assert args == [
        "docker", "run", "--rm", "--name", f"wind-tunnel-{tmp_path.name}",
        "-v", f"{tmp_path}:/case", "-w", "/case", IMAGE, "./Allrun",
    ]  # fmt: skip
    assert kwargs["timeout"] == 140.0
    assert output.force_file.name == "force.dat"
    assert [p.parent.name for p in output.sample_files] == ["9", "10", "100"]
    assert (tmp_path / "solver.log").read_text() == "done\n"


def test_remaining_time_comes_from_the_deadline(tmp_path):
    def ok(args, kwargs):
        write_outputs(tmp_path)
        return subprocess.CompletedProcess(args, 0, stdout="")

    process = FakeProcess(ok)
    DockerRunner(IMAGE, process=process, clock=lambda: 30.0).run(tmp_path, 140.0)
    assert process.calls[0][1]["timeout"] == 110.0


def test_timeout_kills_the_container_and_raises_timeout(tmp_path):
    def slow(args, kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"], output="step 1\nstep 2\n")

    runner, process = runner_with(slow)
    with pytest.raises(SolverFailure) as raised:
        runner.run(tmp_path, 5.0)
    assert raised.value.kind is FailureKind.TIMEOUT
    assert process.calls[1][0] == ["docker", "kill", f"wind-tunnel-{tmp_path.name}"]
    assert "step 2" in raised.value.detail


def test_deadline_already_passed_is_a_timeout_without_running(tmp_path):
    runner, process = runner_with(lambda a, k: pytest.fail("must not run"), now=10.0)
    with pytest.raises(SolverFailure) as raised:
        runner.run(tmp_path, 10.0)
    assert raised.value.kind is FailureKind.TIMEOUT
    assert process.calls == []


def test_non_zero_exit_raises_with_the_log_tail(tmp_path):
    log = "\n".join(f"line {i}" for i in range(100))
    runner, _ = runner_with(lambda a, k: subprocess.CompletedProcess(a, 3, stdout=log))
    with pytest.raises(SolverFailure) as raised:
        runner.run(tmp_path, 140.0)
    assert raised.value.kind is FailureKind.INCOMPLETE
    assert "code 3" in raised.value.reason
    assert "line 99" in raised.value.detail
    assert "line 0\n" not in raised.value.detail


def test_missing_output_raises(tmp_path):
    runner, _ = runner_with(lambda a, k: subprocess.CompletedProcess(a, 0, stdout="ok"))
    with pytest.raises(SolverFailure) as raised:
        runner.run(tmp_path, 140.0)
    assert raised.value.kind is FailureKind.INCOMPLETE
    assert "force file" in raised.value.reason


def test_image_must_carry_a_digest():
    with pytest.raises(ValueError):
        DockerRunner("example/image:2412")


def test_case_folder_is_named_by_the_seed_and_never_overwritten(tmp_path):
    base = tmp_path / "bench-run" / "wind-tunnel"
    folder = create_case_folder(base, 255)
    assert folder.name == "00000000000000ff"
    with pytest.raises(FileExistsError):
        create_case_folder(base, 255)


def test_case_folder_removed_on_success(tmp_path):
    folder = create_case_folder(tmp_path, 1)
    (folder / "a.txt").write_text("x")
    remove_case_folder(folder)
    assert not folder.exists()


@pytest.mark.parametrize("seed", [-1, 2**64, 1.5, True])
def test_bad_seed_is_refused(seed):
    with pytest.raises(ValueError):
        case_folder_name(seed)
