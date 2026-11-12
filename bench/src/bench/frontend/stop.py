"""The `bench-stop` command (Requirements 11.4, 17.2, design F7).

    bench-stop <session config file> --reason <text>

Opens the session from its record and seals it as stopped, without the table check. This is the
builder's action; it is never a tool. It works only while `bench-mcp` is not running, because the server
holds the lock on the session's state folder. A session left open by a closed connection is stopped this way.
"""

import argparse
import sys
from pathlib import Path

from bench.core.outcome import Ran
from bench.core.session import Session, SessionError, StoreError
from bench.frontend import config as config_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench-stop", description="Seal an open session as stopped.")
    parser.add_argument("config", type=Path, help="the session config file")
    parser.add_argument("--reason", required=True, help="why the builder stops the session")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        session = Session.open(config_file.load(args.config).session)
    except (config_file.ConfigError, SessionError, StoreError) as error:
        print(f"bench-stop: {error}", file=sys.stderr)
        return 2
    try:
        outcome = session.stop(args.reason)
    finally:
        session.close()
    if isinstance(outcome, Ran):
        print(f"bench-stop: sealed as stopped at {session.sealed_path}")
        return 0
    print(f"bench-stop: {outcome.message.plain()}", file=sys.stderr)
    if session.last_failure_detail:
        print(f"bench-stop: {session.last_failure_detail}", file=sys.stderr)
    return 1
