"""The solver environment check (wind-tunnel Requirement 7; design 6).

``check`` runs when the adapter is created. It looks at Docker, at the image recorded in
``image-lock.toml`` and at the CPUs of the Docker machine, and raises ``EnvironmentFailure`` on the first
thing that is wrong, naming which it is, what was expected and what was found. It never pulls an image and
never looks at another tag. A passing check appends one line to the builder-side record, which holds no time
and is not part of the sealed session record.

Docker is reached only through ``CommandFunction``, so a test needs no Docker.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path

from wind_tunnel_model.settings import SETTINGS_PATH, Settings

LOCK_PATH = SETTINGS_PATH.parent / "image-lock.toml"
RECORD_PATH = Path(__file__).resolve().parents[4] / "bench-run" / "wind-tunnel" / "environment.jsonl"

DOCKER_TIMEOUT_S = 60.0

DOCKER_NOT_REACHABLE = "Docker not reachable"
IMAGE_MISSING = "image missing"
DIGEST_DIFFERENT = "digest different"
TOO_FEW_CPUS = "too few CPUs"
IMAGE_LOCK_MISSING = "image lock missing"

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class EnvironmentFailure(Exception):
    """The environment is not the recorded one. The message names which check failed."""

    def __init__(self, which: str, expected: str, found: str):
        self.which = which
        self.expected = expected
        self.found = found
        super().__init__(f"{which}: expected {expected}; found {found}")


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandFunction = Callable[[Sequence[str]], CommandResult]


@dataclass(frozen=True)
class ImageLock:
    digest: str
    image_id: str


def run_command(args: Sequence[str]) -> CommandResult:
    """The real command function: run ``args`` and capture the text output."""
    try:
        done = subprocess.run(
            list(args), capture_output=True, text=True, check=False, timeout=DOCKER_TIMEOUT_S
        )
    except FileNotFoundError as error:
        return CommandResult(127, "", f"command not found: {error.filename}")
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"no answer within {DOCKER_TIMEOUT_S:g} s")
    return CommandResult(done.returncode, done.stdout, done.stderr)


def load_lock(path: Path | str | None = None) -> ImageLock:
    """Read the image lock written by task 14.1. A missing or malformed file is an error."""
    target = Path(path) if path is not None else LOCK_PATH
    if not target.is_file():
        raise EnvironmentFailure(
            IMAGE_LOCK_MISSING,
            "model/image-lock.toml, written by task 14.1 of the wind-tunnel spec",
            f"no file at {target}",
        )
    with open(target, "rb") as handle:
        data = tomllib.load(handle)
    if set(data) != {"digest", "image_id"}:
        raise EnvironmentFailure(
            IMAGE_LOCK_MISSING, "exactly the keys digest and image_id", f"keys {sorted(data)}"
        )
    digest, image_id = data["digest"], data["image_id"]
    if not isinstance(digest, str) or not _DIGEST.match(digest):
        raise EnvironmentFailure(IMAGE_LOCK_MISSING, "digest as sha256:<64 hex digits>", f"{digest!r}")
    if not isinstance(image_id, str) or not _DIGEST.match(image_id):
        raise EnvironmentFailure(IMAGE_LOCK_MISSING, "image_id as sha256:<64 hex digits>", f"{image_id!r}")
    return ImageLock(digest=digest, image_id=image_id)


def check(
    settings: Settings,
    *,
    command: CommandFunction = run_command,
    lock_path: Path | str | None = None,
    record_path: Path | str | None = None,
) -> dict[str, str]:
    """Check Docker, the image and the CPUs; append the environment line; return it."""
    lock = load_lock(lock_path)
    name, tag = settings.image.name, settings.image.tag
    reference = f"{name}:{tag}"

    version = command(["docker", "version", "--format", "{{.Server.Version}}"])
    if version.returncode != 0:
        raise EnvironmentFailure(
            DOCKER_NOT_REACHABLE,
            "a Docker server that answers `docker version`",
            _tail(version),
        )

    inspect = command(["docker", "image", "inspect", "--format", "{{json .RepoDigests}} {{.Id}}", reference])
    if inspect.returncode != 0:
        raise EnvironmentFailure(
            IMAGE_MISSING, f"image {reference} present locally (not pulled)", _tail(inspect)
        )
    found_digests, found_id = _parse_inspect(inspect.stdout, reference)
    expected_digest = f"{name}@{lock.digest}"
    if expected_digest not in found_digests:
        raise EnvironmentFailure(
            DIGEST_DIFFERENT,
            f"digest {lock.digest} for {reference}",
            f"digests {[d.split('@', 1)[-1] for d in found_digests]}",
        )
    if found_id != lock.image_id:
        raise EnvironmentFailure(DIGEST_DIFFERENT, f"image id {lock.image_id}", f"image id {found_id}")

    info = command(["docker", "info", "--format", "{{.NCPU}}"])
    if info.returncode != 0:
        raise EnvironmentFailure(
            DOCKER_NOT_REACHABLE, "a Docker server that answers `docker info`", _tail(info)
        )
    cpus = _parse_cpus(info.stdout)
    needed = settings.run.processes
    if cpus < needed:
        raise EnvironmentFailure(TOO_FEW_CPUS, f"at least {needed} CPUs in Docker", f"{cpus} CPUs")

    line = {
        "image": reference,
        "digest": lock.digest,
        "image_id": lock.image_id,
        "gmsh": metadata.version("gmsh"),
        "numpy": metadata.version("numpy"),
        "platform": f"{sys.platform}-{platform.machine()}",
    }
    target = Path(record_path) if record_path is not None else RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")
    return line


def _tail(result: CommandResult) -> str:
    text = (result.stderr or result.stdout).strip()
    lines = text.splitlines()[-3:]
    return f"exit {result.returncode}: " + (" / ".join(lines) if lines else "no output")


def _parse_inspect(output: str, reference: str) -> tuple[list[str], str]:
    head, _, image_id = output.strip().rpartition(" ")
    try:
        digests = json.loads(head)
    except json.JSONDecodeError as error:
        raise EnvironmentFailure(
            IMAGE_MISSING, f"readable digests of {reference}", f"unreadable answer: {output.strip()!r}"
        ) from error
    if not isinstance(digests, list) or not all(isinstance(d, str) for d in digests):
        raise EnvironmentFailure(IMAGE_MISSING, f"a list of digests for {reference}", f"{output.strip()!r}")
    return digests, image_id


def _parse_cpus(output: str) -> int:
    text = output.strip()
    if not text.isdigit():
        raise EnvironmentFailure(DOCKER_NOT_REACHABLE, "a number of CPUs from `docker info`", f"{text!r}")
    return int(text)
