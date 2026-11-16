"""Gmsh recipe: body outline -> one-layer 3D mesh file that OpenFOAM reads as a 2D case (design 3).

The domain is a rectangle around the centre of the body (the origin), with the body as a hole. The surface
mesh is extruded one layer in z by ``flow.depth``, so the mid-plane is at ``z = depth / 2`` (the plane
that the vorticity sampling uses). Mesh generation uses no random seed; the 2D algorithm and the thread
count come from ``settings.mesh``. The file is Gmsh format 2.2, ASCII, which is what ``gmshToFoam`` reads.

Gmsh runs in a child process (``mesh_worker``), never in the bench server (Decision 43).
"""

from __future__ import annotations

import dataclasses
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Protocol

from wind_tunnel_model.casegen import MESH_FILE
from wind_tunnel_model.geometry import Arc, Line, Outline
from wind_tunnel_model.settings import Settings

WORKER_MODULE = "wind_tunnel_model.mesh_worker"

# Shape of the size fields. The three sizes and the wake length are in constants.toml [mesh]; these two
# extents are part of the recipe. STARTING VALUES, confirmed by task 14.1 together with the sizes.
BODY_TRANSITION = 1.5  # distance from the body over which the size grows from size_body to size_far
WAKE_HALF_WIDTH = 2.0  # the wake box spans y in [-WAKE_HALF_WIDTH, WAKE_HALF_WIDTH]
WAKE_BLEND = 2.0  # distance over which the size grows from size_wake to size_far outside the box
VOLUME_NAME = "fluid"  # the cells; gmshToFoam needs the cells in a physical group, so there is a sixth group


class MeshError(Exception):
    """The mesher could not produce a mesh. Builder side only. ``detail`` holds the full failure detail."""

    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.detail = detail


class MeshTimeout(MeshError):
    """The time limit of the run was reached before or while the mesh was built."""


class Mesher(Protocol):
    def build(
        self, outline: Outline, settings: Settings, dest: Path, *, timeout_s: float | None = None
    ) -> None:
        """Write the mesh file ``MESH_FILE`` into the case folder ``dest``; raise ``MeshError`` on failure.

        ``timeout_s`` is the time left of the run's limit, in seconds; ``None`` means no limit."""
        ...


class FakeMesher:
    """Writes a fixed small file; for tests that need no Gmsh."""

    CONTENT = "$MeshFormat\n2.2 0 8\n$EndMeshFormat\n"

    def build(
        self, outline: Outline, settings: Settings, dest: Path, *, timeout_s: float | None = None
    ) -> None:
        Path(dest).mkdir(parents=True, exist_ok=True)
        (Path(dest) / MESH_FILE).write_text(self.CONTENT, encoding="utf-8", newline="\n")


