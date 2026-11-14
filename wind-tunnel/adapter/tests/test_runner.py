"""wind-tunnel task 10.2: the runner and the case folder (Requirements 8.1, 8.2, 8.7, 8.8, 10.5, 10.6)."""

import subprocess

import pytest

from wind_tunnel.failures import FailureKind
from wind_tunnel.runner import (
    DockerRunner,
    SolverFailure,
    case_folder_name,
    create_case_folder,
    prune_case_folder,
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

    process = FakeProcess(ok)
    runner = DockerRunner(IMAGE, process=process, clock=lambda: 0.0, user=501, group=20)
    output = runner.run(tmp_path, 140.0)
    args, kwargs = process.calls[0]
    assert args == [
        "docker", "run", "--rm", "--name", f"wind-tunnel-{tmp_path.name}", "--user", "501:20",
        "-v", f"{tmp_path}:/case", IMAGE, "/case/Allrun",
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


def write(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def fake_failed_case(root):
    """A case folder as a failed run leaves it: what is kept, and what is not."""
    kept = [
        root / "solver.log",
        root / "case.msh",
        root / "system" / "controlDict",
        root / "system" / "fvSchemes",
        root / "constant" / "transportProperties",
        root / "0" / "U",
        root / "0" / "p",
        root / "postProcessing" / "forces" / "0" / "force.dat",
    ]
    removed = [
        root / "processor0" / "0.5" / "U",
        root / "processor1" / "constant" / "polyMesh" / "points",
        root / "constant" / "polyMesh" / "points",
        root / "constant" / "polyMesh" / "boundary",
        root / "postProcessing" / "vorticityFrames" / "145" / "grid_vorticity.xy",
        root / "postProcessing" / "forces" / "0" / "other.dat",
        root / "postProcessing" / "probes" / "0" / "p",
        root / "12" / "U",
        root / "stray.txt",
        root / "system" / "nested" / "extra",
    ]
    for path in kept + removed:
        write(path)
    return kept, removed


def test_prune_keeps_only_log_settings_mesh_file_and_force_file(tmp_path):
    root = create_case_folder(tmp_path, 2)
    kept, removed = fake_failed_case(root)
    prune_case_folder(root)
    assert sorted(p for p in root.rglob("*") if p.is_file()) == sorted(kept)
    assert all(not path.exists() for path in removed)
    assert not (root / "constant" / "polyMesh").exists()
    assert not (root / "processor0").exists()


def test_prune_twice_changes_nothing(tmp_path):
    root = create_case_folder(tmp_path, 2)
    kept, _ = fake_failed_case(root)
    prune_case_folder(root)
    prune_case_folder(root)
    assert sorted(p for p in root.rglob("*") if p.is_file()) == sorted(kept)


def test_prune_of_a_missing_folder_is_loud(tmp_path):
    with pytest.raises(NotADirectoryError):
        prune_case_folder(tmp_path / "absent")


def test_prune_failure_is_loud(tmp_path, monkeypatch):
    root = create_case_folder(tmp_path, 2)
    fake_failed_case(root)

    def refuse(path, *args, **kwargs):
        raise PermissionError(f"cannot remove {path}")

    monkeypatch.setattr("wind_tunnel.runner.shutil.rmtree", refuse)
    with pytest.raises(PermissionError):
        prune_case_folder(root)


@pytest.mark.parametrize("seed", [-1, 2**64, 1.5, True])
def test_bad_seed_is_refused(seed):
    with pytest.raises(ValueError):
        case_folder_name(seed)
