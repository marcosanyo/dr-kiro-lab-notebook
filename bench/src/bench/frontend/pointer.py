"""The session file of a lab: where `bench-mcp` and the logging hook find the session (design F7, F9, D2).

    <lab>.bench-session.json        next to the lab folder, never inside it

One JSON object with two fields, `session_config` and `hook_log`: the paths of the session config and of
the hook log, relative to the folder that holds the session file. `bench-new-session` and `bfs-run` write it
when a session starts. `bench-mcp` reads it for the lab it is started in (its working folder: Kiro CLI
started in the lab, or the Kiro IDE with only the lab open, Requirement 17.12), and the logging hook reads it
for the lab it is installed in. Nothing else names these paths: there is no environment variable to set, so
the IDE runs a session as it is opened.

The file sits outside the lab, so the confinement hook refuses Dr. Kiro any read of it, and no path to the
builder's side is written into the lab (rules.md, Blind).

Standard library only. The logging hook keeps its own reader (`calllog.hook_log`), because it is copied
into the lab alone; a test checks that both read the same file.
"""

import json
import os
from pathlib import Path

SUFFIX = ".bench-session.json"
FIELDS = ("session_config", "hook_log")
# The messages name no path: they reach stderr, which the reader's Kiro log may show (rules.md 1).
WHERE = "the lab's session file"


class PointerError(Exception):
    """The session file is missing or cannot be used. The message says what."""


def path_for(lab: Path) -> Path:
    lab = Path(lab).resolve()
    return lab.parent / f"{lab.name}{SUFFIX}"


def write(lab: Path, session_config: Path, hook_log: Path) -> Path:
    """Write the session file of `lab`. Both paths must lie outside the lab."""
    lab = Path(lab).resolve()
    target = path_for(lab)
    values = {}
    for name, value in (("session_config", session_config), ("hook_log", hook_log)):
        resolved = Path(value).resolve()
        if resolved.is_relative_to(lab):
            raise PointerError(f"the {name} {resolved} lies inside the lab {lab}; it must lie outside")
        values[name] = os.path.relpath(resolved, target.parent)
    target.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    return target


def read(lab: Path) -> dict[str, Path]:
    """The two paths of the session file of `lab`, resolved. Raise PointerError if it cannot be used."""
    target = path_for(lab)
    if not target.is_file():
        raise PointerError(
            f"{WHERE} is not there; start the session with bench-new-session, "
            "and run bench-mcp in the lab folder"
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PointerError(f"{WHERE} is not valid JSON ({error})") from error
    if not isinstance(data, dict) or sorted(data) != sorted(FIELDS):
        raise PointerError(f"{WHERE} must have exactly the keys {', '.join(FIELDS)}")
    paths = {}
    for name in FIELDS:
        value = data[name]
        if not isinstance(value, str) or not value:
            raise PointerError(f"{WHERE}: {name} must be a path")
        paths[name] = (target.parent / value).resolve()
    return paths
