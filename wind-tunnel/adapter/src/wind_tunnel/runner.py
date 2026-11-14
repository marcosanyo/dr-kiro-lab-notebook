"""The solver runner and the case folder (wind-tunnel Requirements 7.2, 8.1, 8.2, 8.7, 8.8, 10.5, 10.6).

`DockerRunner` runs the case in the pinned image with one `docker run`, inside the time that is left of
the 140 s limit. A timeout, an abnormal exit or a missing output raises `SolverFailure`. Nothing is
retried, repaired or filled in (8.2). Everything here is builder side: the detail of a failure never
reaches Dr. Kiro.

The in-image invocation and the output file locations were confirmed in task 14.1 (design 6, S5).
"""

import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from wind_tunnel.failures import FailureKind

LOG_NAME = "solver.log"
LOG_TAIL_LINES = 40
FORCE_GLOB = "postProcessing/forces/*/force.dat"
SAMPLE_GLOB = "postProcessing/vorticityFrames/*/*.xy"
SEED_LIMIT = 1 << 64


class SolverFailure(Exception):
    """A run that did not give usable output. `reason` is the builder-side cause."""

    def __init__(self, kind: FailureKind, reason: str, detail: str):
        super().__init__(f"{kind.value}: {reason}")
        self.kind = kind
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class RunOutput:
    force_file: Path
    sample_files: tuple[Path, ...]


class Runner(Protocol):
    def run(self, case_dir: Path, deadline: float) -> RunOutput:
        """Run the case in `case_dir`. `deadline` is a time on the runner's clock (monotonic seconds)."""
        ...


ProcessFunction = Callable[..., subprocess.CompletedProcess]


def case_folder_name(seed: int) -> str:
    """The seed as 16 hex digits. It is only a label (Decision 3)."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < SEED_LIMIT:
        raise ValueError(f"the seed must be an integer from 0 to 2**64 - 1, got {seed!r}")
    return f"{seed:016x}"


def create_case_folder(base: Path | str, seed: int) -> Path:
    """Make `<base>/<seed as 16 hex digits>/`. An existing folder is an error, never overwritten."""
    base = Path(base)
    path = base / case_folder_name(seed)
    base.mkdir(parents=True, exist_ok=True)
    path.mkdir(exist_ok=False)
    return path


def remove_case_folder(path: Path | str) -> None:
    """Remove the case folder of a run that succeeded (10.6). A failed run keeps its folder."""
    shutil.rmtree(path)


def _tail(text: str) -> str:
    return "\n".join(text.splitlines()[-LOG_TAIL_LINES:])


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


class DockerRunner:
    """Runs `/case/Allrun` of a case folder in the image `image` (`name@digest`), as the user of this process.

    The entry point of the image starts every command in the home directory, whatever `-w` says, so the
    command is an absolute path and `Allrun` changes into `/case` itself. The solver runs as the calling user
    because `mpirun` refuses to run as root and the image prepares a user name for any other user id.
    """

    def __init__(
        self,
        image: str,
        *,
        process: ProcessFunction = subprocess.run,
        clock: Callable[[], float] = time.monotonic,
        user: int | None = None,
        group: int | None = None,
    ):
        if "@sha256:" not in image:
            raise ValueError(f"the image must be given as name@digest, got {image!r}")
        self._image = image
        self._process = process
        self._clock = clock
        self._user = os.getuid() if user is None else user
        self._group = os.getgid() if group is None else group

    def container_name(self, case_dir: Path) -> str:
        return f"wind-tunnel-{case_dir.name}"

    def command(self, case_dir: Path) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            self.container_name(case_dir),
            "--user",
            f"{self._user}:{self._group}",
            "-v",
            f"{case_dir}:/case",
            self._image,
            "/case/Allrun",
        ]

    def run(self, case_dir: Path, deadline: float) -> RunOutput:
        case_dir = Path(case_dir)
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise SolverFailure(
                FailureKind.TIMEOUT,
                "the time limit was used up before the solver started",
                f"remaining seconds: {remaining!r}",
            )
        try:
            done = self._process(
                self.command(case_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=remaining,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            log = _as_text(expired.output)
            self._write_log(case_dir, log)
            kill = self._process(
                ["docker", "kill", self.container_name(case_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            raise SolverFailure(
                FailureKind.TIMEOUT,
                "the solver was still running at the time limit",
                f"docker kill exit code: {kill.returncode}\n"
                f"docker kill output: {_as_text(kill.stdout).strip()}\n"
                f"solver log tail:\n{_tail(log)}",
            ) from expired
        log = _as_text(done.stdout)
        self._write_log(case_dir, log)
        if done.returncode != 0:
            raise SolverFailure(
                FailureKind.INCOMPLETE,
                f"the solver run exited with code {done.returncode}",
                f"solver log tail:\n{_tail(log)}",
            )
        return self._collect(case_dir, log)

    @staticmethod
    def _write_log(case_dir: Path, log: str) -> None:
        (case_dir / LOG_NAME).write_text(log, encoding="utf-8")

    @staticmethod
    def _collect(case_dir: Path, log: str) -> RunOutput:
        forces = sorted(case_dir.glob(FORCE_GLOB))
        if len(forces) != 1:
            raise SolverFailure(
                FailureKind.INCOMPLETE,
                f"expected exactly one force file, found {len(forces)}",
                f"pattern: {FORCE_GLOB}\nsolver log tail:\n{_tail(log)}",
            )
        samples = sorted(case_dir.glob(SAMPLE_GLOB), key=_sample_order)
        if not samples:
            raise SolverFailure(
                FailureKind.INCOMPLETE,
                "no sampled vorticity file was written",
                f"pattern: {SAMPLE_GLOB}\nsolver log tail:\n{_tail(log)}",
            )
        return RunOutput(force_file=forces[0], sample_files=tuple(samples))


def _sample_order(path: Path) -> tuple[float, str]:
    """Time order of the sample files: the folder name is the write time."""
    try:
        return (float(path.parent.name), path.name)
    except ValueError as error:
        raise SolverFailure(
            FailureKind.INCOMPLETE,
            f"a sample folder name is not a time: {path.parent.name!r}",
            f"file: {path}",
        ) from error