class GmshMesher:
    """The real mesher. Gmsh runs in a short-lived child process, always in the main thread of a fresh
    interpreter (Decision 43): Gmsh crashes the process (SIGSEGV in its OpenMP runtime) when it is
    initialised in a new thread after another thread has initialised it and exited, and the bench front
    end runs every call in a changing worker thread. A crash of Gmsh now ends the child, not the bench.
    ``cells`` holds the number of cells of the last mesh built."""

    def __init__(self) -> None:
        self.cells: int | None = None

    def build(
        self, outline: Outline, settings: Settings, dest: Path, *, timeout_s: float | None = None
    ) -> None:
        if not outline:
            raise MeshError("the outline is empty")
        if timeout_s is not None and timeout_s <= 0:
            raise MeshTimeout(
                "the time limit was used up before the mesh was built", f"remaining: {timeout_s!r}"
            )
        target = Path(dest) / MESH_FILE
        target.parent.mkdir(parents=True, exist_ok=True)
        request = json.dumps(
            {
                "outline": outline_to_data(outline),
                "settings": dataclasses.asdict(settings),
                "target": str(target),
            }
        )
        try:
            done = subprocess.run(  # noqa: S603 - a list of arguments, no shell
                [sys.executable, "-m", WORKER_MODULE],
                input=request,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as expired:
            raise MeshTimeout(
                "the mesh was still being built at the time limit",
                f"stdout: {expired.stdout!r}\nstderr: {expired.stderr!r}",
            ) from expired
        if done.returncode != 0:
            raise MeshError(
                f"the mesh process exited with status {done.returncode}",
                f"exit status: {done.returncode}\nstderr:\n{done.stderr.strip()}",
            )
        try:
            self.cells = int(json.loads(done.stdout)["cells"])
        except (ValueError, KeyError, TypeError) as error:
            raise MeshError(
                "the mesh process gave no cell count",
                f"stdout: {done.stdout!r}\nstderr:\n{done.stderr.strip()}",
            ) from error


def outline_to_data(outline: Outline) -> list[dict]:
    """The outline as plain data (for the child process); floats survive JSON exactly."""
    return [
        {"line": [list(piece.p), list(piece.q)]}
        if isinstance(piece, Line)
        else {"arc": [list(piece.p), list(piece.centre), list(piece.q)]}
        for piece in outline
    ]


def outline_from_data(data: list[dict]) -> Outline:
    pieces: list[Line | Arc] = []
    for item in data:
        if "line" in item:
            p, q = item["line"]
            pieces.append(Line(tuple(p), tuple(q)))
        else:
            p, centre, q = item["arc"]
            pieces.append(Arc(tuple(p), tuple(centre), tuple(q)))
    return tuple(pieces)


def build_in_this_process(outline: Outline, settings: Settings, target: Path) -> int:
    """Run Gmsh in the calling thread of this process and write ``target``; return the number of cells.
    Called by ``mesh_worker`` in the main thread of a fresh interpreter, and by nothing else."""
    import gmsh  # imported here so that a missing Gmsh is an error of the call, not of the module

    # interruptible=False: Gmsh then installs no SIGINT handler (Decision 41).
    gmsh.initialize(interruptible=False)
    try:
        return _build(gmsh, outline, settings, target)
    except MeshError:
        raise
    except Exception as error:  # noqa: BLE001 - re-raised as MeshError with the cause kept
        raise MeshError(f"Gmsh failed: {error}") from error
    finally:
        gmsh.finalize()


def _build(gmsh, outline: Outline, settings: Settings, target: Path) -> int:
    mesh, domain, flow, patches = settings.mesh, settings.domain, settings.flow, settings.patches
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.option.setNumber("General.NumThreads", mesh.threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads1D", mesh.threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads2D", mesh.threads)
    gmsh.option.setNumber("Mesh.MaxNumThreads3D", mesh.threads)
    gmsh.option.setNumber("Mesh.Algorithm", mesh.algorithm)
    gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
    gmsh.option.setNumber("Mesh.Binary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.model.add("case")
    geo = gmsh.model.geo

    # Outer rectangle: bottom, outlet, top, inlet (counter-clockwise).
    x0, x1 = -domain.ahead, domain.behind
    y0, y1 = -domain.above_below, domain.above_below
    corners = [geo.addPoint(x, y, 0.0) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    bottom, outlet, top, inlet = (geo.addLine(corners[i], corners[(i + 1) % 4]) for i in range(4))
    outer_loop = geo.addCurveLoop([bottom, outlet, top, inlet])

    # Body curves from the outline; equal endpoints share one point.
    points: dict[tuple[float, float], int] = {}

    def point(p: tuple[float, float]) -> int:
        if p not in points:
            points[p] = geo.addPoint(p[0], p[1], 0.0)
        return points[p]

    body_curves: list[int] = []
    for piece in outline:
        if isinstance(piece, Line):
            body_curves.append(geo.addLine(point(piece.p), point(piece.q)))
        elif isinstance(piece, Arc):
            body_curves.append(geo.addCircleArc(point(piece.p), point(piece.centre), point(piece.q)))
        else:
            raise MeshError(f"unknown outline piece {piece!r}")
    body_loop = geo.addCurveLoop(body_curves)
    surface = geo.addPlaneSurface([outer_loop, body_loop])

    # One layer in z: prisms from the triangles.
    extruded = geo.extrude([(2, surface)], 0.0, 0.0, flow.depth, [1], recombine=True)
    geo.synchronize()
    far_face, volume = extruded[0][1], extruded[1][1]
    laterals = [dim_tag[1] for dim_tag in extruded[2:]]
    sides = [bottom, outlet, top, inlet, *body_curves]
    lateral_of = dict(zip(_boundary_curves(gmsh, surface), laterals, strict=True))
    if set(lateral_of) != set(sides):
        raise MeshError("the boundary of the surface does not match the curves of the recipe")

    groups = (
        (patches.inlet, [lateral_of[inlet]]),
        (patches.outlet, [lateral_of[outlet]]),
        (patches.lateral, [lateral_of[bottom], lateral_of[top]]),
        (patches.obstacle, [lateral_of[c] for c in body_curves]),
        (patches.front_and_back, [surface, far_face]),
    )
    for name, tags in groups:
        gmsh.model.addPhysicalGroup(2, tags, name=name)
    gmsh.model.addPhysicalGroup(3, [volume], name=VOLUME_NAME)

    _size_fields(gmsh, body_curves, settings)

    gmsh.model.mesh.generate(3)
    cells = _cell_count(gmsh)
    gmsh.write(str(target))
    return cells


def _boundary_curves(gmsh, surface: int) -> list[int]:
    """Curves of the surface boundary in the order in which ``extrude`` makes its side faces."""
    boundary = gmsh.model.getBoundary([(2, surface)], combined=False, oriented=False)
    return [tag for _, tag in boundary]


def _size_fields(gmsh, body_curves: list[int], settings: Settings) -> None:
    mesh = settings.mesh
    field = gmsh.model.mesh.field
    field.add("Distance", 1)
    field.setNumbers(1, "CurvesList", body_curves)
    field.setNumber(1, "Sampling", max(100, math.ceil(100 * len(body_curves) / 4)))
    field.add("Threshold", 2)
    field.setNumber(2, "InField", 1)
    field.setNumber(2, "SizeMin", mesh.size_body)
    field.setNumber(2, "SizeMax", mesh.size_far)
    field.setNumber(2, "DistMin", 0.0)
    field.setNumber(2, "DistMax", BODY_TRANSITION)
    field.add("Box", 3)
    field.setNumber(3, "VIn", mesh.size_wake)
    field.setNumber(3, "VOut", mesh.size_far)
    field.setNumber(3, "XMin", -1.0)
    field.setNumber(3, "XMax", mesh.wake_length)
    field.setNumber(3, "YMin", -WAKE_HALF_WIDTH)
    field.setNumber(3, "YMax", WAKE_HALF_WIDTH)
    field.setNumber(3, "ZMin", -1.0)
    field.setNumber(3, "ZMax", settings.flow.depth + 1.0)
    field.setNumber(3, "Thickness", WAKE_BLEND)
    field.add("Min", 4)
    field.setNumbers(4, "FieldsList", [2, 3])
    field.setAsBackgroundMesh(4)


def _cell_count(gmsh) -> int:
    types, tags, _ = gmsh.model.mesh.getElements(3)
    return sum(len(t) for t in tags)
