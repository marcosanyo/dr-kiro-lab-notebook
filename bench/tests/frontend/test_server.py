"""Task 17: the MCP server through the SDK's in-process client, with the fake application (design F11)."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import anyio
import pytest
from mcp.client import Client

from bench.frontend import config as config_file
from bench.frontend.server import TOOLS, BenchServer, open_session, startup_log_for
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
    assert "Goal (for the best point): Make distance as large as possible." in run
    assert "How it is measured: Computed by the fake application" in run


@pytest.mark.parametrize(
    ("setting", "end_session"),
    [
        (
            "required",
            "End the session. Every experiment needs a verdict, and your design.md must end with a "
            "Discovered spec table that agrees with the record.",
        ),
        ("not-required", "End the session. Every experiment needs a verdict."),
    ],
)
def test_end_session_text_follows_the_discovered_table_setting(
    lab: Lab, setting: str, end_session: str
) -> None:
    srv = BenchServer(lab.start(discovered_table=setting))

    async def main() -> dict[str, str]:
        async with Client(srv.mcp) as client:
            return {t.name: t.description or "" for t in (await client.list_tools()).tools}

    assert anyio.run(main)["end_session"] == end_session


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
        "discovered_table": "required",
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


@pytest.mark.parametrize(
    "field", ["resume", "stop_list", "sessions_dir", "application", "seed", "discovered_table"]
)
def test_config_file_missing_field(lab: Lab, tmp_path: Path, field: str) -> None:
    with pytest.raises(config_file.ConfigError, match=f"missing field.*{field}"):
        config_file.load(_config_file(lab, tmp_path, **{field: None}))


def test_config_file_discovered_table_must_be_a_string(lab: Lab, tmp_path: Path) -> None:
    with pytest.raises(config_file.ConfigError, match="discovered_table must be a string"):
        config_file.load(_config_file(lab, tmp_path, discovered_table=1))


def test_config_file_passes_the_discovered_table_setting_on(lab: Lab, tmp_path: Path) -> None:
    config = config_file.load(_config_file(lab, tmp_path, discovered_table="not-required"))
    assert config.session.discovered_table == "not-required"


HOLD_LOCK = (
    "import sys; from pathlib import Path; from bench.record.store import Store; "
    "store = Store.open(Path(sys.argv[1])); print('locked', flush=True); sys.stdin.read(); store.close()"
)
RUN_MAIN = "import sys; from bench.frontend.server import main; sys.exit(main())"


def test_state_folder_in_use_by_a_live_process_stops_with_a_bench_line(lab: Lab, tmp_path: Path) -> None:
    open_session(config_file.load(_config_file(lab, tmp_path))).close()  # creates state/s2, releases its lock
    resumed = _config_file(lab, tmp_path, resume=True)
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_LOCK, str(lab.root / "state" / "s2")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == "locked"
        env = {**os.environ, config_file.ENV_VAR: str(resumed)}
        done = subprocess.run(
            [sys.executable, "-c", RUN_MAIN],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    finally:
        assert holder.stdin is not None
        holder.stdin.close()
        holder.wait(timeout=60)
    assert done.returncode == 2
    assert "Traceback" not in done.stderr
    (line,) = done.stderr.splitlines()
    assert line.startswith("bench-mcp: the session s2 is in use by another process")
    assert "stop that process or wait for it to finish" in line
    assert str(lab.root) not in line
    assert str(lab.root / "state") not in line
    assert "/" not in line


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


def _run_bench_mcp(config: Path | None) -> subprocess.Popen[str]:
    env = {k: v for k, v in os.environ.items() if k != config_file.ENV_VAR}
    if config is not None:
        env[config_file.ENV_VAR] = str(config)
    return subprocess.Popen(
        [sys.executable, "-c", RUN_MAIN],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _log_entries(log: Path) -> list[tuple[datetime, int, str]]:
    """Each entry's (UTC time, process id, first line of the message), as the startup log writes them."""
    entries = []
    for line in log.read_text(encoding="utf-8").splitlines():
        if line[:1].isdigit():
            stamp, pid, message = line.split(" ", 2)
            entries.append((datetime.fromisoformat(stamp), int(pid.removeprefix("pid=")), message))
    return entries


