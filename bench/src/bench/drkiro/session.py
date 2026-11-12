"""The `bench-new-session` command (dr-kiro Requirements 5.2, 5.3, design 7.2).

Starts a fresh session in a lab: checks that no earlier session is still open, removes Dr. Kiro's files of the
previous session (the sealed record holds them), writes the templates, starts the session with the core, and
writes the session config with `resume = true`, so that `bench-mcp` always reopens the session it is given.
Every argument is required. Nothing is changed before the checks pass.
"""

import argparse
import importlib
import json
import os
import shutil
import sys
from importlib import resources
from pathlib import Path

from bench.core.outcome import Ran
from bench.core.session import Session, SessionConfig
from bench.drkiro.lab import BUILDER_FILES, TEMPLATES
from bench.record.chain import VerifyError, verify

FILES = resources.files("bench.drkiro") / "files"
SPEC_FILES = tuple(TEMPLATES.values())
EXPERIMENTS = "experiments"
PICTURES = "pictures"


class NewSessionError(Exception):
    """The session cannot be started. The message says why."""


def _adapter(spec: str) -> object:
    module_name, sep, attribute = spec.partition(":")
    if not sep or not module_name or not attribute:
        raise NewSessionError(f"adapter must be 'module:factory', got {spec!r}")
    try:
        factory = getattr(importlib.import_module(module_name), attribute)
    except (ImportError, AttributeError) as error:
        raise NewSessionError(f"cannot load adapter {spec}: {error}") from error
    return factory()


def open_sessions(state: Path) -> list[str]:
    """Session folders in the state folder whose record does not end with a seal."""
    found = []
    for folder in sorted(p for p in state.iterdir() if p.is_dir()):
        try:
            entries = verify(folder, sealed=False)
        except VerifyError as error:
            raise NewSessionError(f"session {folder.name}: the record does not verify ({error})") from error
        if not entries or entries[-1]["kind"] != "seal":
            found.append(folder.name)
    return found


def _clear(folder: Path) -> None:
    if not folder.exists():
        folder.mkdir()
        return
    for child in folder.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()


def _relative(path: Path, base: Path) -> str:
    return os.path.relpath(path.resolve(), base.resolve())


def new_session(args: argparse.Namespace) -> Path:
    lab, state, sessions = Path(args.lab), Path(args.state), Path(args.sessions)
    config_out = Path(args.config_out)
    # Checks: nothing is changed before all of them pass.
    missing = [target for target in BUILDER_FILES.values() if not (lab / target).is_file()]
    if missing:
        raise NewSessionError(f"{lab} has no builder files ({', '.join(missing)}); run bench-make-lab first")
    for name, folder in (("state", state), ("sessions", sessions)):
        if not folder.is_dir():
            raise NewSessionError(f"the {name} folder {folder} does not exist")
    still_open = open_sessions(state)
    if still_open:
        raise NewSessionError(
            f"session {', '.join(still_open)} is not sealed; end it or run bench-stop first"
        )
    if config_out.exists():
        raise NewSessionError(f"{config_out} already exists; a session id is used once")
    if not config_out.parent.is_dir():
        raise NewSessionError(f"the folder of {config_out} does not exist")
    adapter = _adapter(args.adapter)
    # Reset Dr. Kiro's files and write the templates.
    _clear(lab / EXPERIMENTS)
    _clear(lab / PICTURES)
    for source, target in TEMPLATES.items():
        path = lab / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((FILES / source).read_bytes())
    config = SessionConfig(
        session_id=args.session_id,
        application=args.application,
        adapter=adapter,  # type: ignore[arg-type]
        lab_dir=lab,
        spec_files=SPEC_FILES,  # type: ignore[arg-type]
        experiments_dir=EXPERIMENTS,
        state_dir=state,
        sessions_dir=sessions,
        seed=args.seed,
        scan_sources=(Path(args.scan_sources),),
        stop_list=Path(args.stop_list),
    )
    outcome = Session.start(config)
    if not isinstance(outcome, Ran):
        raise NewSessionError(outcome.message.plain())
    outcome.result.close()
    base = config_out.parent
    values = {
        "session_id": args.session_id,
        "application": args.application,
        "adapter": args.adapter,
        "lab_dir": _relative(lab, base),
        "spec_files": list(SPEC_FILES),
        "experiments_dir": EXPERIMENTS,
        "state_dir": _relative(state, base),
        "sessions_dir": _relative(sessions, base),
        "seed": args.seed,
        "scan_sources": [_relative(Path(args.scan_sources), base)],
        "stop_list": _relative(Path(args.stop_list), base),
        "resume": True,
    }
    config_out.write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in values.items()), encoding="utf-8")
    return config_out


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bench-new-session", description="Start a fresh session in a lab.")
    for name in (
        "application",
        "adapter",
        "scan-sources",
        "stop-list",
        "lab",
        "state",
        "sessions",
        "session-id",
    ):
        p.add_argument(f"--{name}", required=True)
    p.add_argument("--seed", required=True, type=int)
    p.add_argument("--config-out", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(sys.argv[1:] if argv is None else argv)
    try:
        path = new_session(args)
    except NewSessionError as error:
        print(f"bench-new-session: {error}", file=sys.stderr)
        return 2
    print(f"bench-new-session: session {args.session_id} is open; config at {path}")
    return 0
