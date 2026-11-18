"""Turns of the reader's Kiro CLI (design 3.10, Requirements 9.6 and 11.6, Decision 15).

One turn is one Kiro CLI process. The run script sends the fixed start line on the first
turn and the fixed continue line on every later turn. Nothing else is ever sent. The stop
reasons are bench wording: `bench-stop` seals them into the record, so they hold no
forbidden term.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

START_LINE = "Begin the session."
CONTINUE_LINE = "Continue the session."
IDLE_REASON = "the reader called no bench tool in two turns in a row"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
KINDS = ("start", "continue")


class TurnsError(Exception):
    """A turn request that cannot be built. The message names the value that was refused."""


def exit_reason(code: int) -> str:
    """The stop reason for a turn whose Kiro CLI process exited with a non-zero code (design B26)."""
    return f"the reader's Kiro CLI exited with code {code}"


@dataclass(frozen=True)
class Prompt:
    kind: str  # "start" | "continue"
    sha256: str  # of the line sent, UTF-8
    time: str  # UTC, when the turn started
    exit: int  # Kiro CLI's exit code
    entries_before: int  # entries in the state record before the turn
    entries_after: int  # and after it


@dataclass(frozen=True)
class TurnsEnd:
    sealed: bool
    stop_reason: str | None  # None when the record is sealed
    prompts: tuple[Prompt, ...]


def line_for(kind: str) -> str:
    """The fixed line sent for a prompt kind."""
    if kind == "start":
        return START_LINE
    if kind == "continue":
        return CONTINUE_LINE
    raise TurnsError(f"unknown prompt kind {kind!r}; expected one of {', '.join(KINDS)}")


DEFAULT_EFFORT = "default"


def kiro_command(kind: str, model: str, effort: str) -> list[str]:
    """The headless Kiro CLI command for one turn (design 3.10). `--resume` is set on every continue turn.

    The effort `default` omits `--effort`, so Kiro CLI uses its own default (Decision K29).
    """
    if not model:
        raise TurnsError("the model is empty; a model name is required")
    if not effort:
        raise TurnsError("the effort is empty; an effort value is required")
    command = [
        "kiro-cli",
        "chat",
        "--v3",
        "--no-interactive",
        "--require-mcp-startup",
        "--trust-workspace",
        "--trust-tools=",
        "--agent",
        "reader",
        "--model",
        model,
    ]
    if effort != DEFAULT_EFFORT:
        command += ["--effort", effort]
    if kind == "continue":
        command.append("--resume")
    command.append(line_for(kind))
    return command


def run_turns(
    launch: Callable[[str], int],
    entries: Callable[[], tuple[int, bool]],
    save: Callable[[tuple[Prompt, ...]], None],
) -> TurnsEnd:
    """Run turns until the record is sealed or a stop rule applies.

    `launch(kind)` runs one turn and returns the exit code. `entries()` returns the number of
    entries in the state record and whether its last entry is a seal. `save` receives the
    prompts so far after every turn. After each turn:

    1. Sealed: stop, whatever the exit code.
    2. Exit code not 0: stop, with the exit reason.
    3. No new entry in this turn and none in the turn before: stop, with the idle reason.
       There is no turn before the first one, so a silent first turn does not stop the run.
    4. Otherwise send the continue line. There is no maximum (Decision 15).
    """
    prompts: list[Prompt] = []
    previous_idle = False
    kind = "start"
    while True:
        line = line_for(kind)
        before, _ = entries()
        started = datetime.now(UTC).strftime(TIME_FORMAT)
        code = launch(kind)
        after, sealed = entries()
        prompts.append(
            Prompt(kind, hashlib.sha256(line.encode("utf-8")).hexdigest(), started, code, before, after)
        )
        recorded = tuple(prompts)
        save(recorded)
        if sealed:
            return TurnsEnd(True, None, recorded)
        if code != 0:
            return TurnsEnd(False, exit_reason(code), recorded)
        idle = after == before
        if idle and previous_idle:
            return TurnsEnd(False, IDLE_REASON, recorded)
        previous_idle = idle
        kind = "continue"
