"""The `bench` MCP server and the `bench-mcp` command (Requirement 17.1-17.5, 17.17-17.20, design F3, F6, F7).
Four tools, one fair lock. Every handler takes the lock first, then runs the core call (and the rendering,
which writes the picture files) in a worker thread, so the event loop stays free during a long run. The
worker thread is not abandoned if the client cancels: the run finishes and is recorded. The front end adds
no gate and builds no message text of its own.

The server follows the lab's session file (`bench.frontend.pointer`) on every call, not only at start. When a
new session has been started in the lab (`bench-new-session` writes a new config and names it in the file),
the next call closes the sealed session and opens the new one, so Kiro does not have to restart. A session
that is still open is never replaced: the call is refused until the session is sealed.
"""

import sys
import traceback
from collections.abc import Callable
from pathlib import Path

import anyio
import anyio.to_thread
from mcp.server.mcpserver import MCPServer
from mcp_types import CallToolResult, TextContent

from bench.core.outcome import Outcome, Ran
from bench.core.session import Session, SessionError
from bench.frontend import config as config_file
from bench.frontend.describe import descriptions
from bench.frontend.pictures import NOT_DELIVERED, PictureWriteError, PictureWriter
from bench.frontend.render import render
from bench.frontend.startup_log import record_startup_failure, startup_log_for
from bench.record.store import StoreInUseError

TOOLS = ("register_hypothesis", "run_experiment", "record_verdict", "end_session")

# What Dr. Kiro sees when the server cannot switch to the lab's session. These name no path (rules.md 1); the
# detail goes to the builder-side startup log.
NO_SESSION_FILE = "no session is open in this lab; the builder has to start one"
STILL_OPEN = "the session is still open; no other session starts until it is sealed"
OTHER_APPLICATION = "the session the builder started belongs to another application; no session starts here"
CANNOT_OPEN = "the new session cannot be opened; the builder has to read the startup log"


class StartupError(Exception):
    """The server cannot start. The message says why."""


class SwitchError(Exception):
    """The server cannot move to the session the lab's session file names. The message is for Dr. Kiro."""


class BenchServer:
    def __init__(self, session: Session, lab: Path | None = None, key: str | None = None) -> None:
        """`lab` and `key` (from `config.key_for`) make the server follow the lab's session file. Without them
        the server keeps the one session it was given, which the tests use."""
        self.session = session
        self.application = session.config.application
        self.lab = None if lab is None else Path(lab).resolve()
        self._key = key
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
            return await self._call(lambda s: s.register(id))

        async def run_experiment(path: str) -> CallToolResult:
            return await self._call(lambda s: s.run(path))

        async def record_verdict(experiment: str, verdict: str, words: str) -> CallToolResult:
            return await self._call(lambda s: s.verdict(experiment, verdict, words))

        async def end_session() -> CallToolResult:
            return await self._call(lambda s: s.end())

        for fn in (register_hypothesis, run_experiment, record_verdict, end_session):
            self.mcp.add_tool(fn, name=fn.__name__, description=texts[fn.__name__], structured_output=False)

    async def _call(self, action: Callable[[Session], Outcome]) -> CallToolResult:
        async with self.lock:
            return await anyio.to_thread.run_sync(lambda: self._apply(action))

    def _apply(self, action: Callable[[Session], Outcome]) -> CallToolResult:
        try:
            session = self._current()
        except SwitchError as error:
            return CallToolResult(content=[TextContent(text=str(error))], is_error=True)
        outcome = action(session)
        try:
            return render(outcome, self.write_picture)
        except PictureWriteError as error:
            # A picture that cannot be written is a bench failure, recorded as any other (17.15, design F5).
            return render(session.fail("run", NOT_DELIVERED, error.detail), self.write_picture)

    def _current(self) -> Session:
        """The session the next call acts on. Called under the lock, in the worker thread."""
        if self.lab is None:
            return self.session
        try:
            path, key = config_file.key_for(self.lab)
        except config_file.ConfigError as error:
            raise self._refuse_switch(NO_SESSION_FILE, str(error), None) from error
        if key == self._key and self.session is not None:
            return self.session
        if self.session is not None and self.session.state.sealed is None:
            raise self._refuse_switch(
                STILL_OPEN, f"session {self.session.config.session_id} is open; the file names {path}", path
            )
        try:
            config = config_file.for_lab(self.lab)
        except config_file.ConfigError as error:
            raise self._refuse_switch(NO_SESSION_FILE, str(error), path) from error
        if config.session.application != self.application:
            raise self._refuse_switch(
                OTHER_APPLICATION,
                f"session {config.session.session_id} is for {config.session.application}, "
                f"this server runs {self.application}",
                path,
            )
        # Every check has passed: only now is the sealed session closed and the new one opened.
        if self.session is not None:
            self.session.close()
            self.session = None
        try:
            self.session = open_session(config)
        except StartupError as error:
            raise self._refuse_switch(CANNOT_OPEN, str(error), path) from error
        self._key = key
        return self.session

    @staticmethod
    def _refuse_switch(public: str, detail: str, path: Path | None) -> SwitchError:
        record_startup_failure(startup_log_for(None if path is None else str(path)), detail)
        return SwitchError(public)

    def close(self) -> None:
        if self.session is not None:
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


def _known_config(lab: Path) -> str | None:
    # Only to place the startup log; a missing session file is reported by `for_lab` just below.
    try:
        return str(config_file.config_path_for(lab))
    except config_file.ConfigError:
        return None


def main() -> int:
    lab = Path.cwd()
    log = startup_log_for(_known_config(lab))
    try:
        _, key = config_file.key_for(lab)
        server = BenchServer(open_session(config_file.for_lab(lab)), lab, key)
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
