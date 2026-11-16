"""The command line `notebook-build`, the only entry point (design "Command line").

Every option is required and has no default. Usage errors exit 2 before anything is read; a failed check
prints `notebook-build: <where>: <problem>` and exits 1.
"""

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from notebook.errors import NotebookError
from notebook.inputs import Inputs, check_out

PROG = "notebook-build"
USAGE_EXIT = 2
CHECK_EXIT = 1


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(USAGE_EXIT, f"{PROG}: arguments: {message}\n")


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=PROG, description="Build the lab notebook from the sealed session records.")
    parser.add_argument("--sessions", required=True, type=Path, help="the folder of sealed records")
    parser.add_argument("--choices", required=True, type=Path, help="the choice files and cover.toml")
    parser.add_argument("--layouts", required=True, type=Path, help="the frame layout table")
    parser.add_argument("--words", required=True, type=Path, help="the commentary word list")
    parser.add_argument(
        "--scan-config",
        required=True,
        action="append",
        type=Path,
        dest="scan_configs",
        help="an application's scan_sources.toml; give one per application",
    )
    parser.add_argument("--stop-list", required=True, type=Path, help="the reviewed stop list")
    parser.add_argument("--out", required=True, type=Path, help="the output folder: absent or empty")
    return parser


def parse(argv: list[str]) -> Inputs:
    """Parse the arguments. Reads no file; a missing option exits 2 naming it."""
    args = _parser().parse_args(argv)
    return Inputs(
        sessions=args.sessions,
        choices=args.choices,
        layouts=args.layouts,
        words=args.words,
        scan_configs=tuple(args.scan_configs),
        stop_list=args.stop_list,
        out=args.out,
    )


def run(inputs: Inputs) -> None:
    """Run the build. The phases (design "Overview") are written in later tasks; until then this fails."""
    check_out(inputs.out)
    raise NotebookError(PROG, "the build phases are not written yet (lab-notebook task 9.2)")


def main(argv: list[str] | None = None) -> int:
    inputs = parse(sys.argv[1:] if argv is None else argv)
    try:
        run(inputs)
    except NotebookError as error:
        print(f"{PROG}: {error.where}: {error.problem}", file=sys.stderr)
        return CHECK_EXIT
    return 0
