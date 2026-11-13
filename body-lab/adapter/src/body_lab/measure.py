"""The measurer (body-lab Requirement 2, design 3).

`Measurer` is the fixed contract: the measurement names and units, the meaning of `lost`, and the text that
says how the values are made. `PoseMeasurer` computes them from the simulator's pose, limited to what the
camera straight above could measure. A marker-reading measurer can later implement the same protocol from
rendered frames; it is not built now.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Protocol

from bench.adapter import Measurement, NotMeasured

from body_lab.settings import Settings
from body_lab.sim import Pose

LOST = "lost"
FACED_AWAY = "the tracked point faced away from the camera"
OUT_OF_VIEW = "the tracked point left the camera's view"
SCALARS = (("x", "m"), ("y", "m"), ("heading", "deg"))
SERIES = (("track_x", "m"), ("track_y", "m"), ("track_heading", "deg"))

Values = Mapping[str, float | tuple[float, ...] | NotMeasured]


def measurements() -> tuple[Measurement, ...]:
    return tuple(Measurement(name, unit, "scalar", (LOST,)) for name, unit in SCALARS) + tuple(
        Measurement(name, unit, "series", (LOST,)) for name, unit in SERIES
    )


class Measurer(Protocol):
    def measurements(self) -> tuple[Measurement, ...]: ...

    def measured_by(self) -> str: ...

    def measure(self, poses: Sequence[Pose]) -> Values: ...


def _wrap(degrees: float) -> float:
    """Wrap to (-180, 180]."""
    wrapped = math.fmod(degrees, 360.0)
    if wrapped <= -180.0:
        wrapped += 360.0
    elif wrapped > 180.0:
        wrapped -= 360.0
    return wrapped + 0.0


class PoseMeasurer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.camera = (0.0, 0.0, settings.camera_height_m)
        self.tan_half_v = math.tan(math.radians(settings.camera_fovy_deg) / 2)
        self.tan_half_h = self.tan_half_v * settings.image_width / settings.image_height

    def measurements(self) -> tuple[Measurement, ...]:
        return measurements()

    def view_on_floor(self) -> tuple[float, float]:
        """Half width (along x) and half height (along y) of the view on the floor, in m."""
        h = self.settings.camera_height_m
        return h * self.tan_half_h, h * self.tan_half_v

    def measured_by(self) -> str:
        half_x, half_y = self.view_on_floor()
        behind = self.settings.start_behind_m
        return (
            "Computed from the simulator's pose, as the quantities a camera straight above could measure; "
            "not measured from a camera image. "
            f"The camera sees a floor area of {2 * half_x:.2f} m by {2 * half_y:.2f} m. "
            "x, y and heading are relative to the start of each trial: "
            "x in the direction the body faces at the start, y to its left, "
            "heading counter-clockwise seen from above, in (-180, 180]. "
            f"At the start the body is at x = 0, y = 0, and the view spans x from {behind - half_x:.2f} to "
            f"{behind + half_x:.2f} m and y from {-half_y:.2f} to {half_y:.2f} m. "
            "A value is lost when the camera could not see the tracked point."
        )

    def visible(self, p: Pose) -> str | None:
        """None if the camera sees the tracked point, else the reason it does not."""
        cx, cy, cz = self.camera
        px, py, pz = p.position
        depth = cz - pz
        to_camera = (cx - px, cy - py, cz - pz)
        if sum(n * t for n, t in zip(p.normal, to_camera, strict=True)) <= 0:
            return FACED_AWAY
        if depth <= 0 or abs(px - cx) > depth * self.tan_half_h or abs(py - cy) > depth * self.tan_half_v:
            return OUT_OF_VIEW
        return None

    def measure(self, poses: Sequence[Pose]) -> Values:
        start = poses[0]
        start_heading = math.atan2(start.forward[1], start.forward[0])
        cos_h, sin_h = math.cos(-start_heading), math.sin(-start_heading)
        rows: list[tuple[float, float, float]] = []
        lost: str | None = None
        for p in poses:
            reason = self.visible(p)
            if reason is not None and lost is None:
                lost = reason
            dx, dy = p.position[0] - start.position[0], p.position[1] - start.position[1]
            heading = math.degrees(math.atan2(p.forward[1], p.forward[0]) - start_heading)
            rows.append((dx * cos_h - dy * sin_h + 0.0, dx * sin_h + dy * cos_h + 0.0, _wrap(heading)))
        values: dict[str, float | tuple[float, ...] | NotMeasured] = {}
        end_reason = self.visible(poses[-1])
        for i, (name, _unit) in enumerate(SCALARS):
            values[name] = NotMeasured(LOST, end_reason) if end_reason else rows[-1][i]
        for i, (name, _unit) in enumerate(SERIES):
            values[name] = NotMeasured(LOST, lost) if lost else tuple(r[i] for r in rows)
        return values
