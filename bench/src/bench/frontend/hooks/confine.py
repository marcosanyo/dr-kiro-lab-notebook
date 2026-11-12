"""The confinement hook (Requirements 17.7-17.10, design F8). Copied into a lab's `.kiro/hooks/` by `bench-
lab-hooks`, and run before every tool call:

    uv run --no-project python .kiro/hooks/confine.py

It refuses, with exit code 2, every call that reads or writes a path outside the lab, every write into a
protected folder of the lab's `.kiro`, and every call it cannot read or classify. Refusals are logged with
the logging hook's function. Any exception also ends in exit 2, because any other exit code lets the call
through; this turns a failure into a refusal and does not hide it, since the exception goes to the hook
log.

Standard library only. The script holds no path: the lab is the folder two levels above this script, and
every check is built from path parts.
"""

import contextlib
import json
import sys
import traceback
from pathlib import Path

import calllog

BLOCK = 2
OUTSIDE = "That path is outside your folder. Use a path inside your folder."
PROTECTED = "That file is part of the lab's setup and cannot be changed."
UNKNOWN = "That tool is not available in this lab."

# Tools seen in the spike's hook log, and the field that holds their path (design F8).
PATH_TOOLS = {
    "read_file": "path",
    "list_directory": "path",
    "fs_write": "path",
    "fs_append": "path",
    "str_replace": "path",
}
WRITE_TOOLS = frozenset({"fs_write", "fs_append", "str_replace"})
PATHLESS_TOOLS = frozenset(
    {
        "file_search",
        "grep_search",
        "tool_load",
        "mcp_bench_register_hypothesis",
        "mcp_bench_run_experiment",
        "mcp_bench_record_verdict",
        "mcp_bench_end_session",
    }
)
SETUP_FOLDER = ".kiro"
PROTECTED_FOLDERS = frozenset({"agents", "hooks", "steering", "settings"})


def lab_folder() -> Path:
    return Path(__file__).resolve().parents[2]


def decide(event: object, lab: Path) -> str | None:
    """None to allow the call, or the refusal line in Dr. Kiro's terms."""
    if not isinstance(event, dict):
        return UNKNOWN
    name = event.get("tool_name")
    given = event.get("tool_input")
    if not isinstance(name, str) or not isinstance(given, dict):
        return UNKNOWN
    if name in PATHLESS_TOOLS:
        return None
    field = PATH_TOOLS.get(name)
    if field is None:
        return UNKNOWN
    value = given.get(field)
    if not isinstance(value, str) or not value:
        return UNKNOWN
    # A leading tilde is refused: the hook cannot know whether the tool expands it to a home folder.
    if Path(value).parts[0].startswith("~"):
        return OUTSIDE
    # Joined to the lab, so a relative path means "inside the lab"; resolve() follows parent-folder parts and
    # symbolic links before the comparison.
    resolved = (lab / value).resolve()
    if not resolved.is_relative_to(lab):
        return OUTSIDE
    parts = resolved.relative_to(lab).parts
    if name in WRITE_TOOLS and len(parts) >= 2 and parts[0] == SETUP_FOLDER and parts[1] in PROTECTED_FOLDERS:
        return PROTECTED
    return None


def main() -> int:
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        event = None
    reason = decide(event, lab_folder())
    if reason is None:
        return 0
    name = event.get("tool_name") if isinstance(event, dict) else None
    given = event.get("tool_input") if isinstance(event, dict) else raw
    # The call is refused either way; the refusal line below still reaches Dr. Kiro.
    with contextlib.suppress(calllog.LogError):
        calllog.append("refused", name, given, reason)
    print(reason, file=sys.stderr)
    return BLOCK


def run() -> int:
    try:
        return main()
    except Exception:  # noqa: BLE001 - any failure must refuse the call (17.9); the detail goes to the log
        # Nothing more can be done if even the log fails; the call is still refused.
        with contextlib.suppress(Exception):
            calllog.append("refused", None, None, "hook error: " + traceback.format_exc())
        print(UNKNOWN, file=sys.stderr)
        return BLOCK


if __name__ == "__main__":
    sys.exit(run())
