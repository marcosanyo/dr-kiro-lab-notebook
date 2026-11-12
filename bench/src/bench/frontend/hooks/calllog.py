"""The logging hook (Requirement 17.11, design F9). Copied into a lab's `.kiro/hooks/` by `bench-lab-hooks`.

    uv run --no-project python .kiro/hooks/calllog.py pre|post

Appends one JSON line per tool call to the file named by BENCH_HOOK_LOG, which lies outside the lab. The
log is for the builder and is never part of the session record. If the variable is missing or the line
cannot be written, the hook exits 2: the pre-tool hook then blocks the call, so no call goes unlogged; the
post-tool hook can only report the failure.

Standard library only. The script holds no path: the log file comes from the environment.
"""

import json
import os
import sys
import time

BLOCK = 2
ENV_VAR = "BENCH_HOOK_LOG"


class LogError(Exception):
    pass


def append(phase: str, tool_name: object, tool_input: object, reason: str | None = None) -> None:
    """Append one line to the hook log. Raise LogError if it cannot be written."""
    target = os.environ.get(ENV_VAR)
    if not target:
        raise LogError(f"{ENV_VAR} is not set")
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
