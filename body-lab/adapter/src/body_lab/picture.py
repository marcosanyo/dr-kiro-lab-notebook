"""The trial's picture: overhead frames laid out in one PNG (body-lab Requirement 4, design 4).

Frames are rendered offscreen with MuJoCo's renderer from the overhead camera. `MUJOCO_GL` is left to the
environment (macOS uses its default; on Linux set `egl` or `osmesa`). The PNG is written by the bench's
encoder, so it carries no text or metadata.
"""

import mujoco
import numpy as np
from bench.pictures import encode_png

from body_lab.settings import Settings
from body_lab.sim import CAMERA, Body


class FrameRecorder:
    def __init__(self, body: Body, settings: Settings) -> None:
        self.settings = settings
        self.renderer = mujoco.Renderer(body.model, settings.frame_height, settings.frame_width)
        self.frames: list[np.ndarray] = []

    def __call__(self, data: mujoco.MjData) -> None:
        self.renderer.update_scene(data, camera=CAMERA)
        self.frames.append(self.renderer.render().copy())

    def close(self) -> None:
        self.renderer.close()

    def png(self) -> bytes:
        s = self.settings
        if len(self.frames) != s.frame_count:
            raise ValueError(f"expected {s.frame_count} frames, got {len(self.frames)}")
        rows = []
        for start in range(0, s.frame_count, s.frame_columns):
            row = self.frames[start : start + s.frame_columns]
            while len(row) < s.frame_columns:
                row.append(np.zeros_like(self.frames[0]))
            rows.append(np.concatenate(row, axis=1))
        image = np.concatenate(rows, axis=0)
        return encode_png([[tuple(int(c) for c in pixel) for pixel in line] for line in image])


def frame_times(settings: Settings) -> tuple[float, ...]:
    return tuple(settings.frame_step_s * (k + 1) for k in range(settings.frame_count))
