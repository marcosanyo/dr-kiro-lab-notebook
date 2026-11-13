"""Loading the body, the camera added in code, and stepping one trial (body-lab Requirement 1, design 2).

The model file is read, never changed. The wiring decides which channel drives which actuator and with which
sign; that mapping stays inside this module.
"""

import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass

import mujoco
import numpy as np

from body_lab.settings import MODEL_FILE, WIRING_FILE, Settings

CAMERA = "overhead"


@dataclass(frozen=True)
class Wiring:
    control_hz: int
    trial_seconds: float
    settle_seconds: float
    channels: tuple[tuple[str, int], ...]  # (actuator name, sign) in channel order


def load_wiring() -> Wiring:
    data = json.loads(WIRING_FILE.read_text(encoding="utf-8"))
    channels = sorted(data["channels"], key=lambda c: c["channel"])
    if [c["channel"] for c in channels] != list(range(len(channels))):
        raise ValueError("wiring channels must be numbered 0, 1, ... without gaps")
    for c in channels:
        if c["sign"] not in (1, -1):
            raise ValueError("wiring sign must be 1 or -1")
    return Wiring(
        control_hz=int(data["control_hz"]),
        trial_seconds=float(data["trial_seconds"]),
        settle_seconds=float(data["settle_seconds"]),
        channels=tuple((c["actuator"], c["sign"]) for c in channels),
    )


@dataclass(frozen=True)
class Pose:
    """World pose of the tracked point: position, forward axis and outward normal of the marker."""

    position: tuple[float, float, float]
    forward: tuple[float, float, float]
    normal: tuple[float, float, float]


@dataclass
class Body:
    model: mujoco.MjModel
    data: mujoco.MjData
    root: int  # body id of the free-floating body that carries the marker
    marker: tuple[float, float, float]  # marker position in that body's frame
    actuators: tuple[int, ...]  # actuator id per channel
    signs: tuple[int, ...]
    servo: tuple[bool, ...]  # position actuator (rate-limited) or not
    camera: tuple[float, float, float]


def _marker_geom(model: mujoco.MjModel, root: int) -> int:
    """The marker: the first geom of the root body that takes no part in contact (painted on, mass 0)."""
    for g in range(model.ngeom):
        if model.geom_bodyid[g] == root and model.geom_contype[g] == 0 and model.geom_conaffinity[g] == 0:
            return g
    raise ValueError("the root body has no marker geom")


def build(settings: Settings) -> Body:
    wiring = load_wiring()
    spec = mujoco.MjSpec.from_file(str(MODEL_FILE))
    camera_pos = (0.0, 0.0, settings.camera_height_m)
    cam = spec.worldbody.add_camera()
    cam.name = CAMERA
    cam.pos = list(camera_pos)
    cam.fovy = settings.camera_fovy_deg
    cam.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    cam.alt.xyaxes = [1, 0, 0, 0, 1, 0]  # image x along world x, looking straight down
    model = spec.compile()
    data = mujoco.MjData(model)
    roots = [b for b in range(1, model.nbody) if model.body_parentid[b] == 0 and model.body_jntnum[b] > 0]
    if len(roots) != 1:
        raise ValueError("the model must have exactly one free-floating body")
    root = roots[0]
    marker = tuple(float(v) for v in model.geom_pos[_marker_geom(model, root)])
    ids, servo = [], []
    for name, _sign in wiring.channels:
        a = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
        if a < 0:
            raise ValueError("the wiring names an actuator the model lacks")
        ids.append(a)
        # A position actuator (servo) has bias -kp on the joint position; a velocity actuator has none.
        servo.append(bool(model.actuator_biasprm[a, 1] < 0))
    signs = tuple(sign for _name, sign in wiring.channels)
    return Body(model, data, root, marker, tuple(ids), signs, tuple(servo), camera_pos)


def _reset(body: Body, settings: Settings) -> None:
    m, d = body.model, body.data
    mujoco.mj_resetData(m, d)
    adr = m.jnt_qposadr[m.body_jntadr[body.root]]
    start_z = float(m.body_pos[body.root][2])
    d.qpos[adr : adr + 3] = (-settings.start_behind_m, 0.0, start_z)
    half = math.radians(settings.start_roll_deg) / 2
    d.qpos[adr + 3 : adr + 7] = (math.cos(half), math.sin(half), 0.0, 0.0)
    mujoco.mj_forward(m, d)


def pose(body: Body) -> Pose:
    d = body.data
    rot = d.xmat[body.root].reshape(3, 3)
    position = d.xpos[body.root] + rot @ np.array(body.marker)
    return Pose(tuple(map(float, position)), tuple(map(float, rot[:, 0])), tuple(map(float, rot[:, 2])))


Commands = Mapping[str, tuple[float, ...]]  # knob name -> one command per control step


def run(
    body: Body,
    settings: Settings,
    commands: Commands,
    sample_times: tuple[float, ...],
    frame_times: tuple[float, ...],
    on_frame: Callable[[mujoco.MjData], None],
) -> list[Pose]:
    """Settle, then run the trial. Return the tracked pose at each sample time, and call on_frame at
    each frame time."""
    m, d = body.model, body.data
    wiring = load_wiring()
    _reset(body, settings)
    dt = 1.0 / wiring.control_hz
    substeps = round(dt / m.opt.timestep)
    steps = round(wiring.trial_seconds * wiring.control_hz)
    max_move = math.radians(settings.servo_rate_deg_s) * dt
    lo = m.actuator_ctrlrange[list(body.actuators), 0]
    hi = m.actuator_ctrlrange[list(body.actuators), 1]
    targets = np.clip(np.zeros(len(body.actuators)), lo, hi)
    knobs = [f"c{i}" for i in range(len(body.actuators))]

    def apply(command: np.ndarray) -> None:
        nonlocal targets
        wanted = lo + (command * np.array(body.signs) + 1.0) / 2.0 * (hi - lo)
        for i, is_servo in enumerate(body.servo):
            if is_servo:
                targets[i] += float(np.clip(wanted[i] - targets[i], -max_move, max_move))
            else:
                targets[i] = wanted[i]
        d.ctrl[list(body.actuators)] = targets
        mujoco.mj_step(m, d, nstep=substeps)

    for _ in range(round(wiring.settle_seconds * wiring.control_hz)):
        apply(np.zeros(len(knobs)))
    start = d.time
    poses: list[Pose] = []
    samples = list(sample_times)
    frames = list(frame_times)

    def due(times: list[float], now: float) -> bool:
        return bool(times) and now >= times[0] - 1e-9

    for k in range(steps + 1):
        now = d.time - start
        while due(samples, now):
            poses.append(pose(body))
            samples.pop(0)
        while due(frames, now):
            on_frame(d)
            frames.pop(0)
        if k == steps:
            break
        apply(np.array([commands[name][k] for name in knobs]))
    if samples or frames:
        raise ValueError("sample or frame times lie beyond the trial")
    return poses


def channel_count() -> int:
    return len(load_wiring().channels)
