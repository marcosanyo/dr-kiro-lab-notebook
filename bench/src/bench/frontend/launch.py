"""The `bench-mcp` command: a launcher in front of the bench MCP server (design K33).

`bench-mcp --check` imports the MCP parts and the server. It prints `bench-mcp: ready` and exits 0, or it
prints one bench line naming the module that cannot be imported and exits 2. The run script runs this check
before it creates anything (build-from-spec design 3.9, phase A).

Without `--check` the server starts as before (`server.main`). When the import of the server fails, one line
goes to the builder-side startup log, if the lab's session file names an existing config, and one bench line
goes to stderr. Errors other than an import failure are not caught here.
"""

import importlib
import sys
from pathlib import Path

from bench.frontend import config as config_file
from bench.frontend.startup_log import record_startup_failure, startup_log_for

CHECK = "--check"
READY = "bench-mcp: ready"
# What the server needs before it starts, in the order the check imports them.
PARTS = ("mcp", "anyio", "bench.frontend.server")


def _missing(error: ImportError) -> str:
    # The module name only: stderr may reach the reader's Kiro log, so it carries no path (rules.md 1).
    name = error.name or "an unknown module"
    return f"bench-mcp: cannot import module {name}; the bench front end needs it"


def check() -> int:
    for part in PARTS:
        try:
            importlib.import_module(part)
        except ImportError as error:
            print(_missing(error), file=sys.stderr)
            return 2
    print(READY)
    return 0


def start() -> int:
    # Only to place the startup log: the server itself reports a missing or unusable session file.
    try:
        config_path = config_file.config_path_for(Path.cwd())
    except config_file.ConfigError:
        config_path = None
    log = startup_log_for(str(config_path)) if config_path is not None and config_path.is_file() else None
    try:
        from bench.frontend import server
    except ImportError as error:
        record_startup_failure(log, f"cannot import the bench front end: {error}")
        print(_missing(error), file=sys.stderr)
        return 2
    return server.main()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == [CHECK]:
        return check()
    if args:
        print(f"bench-mcp: takes no arguments except {CHECK}", file=sys.stderr)
        return 2
    return start()


if __name__ == "__main__":
    raise SystemExit(main())
