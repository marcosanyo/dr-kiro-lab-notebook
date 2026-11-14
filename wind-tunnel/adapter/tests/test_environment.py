"""Unit tests for the environment check (wind-tunnel Requirement 7). No Docker is used."""

import json

import pytest
from wind_tunnel_model.settings import Settings

from wind_tunnel import declaration, environment
from wind_tunnel.environment import CommandResult, EnvironmentFailure

DIGEST = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64
OTHER = "sha256:" + "c" * 64


@pytest.fixture
def settings():
    return Settings.load()


@pytest.fixture
def lock(tmp_path):
    path = tmp_path / "image-lock.toml"
    path.write_text(f'digest = "{DIGEST}"\nimage_id = "{IMAGE_ID}"\n')
    return path


def fake_docker(
    *, version=0, inspect=0, digests=None, image_id=IMAGE_ID, cpus="4", name="opencfd/openfoam-default"
):
    digests = [f"{name}@{DIGEST}"] if digests is None else digests
    calls = []

    def command(args):
        calls.append(list(args))
        if args[:2] == ["docker", "version"]:
            return CommandResult(
                version, "27.0\n", "" if version == 0 else "Cannot connect to the Docker daemon"
            )
        if args[:3] == ["docker", "image", "inspect"]:
            if inspect:
                return CommandResult(inspect, "", "Error: No such image")
            return CommandResult(0, f"{json.dumps(digests)} {image_id}\n", "")
        if args[:2] == ["docker", "info"]:
            return CommandResult(0, f"{cpus}\n", "")
        raise AssertionError(f"unexpected command {args}")

    command.calls = calls
    return command


def run_check(settings, lock, tmp_path, command):
    record = tmp_path / "out" / "environment.jsonl"
    return environment.check(settings, command=command, lock_path=lock, record_path=record), record


def test_passing_check_writes_one_line_without_time(settings, lock, tmp_path):
    line, record = run_check(settings, lock, tmp_path, fake_docker())
    lines = record.read_text().splitlines()
    assert len(lines) == 1
    written = json.loads(lines[0])
    assert written == line
    assert set(written) == {"image", "digest", "image_id", "gmsh", "numpy", "platform"}
    assert written["image"] == "opencfd/openfoam-default:2412"
    assert written["digest"] == DIGEST


def test_two_checks_give_two_identical_lines(settings, lock, tmp_path):
    record = tmp_path / "environment.jsonl"
    for _ in range(2):
        environment.check(settings, command=fake_docker(), lock_path=lock, record_path=record)
    first, second = record.read_text().splitlines()
    assert first == second


def test_no_pull_and_only_the_recorded_tag(settings, lock, tmp_path):
    command = fake_docker()
    run_check(settings, lock, tmp_path, command)
    assert all(call[1] != "pull" for call in command.calls)
    inspected = [call[-1] for call in command.calls if call[:3] == ["docker", "image", "inspect"]]
    assert inspected == ["opencfd/openfoam-default:2412"]


def test_docker_not_reachable(settings, lock, tmp_path):
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, lock, tmp_path, fake_docker(version=1))
    assert error.value.which == environment.DOCKER_NOT_REACHABLE
    assert "Cannot connect" in error.value.found
    assert not (tmp_path / "out").exists()


def test_image_missing(settings, lock, tmp_path):
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, lock, tmp_path, fake_docker(inspect=1))
    assert error.value.which == environment.IMAGE_MISSING
    assert "opencfd/openfoam-default:2412" in error.value.expected


def test_digest_different(settings, lock, tmp_path):
    command = fake_docker(digests=[f"opencfd/openfoam-default@{OTHER}"])
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, lock, tmp_path, command)
    assert error.value.which == environment.DIGEST_DIFFERENT
    assert DIGEST in error.value.expected
    assert OTHER in error.value.found


def test_image_id_different(settings, lock, tmp_path):
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, lock, tmp_path, fake_docker(image_id=OTHER))
    assert error.value.which == environment.DIGEST_DIFFERENT
    assert OTHER in error.value.found


def test_too_few_cpus(settings, lock, tmp_path):
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, lock, tmp_path, fake_docker(cpus="2"))
    assert error.value.which == environment.TOO_FEW_CPUS
    assert error.value.expected == "at least 3 CPUs in Docker"
    assert error.value.found == "2 CPUs"


def test_exactly_three_cpus_pass(settings, lock, tmp_path):
    run_check(settings, lock, tmp_path, fake_docker(cpus="3"))


def test_missing_lock_names_the_task(settings, tmp_path):
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, tmp_path / "absent.toml", tmp_path, fake_docker())
    assert error.value.which == environment.IMAGE_LOCK_MISSING
    assert "14.1" in error.value.expected


def test_placeholder_in_lock_is_refused(settings, tmp_path):
    path = tmp_path / "image-lock.toml"
    path.write_text(f'digest = "<not yet recorded>"\nimage_id = "{IMAGE_ID}"\n')
    with pytest.raises(EnvironmentFailure) as error:
        run_check(settings, path, tmp_path, fake_docker())
    assert error.value.which == environment.IMAGE_LOCK_MISSING


def test_sealed_record_text_holds_none_of_it(settings):
    told = [declaration.MEASURED_BY, declaration.GOAL, *declaration.knob_texts(settings).values()]
    for text in told:
        lowered = text.lower()
        for word in ("sha256", "docker", "gmsh", "openfoam", "numpy"):
            assert word not in lowered
