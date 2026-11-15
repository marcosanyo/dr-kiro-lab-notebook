"""Rehearsal of a whole wind-tunnel session, without an LLM (wind-tunnel Decision 42).

It drives the real MCP front end (`bench-mcp`) over stdio, the way Kiro CLI does, with the real WindAdapter
and real Docker, then runs `bench-verify` and `bench-scan` on the sealed folder, as `README.md` ("Running a
session") says. It uses a new folder under `bench-run/wind-tunnel/rehearsal/` (git-ignored) with its own lab,
state folder and sessions folder; the real `wind-tunnel/lab`, `bench-run/wind-tunnel/state` and `sessions/`
are never touched.

Run it from the repository root, with the python of the installed tool (it has the MCP client and the
adapter):

    ~/.local/share/uv/tools/lab-bench/bin/python wind-tunnel/rehearse_session.py

It needs Docker and the solver image and takes a few minutes (two real runs). It stops at the first thing
that is not as expected and says what. The folder is named by the clock and is never deleted by this script.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

REPO = Path(__file__).resolve().parent.parent
SESSION_ID = "rehearsal-1"
SEED = 1
SETTLED = [1.5, 0.5, 1.0, 10.0]
NOT_SETTLING = [2.57819, 0.953007, 1.241, 0.83314]
REFUSED = [1.75, 0.01, 1.5, 5.0]
KNOBS = ("aspect", "corner", "splitter", "angle")
STOP_LIST = REPO / ".kiro/blind-scan/stop-list.txt"
SCAN_SOURCES = REPO / "wind-tunnel/adapter/scan_sources.toml"


class RehearsalError(Exception):
    """A step of the rehearsal did not give the expected result."""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalError(message)


def run(command: list[str], cwd: Path = REPO, timeout: int = 600) -> str:
    done = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    if done.returncode != 0:
        raise RehearsalError(
            f"{' '.join(command)} exited with {done.returncode}\n{done.stdout}\n{done.stderr}"
        )
    return done.stdout


def prediction(pid: str, when: list[float]) -> str:
    conditions = "\n".join(f"{name} = {value!r}" for name, value in zip(KNOBS, when, strict=True))
    return (
        f'[[prediction]]\nid = "{pid}"\nmeasurement = "cd"\nrange = [0.1, 5.0]\nlabel = "inside"\n'
        f"[prediction.when]\n{conditions}\n"
    )


def hypothesis_block() -> str:
    return (
        "### H1: rehearsal\n\n"
        "WHEN the knobs are at the given values, THE system SHALL give a cd between 0.1 and 5.0.\n\n"
        f"```prediction\n{prediction('P1', SETTLED)}{prediction('P2', NOT_SETTLING)}```\n"
    )


def experiment(rows: list[list[float]]) -> str:
    return f'# H1: rehearsal\nPHASE = "map"\nMODE = "compare"\nPARAMS = {list(KNOBS)!r}\nTRIALS = {rows!r}\n'


def text(result) -> str:
    return "".join(part.text for part in result.content if part.type == "text")


async def drive(lab: Path, config: Path) -> None:
    server = StdioServerParameters(command="bench-mcp", env={"BENCH_SESSION_CONFIG": str(config)}, cwd=lab)
    async with stdio_client(server) as (read, write), ClientSession(read, write) as client:
        await client.initialize()
        names = sorted(tool.name for tool in (await client.list_tools()).tools)
        check(
            names == ["end_session", "record_verdict", "register_hypothesis", "run_experiment"],
            f"unexpected tools {names}",
        )
        registered = await client.call_tool("register_hypothesis", {"id": "H1"})
        check(not registered.is_error, f"register_hypothesis refused: {text(registered)}")
        print("registered H1:", text(registered))

        (lab / "experiments/e1.py").write_text(experiment([SETTLED, NOT_SETTLING]), encoding="utf-8")
        started = time.monotonic()
        ran = await client.call_tool("run_experiment", {"path": "experiments/e1.py"})
        print(f"run_experiment took {time.monotonic() - started:.0f} s")
        check(not ran.is_error, f"run_experiment failed: {text(ran)}")
        data = json.loads(text(ran))
        check(data["budget_remaining"] == 22, f"budget after two trials: {data['budget_remaining']}")
        settled, unsettled = data["trials"]
        check(set(settled["measurements"]) >= {"cd"}, f"settled trial has no cd: {settled}")
        check(
            set(unsettled["not_measured"]) == {"cd", "cl_mean", "cl_amp", "strouhal", "shedding"}
            and not unsettled["measurements"],
            f"the second trial did not give not_settled for every measurement: {unsettled}",
        )
        for trial in (settled, unsettled):
            check(
                (lab / trial["picture"]).read_bytes().startswith(b"\x89PNG"), f"no picture {trial['picture']}"
            )
        print("measurements of the settled trial:", settled["measurements"])

        verdict = await client.call_tool(
            "record_verdict", {"experiment": "E1", "verdict": "partly", "words": "rehearsal: two trials ran."}
        )
        check(not verdict.is_error, f"record_verdict refused: {text(verdict)}")

        (lab / "experiments/e2.py").write_text(experiment([REFUSED]), encoding="utf-8")
        refused = await client.call_tool("run_experiment", {"path": "experiments/e2.py"})
        check(refused.is_error, "the corner rule did not refuse corner 0.01 with aspect 1.75")
        print("refusal:", text(refused))
        # A refusal uses no budget: a verdict-free state would refuse the next call, so the budget is read
        # from the next accepted answer, the end of the session, below.
        ended = await client.call_tool("end_session", {})
        check(not ended.is_error, f"end_session refused: {text(ended)}")
        print("end_session:", text(ended))
        check(json.loads(text(ended)).get("budget_remaining") == 22, "the refusal used budget")


def main() -> int:
    root = REPO / "bench-run/wind-tunnel/rehearsal" / time.strftime("run-%Y%m%d-%H%M%S")
    lab, state, sessions = root / "lab", root / "state", root / "sessions"
    for folder in (lab, state, sessions):
        folder.mkdir(parents=True)
    config = root / f"{SESSION_ID}.toml"
    run(["bench-make-lab", str(lab)])
    run(
        [
            "bench-new-session", "--application", "wind-tunnel",
            "--adapter", "wind_tunnel.adapter:WindAdapter",
            "--scan-sources", str(SCAN_SOURCES), "--stop-list", str(STOP_LIST), "--lab", str(lab),
            "--state", str(state), "--sessions", str(sessions), "--session-id", SESSION_ID,
            "--seed", str(SEED), "--config-out", str(config),
        ]
    )  # fmt: skip
    requirements = lab / ".kiro/specs/lab/requirements.md"
    requirements.write_text(
        requirements.read_text(encoding="utf-8") + "\n" + hypothesis_block(), encoding="utf-8"
    )
    # The table must agree with the record for end_session to be accepted (an observed rule cites no miss).
    design = lab / ".kiro/specs/lab/design.md"
    row = "| R1 | rehearsal rule | the two tried settings | E1 | H1.P1, H1.P2 | observed | |\n"
    design.write_text(design.read_text(encoding="utf-8").rstrip("\n") + "\n" + row, encoding="utf-8")
    try:
        anyio.run(drive, lab, config)
    except BaseExceptionGroup as group:  # the SDK wraps an error of the rehearsal in task-group groups
        errors = group.exceptions
        while len(errors) == 1 and isinstance(errors[0], BaseExceptionGroup):
            errors = errors[0].exceptions
        if len(errors) == 1:
            raise errors[0] from None
        raise
    sealed = sessions / "wind-tunnel" / SESSION_ID
    check(sealed.is_dir(), f"no sealed folder {sealed}")
    print(run(["bench-verify", str(sealed)]).strip())
    print(
        run(
            ["bench-scan", "--config", str(SCAN_SOURCES), "--stop-list", str(STOP_LIST), str(sealed)]
        ).strip()
    )  # fmt: skip
    print(f"rehearsal passed; folder {root}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RehearsalError as error:
        print(f"rehearsal failed: {error}", file=sys.stderr)
        sys.exit(1)
