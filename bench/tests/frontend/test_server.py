"""Task 17: the MCP server through the SDK's in-process client, with the fake application (design F11)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from mcp.client import Client

from bench.frontend import config as config_file
from bench.frontend.server import TOOLS, BenchServer, open_session
from labkit import FAKE_SOURCES, STOP_LIST, Lab, exp_file, hyp_block

STATEMENT = "WHEN amp rises, THE distance SHALL rise."
P1 = {"id": "P1", "range": [0.4, 0.6], "when": {"amp": 0.5, "gain": 1.0}}


def server(lab: Lab) -> BenchServer:
    return BenchServer(lab.start())


def call(srv: BenchServer, *calls: tuple[str, dict]) -> list:
    results: list = []

    async def main() -> None:
        async with Client(srv.mcp) as client:
            for name, args in calls:
                results.append(await client.call_tool(name, args))

    anyio.run(main)
    return results


def text(result) -> str:  # type: ignore[no-untyped-def]
    (content,) = result.content
    return content.text


def test_four_tools_and_no_start_or_stop(lab: Lab) -> None:
    srv = server(lab)

    async def main() -> list[str]:
        async with Client(srv.mcp) as client:
            return [t.name for t in (await client.list_tools()).tools]

    names = anyio.run(main)
    assert sorted(names) == sorted(TOOLS)
    assert not {"start", "stop", "start_session", "stop_session"} & set(names)


def test_descriptions_come_from_the_declaration(lab: Lab) -> None:
    srv = server(lab)

    async def main() -> dict[str, str]:
        async with Client(srv.mcp) as client:
            return {t.name: t.description or "" for t in (await client.list_tools()).tools}

    descriptions = anyio.run(main)
    run = descriptions["run_experiment"]
    assert (
        "drive" in run and "gain" in run and "[0.0, 3.0]" in run and "lost" in run and "budget is 12" in run
    )


def test_run_result_has_measurements_paths_and_no_image(lab: Lab) -> None:
    srv = server(lab)
    lab.add(hyp_block("H1", STATEMENT, P1))
    path = lab.experiment("e1.py", exp_file("H1", [[0.5, 1.0], [0.25, 2.75]]))
    registered, ran = call(srv, ("register_hypothesis", {"id": "H1"}), ("run_experiment", {"path": path}))
    assert not registered.is_error and json.loads(text(registered)) == {"budget_remaining": 12}
    assert not ran.is_error and all(c.type == "text" for c in ran.content)
    data = json.loads(text(ran))
    assert data["experiment"] == "E1" and data["budget_remaining"] == 10
    first, second = data["trials"]
    assert first["trial"] == "T1" and first["picture"] == "pictures/E1-T1.png"
    assert set(first["measurements"]) == {"distance", "turn", "trace"} and first["not_measured"] == {}
    assert second["not_measured"] == {
        "turn": {"outcome": "lost", "reason": "the fake tracker lost the target"}
    }
    assert "turn" not in second["measurements"]
    assert (lab.lab / first["picture"]).read_bytes().startswith(b"\x89PNG")


def test_refusal_is_a_tool_error_with_the_core_text(lab: Lab) -> None:
    srv = server(lab)
    (result,) = call(srv, ("register_hypothesis", {"id": "H7"}))
    assert result.is_error
    assert text(result).startswith("hypothesis H7 is not in .kiro/specs/lab/requirements.md")


def test_bench_failure_is_a_tool_error_and_later_calls_are_refused(lab: Lab) -> None:
    srv = server(lab)
    lab.add(hyp_block("H1", STATEMENT, P1))
    path = lab.experiment("e1.py", exp_file("H1", [[0.5, 0.125]]))
    _, failed, later = call(
        srv,
        ("register_hypothesis", {"id": "H1"}),
        ("run_experiment", {"path": path}),
        ("end_session", {}),
    )
    assert failed.is_error and text(failed) == "the trial did not complete"
    assert later.is_error and text(later) == "the session has ended; no further actions are accepted"


def test_parallel_runs_give_one_ran_and_one_refused(lab: Lab) -> None:
    srv = server(lab)
    lab.add(hyp_block("H1", STATEMENT, P1))
    a = lab.experiment("a.py", exp_file("H1", [[0.5, 1.0]]))
    b = lab.experiment("b.py", exp_file("H1", [[0.25, 1.0]]))
    results: list = []

    async def main() -> None:
        async with Client(srv.mcp) as client:
            await client.call_tool("register_hypothesis", {"id": "H1"})
            async with anyio.create_task_group() as group:
                for path in (a, b):
                    group.start_soon(lambda p=path: _append(client, p))

    async def _append(client: Client, path: str) -> None:
        results.append(await client.call_tool("run_experiment", {"path": path}))

    anyio.run(main)
    assert sorted(r.is_error for r in results) == [False, True]
    refused = next(r for r in results if r.is_error)
    assert text(refused) == "E1 needs a verdict before the next experiment runs"
    assert srv.session.state.remaining == 11


def _config_file(lab: Lab, tmp: Path, **changes: object) -> Path:
    values = {
        "session_id": "s2",
        "application": "fake",
        "adapter": "bench.fake.adapter:FakeAdapter",
        "lab_dir": str(lab.lab),
        "spec_files": list(lab.config.spec_files),
        "experiments_dir": "experiments",
        "state_dir": str(lab.root / "state"),
        "sessions_dir": str(lab.root / "sessions"),
        "seed": 3,
        "scan_sources": [str(FAKE_SOURCES)],
        "stop_list": str(STOP_LIST),
        "resume": False,
    }
    values.update(changes)
    lines = []
    for key, value in values.items():
        if value is None:
            continue
        lines.append(f"{key} = {json.dumps(value)}")
    path = tmp / "session.toml"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_config_file_starts_and_resumes(lab: Lab, tmp_path: Path) -> None:
    session = open_session(config_file.load(_config_file(lab, tmp_path)))
    assert session.config.session_id == "s2" and session.state.budget == 12
    session.close()
    resumed = open_session(config_file.load(_config_file(lab, tmp_path, resume=True)))
    assert resumed.state.budget == 12
    resumed.close()


@pytest.mark.parametrize("field", ["resume", "stop_list", "sessions_dir", "application", "seed"])
def test_config_file_missing_field(lab: Lab, tmp_path: Path, field: str) -> None:
    with pytest.raises(config_file.ConfigError, match=f"missing field.*{field}"):
        config_file.load(_config_file(lab, tmp_path, **{field: None}))


def test_missing_session_config_variable_stops_the_server() -> None:
    env = {k: v for k, v in os.environ.items() if k != config_file.ENV_VAR}
    done = subprocess.run(
        [sys.executable, "-c", "import sys; from bench.frontend.server import main; sys.exit(main())"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        stdin=subprocess.DEVNULL,
    )
    assert done.returncode == 2
    assert "BENCH_SESSION_CONFIG is not set" in done.stderr
