"""Test-side helpers for the adapter pipeline: a FakeRunner that writes synthetic solver output, a fake
Docker command function, and small settings. Nothing here needs Docker or Gmsh."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
from wind_tunnel_model.estimators import dynamic_pressure
from wind_tunnel_model.settings import Settings, frame_times
from wind_tunnel_model.solver_output import picture_grid

from wind_tunnel.environment import CommandResult
from wind_tunnel.runner import FORCE_GLOB, SAMPLE_GLOB, RunOutput, SolverFailure

DIGEST = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def small_settings() -> Settings:
    """The settings with a small picture grid so that the sample files stay short."""
    settings = Settings.load()
    picture = dataclasses.replace(settings.picture, cell_width=8, cell_height=4, gap=1)
    return dataclasses.replace(settings, picture=picture)


def write_lock(directory: Path) -> Path:
    path = directory / "image-lock.toml"
    path.write_text(f'digest = "{DIGEST}"\nimage_id = "{IMAGE_ID}"\n')
    return path


def fake_docker(settings: Settings):
    name = settings.image.name

    def command(args):
        if args[:2] == ["docker", "version"]:
            return CommandResult(0, "27.0\n", "")
        if args[:3] == ["docker", "image", "inspect"]:
            return CommandResult(0, f"{json.dumps([f'{name}@{DIGEST}'])} {IMAGE_ID}\n", "")
        if args[:2] == ["docker", "info"]:
            return CommandResult(0, "4\n", "")
        raise AssertionError(f"unexpected command {args}")

    return command


class FakeRunner:
    """Writes force and vorticity files from a known sinusoid.

    The drag coefficient is `cd`; the lift coefficient is cl_mean + amp * sin(2 pi st t).

    `fail` raises a SolverFailure instead; `drift` adds a slope to the drag so that the run does not settle.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        cd: float = 1.2,
        cl_mean: float = 0.05,
        amp: float = 0.4,
        st: float = 0.17,
        dt: float = 0.02,
        drift: float = 0.0,
        fail: SolverFailure | None = None,
    ) -> None:
        self.settings = settings
        self.cd, self.cl_mean, self.amp, self.st, self.dt, self.drift, self.fail = (
            cd,
            cl_mean,
            amp,
            st,
            dt,
            drift,
            fail,
        )
        self.calls: list[tuple[Path, float]] = []

    def run(self, case_dir: Path, deadline: float) -> RunOutput:
        self.calls.append((case_dir, deadline))
        if self.fail is not None:
            raise self.fail
        settings = self.settings
        q = dynamic_pressure(settings.flow)
        count = int(round(settings.time.end / self.dt))
        t = self.dt * np.arange(1, count + 1)
        cd = self.cd + self.drift * (t - settings.time.average_from)
        cl = self.cl_mean + self.amp * np.sin(2 * np.pi * self.st * t)
        lines = [
            "# Force",
            "# Time total_x total_y total_z pressure_x pressure_y pressure_z viscous_x viscous_y viscous_z",
        ]
        for ti, xi, yi in zip(t, cd * q, cl * q, strict=True):
            lines.append(f"{float(ti)!r} {float(xi)!r} {float(yi)!r} 0 0 0 0 0 0 0")
        force = case_dir / "postProcessing" / "forces" / "0" / "force.dat"
        force.parent.mkdir(parents=True)
        force.write_text("\n".join(lines) + "\n", encoding="utf-8")
        xs, ys = picture_grid(settings.picture)
        for k, when in enumerate(frame_times(settings)):
            folder = case_dir / "postProcessing" / "vorticityFrames" / f"{when:g}"
            folder.mkdir(parents=True)
            rows = [
                f"{float(x)!r} {float(y)!r} 0 0 0 {float(np.sin(0.5 * (i + j) + k))!r}"
                for j, y in enumerate(ys)
                for i, x in enumerate(xs)
                if (i, j) != (0, 0)  # one point is never returned: the mask
            ]
            (folder / "grid_vorticity.xy").write_text("\n".join(rows) + "\n", encoding="utf-8")
        return RunOutput(
            force_file=next(case_dir.glob(FORCE_GLOB)),
            sample_files=tuple(sorted(case_dir.glob(SAMPLE_GLOB), key=lambda p: float(p.parent.name))),
        )
