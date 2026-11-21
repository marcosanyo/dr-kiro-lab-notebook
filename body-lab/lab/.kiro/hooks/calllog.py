"""The logging hook (Requirement 17.11, design F9). Copied into a lab's `.kiro/hooks/` by `bench-lab-hooks`.

    uv run --no-project python -B .kiro/hooks/calllog.py pre|post

Appends one JSON line per tool call to the hook log, which lies outside the lab. The log is named by the
lab's session file, `<lab>.bench-session.json` next to the lab folder (design D2; `bench.frontend.pointer`
writes it). The log is for the builder and is never part of the session record. If the session file is
missing or unusable, or the line cannot be written, the hook exits 2: the pre-tool hook then blocks the call,
so no call goes unlogged; the post-tool hook can only report the failure.

Standard library only. The script holds no path: the lab is the folder two levels above this script.
"""

import json
import sys
import time
from pathlib import Path

BLOCK = 2
SESSION_FILE_SUFFIX = ".bench-session.json"  # the same as bench.frontend.pointer.SUFFIX


class LogError(Exception):
    pass


def lab_folder() -> Path:
    return Path(__file__).resolve().parents[2]


def hook_log(lab: Path) -> Path:
    """The hook log named by the session file of `lab`. Raise LogError if it cannot be used."""
    session_file = lab.parent / f"{lab.name}{SESSION_FILE_SUFFIX}"
    try:
        data = json.loads(session_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise LogError(f"cannot read the lab's session file: {error}") from error
    value = data.get("hook_log") if isinstance(data, dict) else None
    if not isinstance(value, str) or not value:
        raise LogError("the lab's session file has no hook_log path")
    return (session_file.parent / value).resolve()


def append(phase: str, tool_name: object, tool_input: object, reason: str | None = None) -> None:
    """Append one line to the hook log. Raise LogError if it cannot be written."""
    target = hook_log(lab_folder())
    line: dict[str, object] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": phase,
        "tool_name": tool_name,
        "tool_input": tool_input,
    }
    if reason is not None:
        line["reason"] = reason
    try:
        with open(target, "a", encoding="utf-8") as log:
            log.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError as error:
        raise LogError(f"cannot write the hook log: {error}") from error


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) == 2 else ""
    if phase not in ("pre", "post"):
        print("That tool is not available in this lab.", file=sys.stderr)
        return BLOCK
    raw = sys.stdin.read()
    try:
        event = json.loads(raw)
        name = event.get("tool_name") if isinstance(event, dict) else None
        given = event.get("tool_input") if isinstance(event, dict) else None
    except json.JSONDecodeError:
        name, given = None, raw
    try:
        append(phase, name, given)
    except LogError:
        print("The lab's call log is not available, so the call is not allowed.", file=sys.stderr)
        return BLOCK
    return 0


if __name__ == "__main__":
    sys.exit(main())
