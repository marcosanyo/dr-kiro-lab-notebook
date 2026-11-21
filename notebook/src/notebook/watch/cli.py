"""The command line `notebook-watch` (Requirement 23; design "Command line of the watch", N33).

Every option is required and has no default, except the two that turn on a part: `--replay SECONDS` shows a
sealed record one entry at a time (23.17) and `--site` names a built site whose page of this session is linked
after the seal (23.16). `--scan-config` and `--app` are given at least once (`--app` names an application's
notebook folder, as for the build). There is no `--out`, no `--choices` and no host option: the watch writes
nothing and binds 127.0.0.1 only. Usage errors exit 2 before
anything is read; a failed check prints `notebook-watch: <where>: <problem>` and exits 1.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from bench.record.chain import LOG_NAME

from notebook import layouts, scan, words
from notebook.build import ASSETS, commentary_strings
from notebook.choices import App, read_app
from notebook.errors import NotebookError
from notebook.pages import legend
from notebook.watch import serve
from notebook.watch.versions import Watch

PROG = "notebook-watch"
USAGE_EXIT = 2
CHECK_EXIT = 1
PORT_MAX = 65535


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(USAGE_EXIT, f"{PROG}: arguments: {message}\n")


@dataclass(frozen=True)
class WatchInputs:
    """The watch's inputs, exactly as given on the command line. No field has a default."""

    record: Path
    state: Path
    layouts: Path
    words: Path
    scan_configs: tuple[Path, ...]
    stop_list: Path
    port: int
    apps: tuple[Path, ...]
    replay: float | None = None  # seconds between entries of a sealed record (23.15); None: the live record
    site: Path | None = None  # a built site that may hold the session's finished page (23.14)


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=PROG, description="Show one session at the bench on 127.0.0.1.")
    parser.add_argument("--record", required=True, type=Path, help="the record folder, <state>/<session-id>")
    parser.add_argument("--state", required=True, type=Path, help="the bench state folder")
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
    parser.add_argument("--port", required=True, type=int, help="the port on 127.0.0.1")
    parser.add_argument(
        "--app",
        required=True,
        action="append",
        type=Path,
        dest="apps",
        help="an application's notebook folder (holding app.toml), as for the build; one per application",
    )
    parser.add_argument(
        "--replay",
        type=float,
        help="show a sealed record one entry every SECONDS, labelled as a replay (optional)",
    )
    parser.add_argument(
        "--site", type=Path, help="a built site (notebook-build --out); links the finished page (optional)"
    )
    return parser


def parse(argv: list[str]) -> WatchInputs:
    """Parse the arguments. Reads no file; a missing option exits 2 naming it."""
    args = _parser().parse_args(argv)
    if not 0 <= args.port <= PORT_MAX:
        _parser().error(f"--port must be from 0 to {PORT_MAX}")
    return WatchInputs(
        args.record,
        args.state,
        args.layouts,
        args.words,
        tuple(args.scan_configs),
        args.stop_list,
        args.port,
        tuple(args.apps),
        args.replay,
        args.site,
    )


def check_record(inputs: WatchInputs) -> tuple[str, str]:
    """The record folder must lie directly under the state folder, and the session of its first entry must be
    its name. Returns (application, session) of the start entry."""
    record, state = inputs.record.resolve(), inputs.state.resolve()
    if record.parent != state:
        raise NotebookError(
            "--record", f"{inputs.record} is not a folder directly under --state {inputs.state}"
        )
    log = record / LOG_NAME
    if not log.is_file():
        raise NotebookError("--record", f"{inputs.record} has no {LOG_NAME}")
    with log.open("rb") as handle:
        first = handle.readline()
    if not first.endswith(b"\n"):
        raise NotebookError(LOG_NAME, "the first entry is not complete yet")
    try:
        body = json.loads(first)["body"]
        application, session = body["application"], body["session"]
    except (ValueError, KeyError, TypeError) as error:
        raise NotebookError(f"{LOG_NAME} line 1", "is not a start entry") from error
    if session != record.name:
        raise NotebookError(
            f"{LOG_NAME} line 1", f"the session {session!r} is not the folder name {record.name!r}"
        )
    return application, session


def pick_app(folders: Sequence[Path], application: str) -> App:
    found = [app for app in (read_app(f) for f in folders) if app.application == application]
    if len(found) != 1:
        raise NotebookError("--app", f"no single settings file for the application {application!r}")
    return found[0]


def prepare(inputs: WatchInputs, *, allow_fake: bool = False) -> serve.Server:
    """Check every input, make the watch and the server (the first pass is done, nothing is served yet).
    The command line passes `allow_fake=False`; only the Python API of the tests may pass True."""
    application, _ = check_record(inputs)
    scanner = scan.load(inputs.scan_configs, inputs.stop_list)
    table = layouts.load(inputs.layouts)
    word_list = words.load(inputs.words)
    for source, value in commentary_strings():
        word_list.check(value, source)
    app = pick_app(inputs.apps, application)
    page = scan.check(scanner, {"legend.html": legend.legend(app)})["legend.html"][0]
    static = serve.load_assets(ASSETS)
    static["/legend.html"] = (page.encode("utf-8"), serve.HTML)
    finished = None
    if inputs.site is not None:
        if not (inputs.site / "index.html").is_file():
            raise NotebookError(
                "--site", f"{inputs.site} has no index.html; give the folder notebook-build wrote"
            )
        if (inputs.site / app.slug / f"{inputs.record.name}.html").is_file():
            finished = f"{serve.SITE}{app.slug}/{inputs.record.name}.html"
    watch = Watch(
        inputs.record, app, table, scanner, allow_fake=allow_fake, replay=inputs.replay, finished=finished
    )
    return serve.Server(watch, static, inputs.port, inputs.site)


def main(argv: list[str] | None = None) -> int:
    inputs = parse(sys.argv[1:] if argv is None else argv)
    try:
        server = prepare(inputs)
        print(f"{PROG}: http://{serve.HOST}:{server.port}/", file=sys.stderr)
        try:
            server.run()
        except KeyboardInterrupt:
            server.close()
    except NotebookError as error:
        print(f"{PROG}: {error.where}: {error.problem}", file=sys.stderr)
        return CHECK_EXIT
    return 0
