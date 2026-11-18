"""The builder-side startup log of `bench-mcp` (commit 1c20586, design K33).

Kept apart from the server module, which imports the MCP SDK. The launcher (`bench.frontend.launch`) must
write this log even when that import fails. Nothing here imports the SDK.
"""

import os
from datetime import UTC, datetime
from pathlib import Path

CONFIG_SUFFIX = ".session.toml"
STARTUP_LOG_SUFFIX = ".mcp-startup.log"


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
