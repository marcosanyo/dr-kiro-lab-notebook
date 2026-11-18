"""The `bench` MCP server and the `bench-mcp` command (Requirement 17.1-17.5, 17.17-17.20, design F3, F6, F7).

Four tools, one fair lock. Every handler takes the lock first, then runs the core call (and the rendering,
which writes the picture files) in a worker thread, so the event loop stays free during a long run. The
worker thread is not abandoned if the client cancels: the run finishes and is recorded. The front end adds
no gate and builds no message text of its own.
"""

import os
import sys
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import anyio
import anyio.to_thread
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult

from bench.core.outcome import Outcome, Ran
from bench.core.session import Session, SessionError
from bench.frontend import config as config_file
from bench.frontend.describe import descriptions
from bench.frontend.pictures import NOT_DELIVERED, PictureWriteError, PictureWriter
from bench.frontend.render import render
from bench.record.store import StoreInUseError

TOOLS = ("register_hypothesis", "run_experiment", "record_verdict", "end_session")
CONFIG_SUFFIX = ".session.toml"
STARTUP_LOG_SUFFIX = ".mcp-startup.log"


class StartupError(Exception):
    """The server cannot start. The message says why."""


class BenchServer:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.lock = anyio.Lock()
        self.write_picture = PictureWriter(session.config.lab_dir)
        texts = descriptions(session.declaration, session.config.discovered_table)
        findings = [
            f for name, text in texts.items() for f in session.scanner.scan_text(text, "builder", name)
        ]
        if findings:
            raise StartupError("tool descriptions fail the blind scan: " + "; ".join(map(str, findings)))
        self.mcp = MCPServer("bench")

        async def register_hypothesis(id: str) -> CallToolResult:
            return await self._call(lambda: self.session.register(id))

        async def run_experiment(path: str) -> CallToolResult:
            return await self._call(lambda: self.session.run(path))

        async def record_verdict(experiment: str, verdict: str, words: str) -> CallToolResult:
            return await self._call(lambda: self.session.verdict(experiment, verdict, words))

        async def end_session() -> CallToolResult:
            return await self._call(self.session.end)

        for fn in (register_hypothesis, run_experiment, record_verdict, end_session):
            self.mcp.add_tool(fn, name=fn.__name__, description=texts[fn.__name__], structured_output=False)

    async def _call(self, action: Callable[[], Outcome]) -> CallToolResult:
        async with self.lock:
            return await anyio.to_thread.run_sync(lambda: self._apply(action))

    def _apply(self, action: Callable[[], Outcome]) -> CallToolResult:
        outcome = action()
        try:
            return render(outcome, self.write_picture)
        except PictureWriteError as error:
            # A picture that cannot be written is a bench failure, recorded as any other (17.15, design F5).
            return render(self.session.fail("run", NOT_DELIVERED, error.detail), self.write_picture)

    def close(self) -> None:
        self.session.close()


def open_session(cfg: config_file.ServerConfig) -> Session:
    if cfg.resume:
        try:
            return Session.open(cfg.session)
        except SessionError as error:
            raise StartupError(f"cannot reopen the session: {error}") from error
        except StoreInUseError as error:
            # No file path here: this line may reach the reader's Kiro log (rules.md 1).
            raise StartupError(
                f"the session {cfg.session.session_id} is in use by another process; "
                f"stop that process or wait for it to finish"
            ) from error
    outcome = Session.start(cfg.session)
    if not isinstance(outcome, Ran):
        raise StartupError(f"cannot start the session: {outcome.message.plain()}")
    return outcome.result


def startup_log_for(config_value: str | None) -> Path | None:
    """The builder-side startup log next to the session config, `<stem>.mcp-startup.log`.

    None when the config path is not known from the environment or its folder does not exist: then only
    stderr is written. The stem drops `.session.toml`, so the log of run `<run-id>` is
    `<run-id>.mcp-startup.log`.
    """
    if not config_value:
        return None
    config = Path(config_value)
    if not config.parent.is_dir():
        return None
    name = config.name
    stem = name.removesuffix(CONFIG_SUFFIX) if name.endswith(CONFIG_SUFFIX) else config.stem
    return config.parent / f"{stem}{STARTUP_LOG_SUFFIX}"


def record_startup_failure(log: Path | None, message: str, traceback_text: str | None = None) -> None:
    """Append one entry: UTC time, process id, the message in full, and the traceback if there is one."""
    if log is None:
        return
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    entry = f"{stamp} pid={os.getpid()} {message}\n"
    if traceback_text:
        entry += traceback_text if traceback_text.endswith("\n") else traceback_text + "\n"
    with log.open("a", encoding="utf-8") as file:
        file.write(entry)


def main() -> int:
    log = startup_log_for(os.environ.get(config_file.ENV_VAR))
    try:
        server = BenchServer(open_session(config_file.from_environment()))
    except (config_file.ConfigError, StartupError) as error:
        record_startup_failure(log, str(error))
        print(f"bench-mcp: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        # Not swallowed: the error is logged with its traceback, then raised as before (exit code 1).
        message = f"unexpected {type(error).__name__}: {error}"
        record_startup_failure(log, message, traceback.format_exc())
        raise
    try:
        server.mcp.run("stdio")
    finally:
        server.close()
    return 0
