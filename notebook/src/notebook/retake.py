"""Retake the pictures of body-lab trials for display (notebook-shelf design 8). Run by the builder on a Mac
with MuJoCo; it is never part of the site build.
For every trial of the chosen sessions it reads the sealed record (read-only), runs the trial again through
the body-lab adapter's own simulator with the recorded inputs, and compares what the rerun measured with what
the record holds: x, y, heading and the three tracks, exactly. The first difference stops the run and says
where (`rules.md` 2); nothing is retried, adjusted or skipped. Only then is the sheet kept: a camera straight
above that follows the body, showing the floor around it, one cell every `FRAME_SECONDS` seconds, each `CELL`
pixels square, laid out as one PNG sheet with no gap. The sheets and a `manifest.toml` go to the display
folder.
The adapter, the bench and the sealed records are not changed: the following camera is a free camera of the
renderer, the simulation is `sim.run` with the recorded commands, and the measurer is the adapter's own.
"""

import argparse
import hashlib
import math
import struct
import sys
import zlib
from pathlib import Path

import mujoco
import numpy as np
from body_lab.adapter import BodyAdapter
from body_lab.sim import run as sim_run

from notebook import numbers, png, records
from notebook.errors import NotebookError

PROG = "notebook-retake"
APPLICATION = "body-lab"
FRAME_SECONDS = 0.2
FRAMES = 25
COLUMNS = 5
ROWS = 5
CELL = 320
SIGHT_M = 0.25  # the floor shown on each side of the body: 50 cm across, the body is about a quarter of it
TRACK = "track_x"
TRACK_STEP = 2  # track samples (0.1 s apart) per frame (0.2 s)
INTERVAL_MS = 200
DROP_BITS = 3  # the low bits of each colour are dropped: the sheets are display pictures and stay small


def _same(name: str, recorded: object, rerun: object, where: str) -> None:
    """Fail unless the rerun's value `name` equals the recorded one exactly."""
    if isinstance(recorded, records.NotMeasuredValue) or not isinstance(rerun, int | float | tuple):
        ok = isinstance(recorded, records.NotMeasuredValue) and hasattr(rerun, "outcome")
        ok = ok and recorded.outcome == rerun.outcome
        if not ok:
            raise NotebookError(where, f"{name}: the rerun gave {rerun!r}, the record holds {recorded!r}")
        return
    if isinstance(recorded, tuple):
        same = (
            isinstance(rerun, tuple)
            and len(recorded) == len(rerun)
            and all(a == b for a, b in zip(recorded, rerun, strict=True))
        )
    else:
        same = recorded == rerun
    if not same:
        raise NotebookError(
            where, f"{name}: the rerun gave {_brief(rerun)}, the record holds {_brief(recorded)}"
        )


def _brief(value: object) -> str:
    if isinstance(value, tuple):
        return f"a series of {len(value)} values starting {value[:3]}"
    return repr(value)


def verify(record: records.RecordModel, trial: records.Trial, measured: dict[str, object]) -> None:
    """Every measurement of the trial, by name, is what the record holds."""
    where = f"{record.name} {trial.id}"
    recorded = dict(trial.measurements)
    if set(recorded) != set(measured):
        raise NotebookError(
            where, f"the rerun measured {sorted(measured)}, the record holds {sorted(recorded)}"
        )
    for name in recorded:
        _same(name, recorded[name], measured[name], where)


def camera() -> mujoco.MjvCamera:
    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.elevation = -90.0
    cam.azimuth = 90.0
    return cam


def distance_for(fovy_deg: float) -> float:
    """How high the camera is so that the floor shown has half the width `SIGHT_M` on each side."""
    return SIGHT_M / math.tan(math.radians(fovy_deg) / 2)


def encode(image: np.ndarray) -> bytes:
    """A PNG of an RGB array. Each row is stored with the filter (none, sub or up) that makes it smallest, so
    the smooth floor compresses well; the pixels are exactly the rendered ones. Every reader supports it."""
    height, width, _ = image.shape
    rows = image.reshape(height, width * 3).astype(np.int16)
    out = bytearray()
    previous = np.zeros(width * 3, dtype=np.int16)
    for row in rows:
        sub = row.copy()
        sub[3:] -= row[:-3]
        candidates = ((0, row), (1, sub), (2, row - previous))
        kind, best = min(candidates, key=lambda c: int(np.abs(((c[1] + 128) % 256) - 128).sum()))
        out += bytes([kind]) + (best % 256).astype(np.uint8).tobytes()
        previous = row
    return (
        png.SIGNATURE
        + png.chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png.chunk(b"IDAT", zlib.compress(bytes(out), 9))
        + png.chunk(b"IEND", b"")
    )


