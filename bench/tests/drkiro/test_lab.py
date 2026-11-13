"""dr-kiro task 2: a lab made by `bench-make-lab` passes the blind scan for the fake application
(1.3, 7.1)."""

from pathlib import Path

from bench.drkiro.lab import make_lab
from bench.scan.scan import Scanner, local_paths
from bench.scan.terms import LabLayout, load_app, load_stop_list
from labkit import FAKE_SOURCES, STOP_LIST


def test_made_lab_passes_the_blind_scan(tmp_path: Path) -> None:
    lab = tmp_path / "lab"
    lab.mkdir()
    make_lab(lab)
    assert (lab / ".kiro" / "agents" / "dr-kiro.json").is_file()
    assert (lab / ".kiro" / "hooks" / "confine.py").is_file()
    app = load_app(FAKE_SOURCES)
    layout = LabLayout(lab, ("experiments/**", ".kiro/specs/**"))
    sources = type(app)(app.names, app.file_names, app.solver_dirs, app.allow, layout)
    scanner = Scanner([sources], load_stop_list(STOP_LIST), local_paths=local_paths(STOP_LIST))
    assert scanner.scan_paths([lab]) == []
