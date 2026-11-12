"""Task 19: `bench-stop` (Requirements 11.4, 17.2, design F7)."""

import json
from pathlib import Path

import pytest

from bench.frontend.stop import main
from bench.record.chain import verify
from labkit import FAKE_SOURCES, STOP_LIST, Lab


def config(lab: Lab, tmp: Path) -> Path:
    values = {
        "session_id": "s1",
        "application": "fake",
        "adapter": "bench.fake.adapter:FakeAdapter",
        "lab_dir": str(lab.lab),
        "spec_files": list(lab.config.spec_files),
        "experiments_dir": "experiments",
        "state_dir": str(lab.root / "state"),
        "sessions_dir": str(lab.root / "sessions"),
        "seed": 7,
        "scan_sources": [str(FAKE_SOURCES)],
        "stop_list": str(STOP_LIST),
        "resume": True,
    }
    path = tmp / "session.toml"
    path.write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in values.items()))
    return path


def test_stops_a_session_left_open_by_a_closed_server(lab: Lab, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    lab.start().close()  # what a closed bench-mcp leaves behind
    assert main([str(config(lab, tmp_path)), "--reason", "the connection closed"]) == 0
    entries = verify(lab.root / "sessions" / "fake" / "s1", sealed=True)
    assert entries[-1]["body"]["end"] == "stopped"
    assert entries[-1]["body"]["reason"]["text"] == "the connection closed"
    assert main([str(config(lab, tmp_path)), "--reason", "again"]) == 1
    assert "already sealed" in capsys.readouterr().err


def test_fails_while_the_server_holds_the_session(lab: Lab, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    held = lab.start()  # the running server holds the state folder lock
    assert main([str(config(lab, tmp_path)), "--reason", "test"]) == 2
    assert "in use by another process" in capsys.readouterr().err
    assert held.state.sealed is None
    held.close()


def test_needs_a_reason(lab: Lab, tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main([str(config(lab, tmp_path))])