def test_startup_log_is_next_to_the_config_and_named_by_its_stem(tmp_path: Path) -> None:
    assert startup_log_for(None) is None
    assert startup_log_for(str(tmp_path / "missing" / "run-1.session.toml")) is None
    assert startup_log_for(str(tmp_path / "run-1.session.toml")) == tmp_path / "run-1.mcp-startup.log"
    assert startup_log_for(str(tmp_path / "session.toml")) == tmp_path / "session.mcp-startup.log"


def test_missing_config_file_logs_one_line_and_stderr_has_no_path(tmp_path: Path) -> None:
    config = tmp_path / "run-1.session.toml"
    log = tmp_path / "run-1.mcp-startup.log"
    pids = []
    for attempt in (1, 2):
        proc = _run_bench_mcp(config)
        _, err = proc.communicate(timeout=60)
        pids.append(proc.pid)
        assert proc.returncode == 2
        (line,) = err.splitlines()
        assert line == "bench-mcp: session config: file not found"
        assert str(tmp_path) not in err
        assert len(_log_entries(log)) == attempt  # appended, not overwritten
    first, second = _log_entries(log)
    assert first[0].utcoffset() == timedelta(0)  # UTC
    assert (first[1], second[1]) == tuple(pids)
    assert first[2] == second[2] == "session config: file not found"
    assert "Traceback" not in log.read_text(encoding="utf-8")


def test_unreadable_toml_is_logged_and_stderr_stays_path_free(tmp_path: Path) -> None:
    config = tmp_path / "run-2.session.toml"
    config.write_text("session_id = \n", encoding="utf-8")
    proc = _run_bench_mcp(config)
    _, err = proc.communicate(timeout=60)
    assert proc.returncode == 2 and str(tmp_path) not in err
    (entry,) = _log_entries(tmp_path / "run-2.mcp-startup.log")
    assert entry[2].startswith("session config: not valid TOML (")


def test_unknown_adapter_module_is_logged(lab: Lab, tmp_path: Path) -> None:
    config = _config_file(lab, tmp_path, adapter="no_such_module_for_bench_tests:Factory")
    proc = _run_bench_mcp(config)
    _, err = proc.communicate(timeout=60)
    assert proc.returncode == 2
    assert err.splitlines() == [
        "bench-mcp: session config: cannot import adapter module no_such_module_for_bench_tests "
        "(No module named 'no_such_module_for_bench_tests')"
    ]
    assert str(lab.root) not in err
    (entry,) = _log_entries(tmp_path / "session.mcp-startup.log")
    assert entry[2].startswith("session config: cannot import adapter module no_such_module_for_bench_tests")


def test_unexpected_error_is_logged_with_traceback_and_still_raised(lab: Lab, tmp_path: Path) -> None:
    # json:loads is callable, so the config loads; calling it with no argument raises TypeError at start.
    config = _config_file(lab, tmp_path, adapter="json:loads")
    proc = _run_bench_mcp(config)
    _, err = proc.communicate(timeout=60)
    assert proc.returncode == 1
    assert "Traceback" in err  # as before this change, the traceback still goes to stderr
    text = (tmp_path / "session.mcp-startup.log").read_text(encoding="utf-8")
    assert text.splitlines()[0].split(" ", 2)[2].startswith("unexpected TypeError: ")
    assert "Traceback (most recent call last)" in text and "TypeError" in text


def test_state_folder_in_use_is_logged(lab: Lab, tmp_path: Path) -> None:
    open_session(config_file.load(_config_file(lab, tmp_path))).close()
    resumed = _config_file(lab, tmp_path, resume=True)
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD_LOCK, str(lab.root / "state" / "s2")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline().strip() == "locked"
        proc = _run_bench_mcp(resumed)
        _, err = proc.communicate(timeout=60)
    finally:
        assert holder.stdin is not None
        holder.stdin.close()
        holder.wait(timeout=60)
    assert proc.returncode == 2 and str(lab.root) not in err
    (entry,) = _log_entries(tmp_path / "session.mcp-startup.log")
    assert entry[2].startswith("the session s2 is in use by another process")


def test_a_normal_start_writes_no_startup_log(lab: Lab, tmp_path: Path) -> None:
    proc = _run_bench_mcp(_config_file(lab, tmp_path))
    _, err = proc.communicate(timeout=60)
    assert proc.returncode == 0, err
    assert not (tmp_path / "session.mcp-startup.log").exists()
