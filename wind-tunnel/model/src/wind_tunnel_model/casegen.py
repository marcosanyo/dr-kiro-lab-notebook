"""Write an OpenFOAM case folder from the templates in ``model/case/`` (pure text, no solver needed).

Every file under ``case/`` is a template. ``@NAME@`` is replaced by the value named ``NAME`` (a float or an
integer by ``repr``, a string as it is). A file named ``*.in`` is written without that suffix. Files are
written in sorted order with ``\\n`` endings, so equal inputs give identical bytes. A placeholder with no value, or one
left after the substitution, is an error.
"""

from __future__ import annotations

import re
from pathlib import Path

from wind_tunnel_model.settings import Settings, frame_times

CASE_DIR = Path(__file__).resolve().parents[2] / "case"
KNOB_NAMES = ("aspect", "corner", "splitter", "angle")
# The mesh file that the mesher writes into the case folder, and that the first command of Allrun reads.
MESH_FILE = "case.msh"
SAMPLE_POINTS_FILE = "system/samplePoints"
_PLACEHOLDER = re.compile(r"@([A-Za-z0-9_]*)@")
_EXECUTABLE = {"Allrun"}


class CaseError(Exception):
    """The case cannot be written. The message says what and where (builder side only)."""


def placeholder_values(settings: Settings) -> dict[str, str]:
    """The text for every placeholder, from the settings."""
    flow, time, patches = settings.flow, settings.time, settings.patches
    times = frame_times(settings)
    values: dict[str, float | int | str] = {
        "NU": flow.speed * flow.height / flow.reynolds,
        "SPEED": flow.speed,
        "DENSITY": flow.density,
        "END": time.end,
        "INITIAL_DELTA_T": time.initial_delta_t,
        "MAX_CO": time.max_co,
        "MAX_DELTA_T": time.max_delta_t,
        "PROCESSES": settings.run.processes,
        "FIRST_FRAME_TIME": times[0],
        "LAST_FRAME_TIME": times[-1],
        "FRAME_SPACING": settings.picture.spacing,
        "PATCH_INLET": patches.inlet,
        "PATCH_OUTLET": patches.outlet,
        "PATCH_LATERAL": patches.lateral,
        "PATCH_OBSTACLE": patches.obstacle,
        "PATCH_FRONT_AND_BACK": patches.front_and_back,
        "IMAGE_TAG": settings.image.tag,
        "MESH_FILE": MESH_FILE,
    }
    return {k: v if isinstance(v, str) else repr(v) for k, v in values.items()}


def sample_points(settings: Settings) -> str:
    """The cell centres of the picture grid as an OpenFOAM list of points, rows from the top of the window."""
    pic = settings.picture
    x0, x1, y0, y1 = pic.window
    dx = (x1 - x0) / pic.cell_width
    dy = (y1 - y0) / pic.cell_height
    z = settings.flow.depth / 2
    lines = ["("]
    for j in range(pic.cell_height):
        y = y1 - (j + 0.5) * dy
        for i in range(pic.cell_width):
            lines.append(f"({x0 + (i + 0.5) * dx!r} {y!r} {z!r})")
    lines.append(")")
    return "\n".join(lines) + "\n"


def _substitute(text: str, values: dict[str, str], where: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise CaseError(f"{where}: placeholder @{name}@ has no value")
        return values[name]

    out = _PLACEHOLDER.sub(replace, text)
    if _PLACEHOLDER.search(out):
        raise CaseError(f"{where}: an unfilled placeholder is left after substitution")
    return out


def render_case(
    knobs: dict[str, float],
    settings: Settings,
    dest: Path | str,
    template_dir: Path | str | None = None,
) -> tuple[Path, ...]:
    """Write the case into ``dest`` (new or empty) and return the paths written, in the order written.

    ``knobs`` must hold exactly the four knob names: the outline reaches the solver through the mesh file,
    so no knob value appears in the text of the case.
    """
    if set(knobs) != set(KNOB_NAMES):
        raise CaseError(f"knobs: expected exactly {sorted(KNOB_NAMES)}, found {sorted(knobs)}")
    source = Path(template_dir) if template_dir is not None else CASE_DIR
    if not source.is_dir():
        raise CaseError(f"{source}: template folder not found")
    target = Path(dest)
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise CaseError(f"{target}: case folder exists and is not empty")
    values = placeholder_values(settings)
    templates = sorted(p for p in source.rglob("*") if p.is_file())
    if not templates:
        raise CaseError(f"{source}: no templates")
    rendered: list[tuple[str, str]] = []
    for path in templates:
        rel = path.relative_to(source).as_posix()
        name = rel[:-3] if rel.endswith(".in") else rel
        rendered.append((name, _substitute(path.read_text(encoding="utf-8"), values, rel)))
    rendered.append((SAMPLE_POINTS_FILE, sample_points(settings)))
    rendered.sort(key=lambda item: item[0])
    written = []
    for name, text in rendered:
        out = target / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(text.encode("utf-8"))
        out.chmod(0o755 if name in _EXECUTABLE else 0o644)
        written.append(out)
    return tuple(written)