class Reel:
    """Draws one frame per call: a camera straight above, centred on the body."""

    def __init__(self, adapter: BodyAdapter) -> None:
        body = adapter.body
        self.body = body
        self.renderer = mujoco.Renderer(body.model, CELL, CELL)
        self.cam = camera()
        self.cam.distance = distance_for(float(body.model.vis.global_.fovy))
        self.frames: list[np.ndarray] = []

    def __call__(self, data: mujoco.MjData) -> None:
        self.cam.lookat[:] = data.subtree_com[self.body.root]
        self.renderer.update_scene(data, camera=self.cam)
        self.frames.append(self.renderer.render().copy())

    def close(self) -> None:
        self.renderer.close()

    def sheet(self) -> bytes:
        if len(self.frames) != FRAMES:
            raise ValueError(f"expected {FRAMES} frames, got {len(self.frames)}")
        rows = [np.concatenate(self.frames[r * COLUMNS : (r + 1) * COLUMNS], axis=1) for r in range(ROWS)]
        image = np.ascontiguousarray(np.concatenate(rows, axis=0), dtype=np.uint8)
        return encode((image >> DROP_BITS) << DROP_BITS)


def retake(
    adapter: BodyAdapter, trial: records.Trial, record: records.RecordModel
) -> tuple[bytes, dict[str, object]]:
    """Run the trial again; return its sheet and what it measured, verified against the record first."""
    commands = {name: tuple(values) for name, values in trial.inputs.items()}
    reel = Reel(adapter)
    try:
        times = tuple(FRAME_SECONDS * (k + 1) for k in range(FRAMES))
        poses = sim_run(adapter.body, adapter.settings, commands, adapter.series_times, times, reel)
        measured = dict(adapter.measurer.measure(poses))
        verify(record, trial, measured)
        return reel.sheet(), measured
    finally:
        reel.close()


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def entry(record: records.RecordModel, trial: records.Trial, file: str, data: bytes) -> str:
    where = f"{record.name} {trial.id}"
    measured = {n: numbers.short(v, where) for n, v in trial.measurements if n in ("x", "y", "heading")}
    pairs = ", ".join(f"{n} = {v}" for n, v in measured.items())
    return "\n".join(
        [
            "[[retake]]",
            f"application = {_toml_string(record.application)}",
            f"session = {_toml_string(record.session)}",
            f"trial = {_toml_string(trial.id)}",
            f"file = {_toml_string(file)}",
            f"sha256 = {_toml_string(hashlib.sha256(data).hexdigest())}",
            f"source_picture = {_toml_string(trial.picture.digest)}",
            f"columns = {COLUMNS}",
            f"rows = {ROWS}",
            f"interval = {INTERVAL_MS}",
            f"frame_seconds = {FRAME_SECONDS}",
            f"track = {_toml_string(TRACK)}",
            f"track_step = {TRACK_STEP}",
            f"measured = {{{pairs}}}",
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Retake the pictures of body-lab trials for display."
    )
    parser.add_argument("--sessions", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="the display folder; absent or empty")
    parser.add_argument("--session", action="append", required=True, help="a body-lab session id; repeat")
    parser.add_argument(
        "--unlabelled-body",
        default=None,
        help="the body of a session whose record names none (made before body labels); never guessed",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.out.exists() and any(args.out.iterdir()):
            raise NotebookError(str(args.out), "the display folder is not empty; give a new or empty folder")
        loaded = {r.session: r for r in records.load(args.sessions) if r.application == APPLICATION}
        for name in args.session:
            if name not in loaded:
                raise NotebookError(name, "is not a body-lab session of the records")
        adapters: dict[str, BodyAdapter] = {}
        args.out.mkdir(parents=True, exist_ok=True)
        blocks: list[str] = []
        for name in args.session:
            record = loaded[name]
            body = record.variant or args.unlabelled_body
            if body is None:
                raise NotebookError(
                    name, "the record names no body; give --unlabelled-body to say which it was"
                )
            if body not in adapters:
                adapters[body] = BodyAdapter(variant=body)
            adapter = adapters[body]
            for trial in record.trials:
                data, _ = retake(adapter, trial, record)
                file = f"{record.session}-{trial.id}.png"
                (args.out / file).write_bytes(data)
                blocks.append(entry(record, trial, file, data))
                print(
                    f"{PROG}: {record.session} {trial.id} matches the record; {len(data)} bytes", flush=True
                )
        (args.out / "manifest.toml").write_text("\n".join(blocks), encoding="utf-8")
    except NotebookError as error:
        print(f"{PROG}: {error.where}: {error.problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
