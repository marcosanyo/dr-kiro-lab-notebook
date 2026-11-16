import re

import pytest

from wind_tunnel_model.casegen import (
    CASE_DIR,
    KNOB_NAMES,
    CaseError,
    render_case,
    sample_points,
)
from wind_tunnel_model.settings import Settings

KNOBS = dict.fromkeys(KNOB_NAMES, 1.0)


def _files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_viscosity_is_speed_times_height_over_reynolds(tmp_path):
    s = Settings.load()
    render_case(KNOBS, s, tmp_path / "c")
    text = (tmp_path / "c/constant/transportProperties").read_text()
    match = re.search(r"nu\s+\[0 2 -1 0 0 0 0\]\s+(\S+);", text)
    assert float(match.group(1)) == s.flow.speed * s.flow.height / 150.0
    s100 = s.with_reynolds(100.0)
    render_case(KNOBS, s100, tmp_path / "d")
    text = (tmp_path / "d/constant/transportProperties").read_text()
    assert float(re.search(r"\]\s+(\S+);", text).group(1)) == 1.0 / 100.0


def test_no_placeholder_remains_and_names_are_written(tmp_path):
    render_case(KNOBS, Settings.load(), tmp_path / "c")
    files = _files(tmp_path / "c")
    assert "Allrun" in files and "system/samplePoints" in files and "0/U" in files
    assert not [n for n in files if n.endswith(".in")]
    for name, data in files.items():
        assert b"@" not in data, name
        assert b"\r" not in data, name
    assert (tmp_path / "c/Allrun").stat().st_mode & 0o111


def test_two_renders_are_identical(tmp_path):
    s = Settings.load()
    render_case(KNOBS, s, tmp_path / "a")
    render_case(KNOBS, s, tmp_path / "b")
    assert _files(tmp_path / "a") == _files(tmp_path / "b")


def test_sample_points_cover_the_window():
    s = Settings.load()
    lines = sample_points(s).splitlines()
    assert len(lines) == s.picture.cell_width * s.picture.cell_height + 2
    assert lines[0] == "(" and lines[-1] == ")"


def test_unfilled_placeholder_is_an_error(tmp_path):
    (tmp_path / "t").mkdir()
    (tmp_path / "t/x.in").write_text("a @NOPE@\n")
    with pytest.raises(CaseError, match="NOPE"):
        render_case(KNOBS, Settings.load(), tmp_path / "c", template_dir=tmp_path / "t")


def test_knob_names_and_existing_folder_are_refused(tmp_path):
    s = Settings.load()
    with pytest.raises(CaseError, match="knobs"):
        render_case({"aspect": 1.0}, s, tmp_path / "c")
    (tmp_path / "full").mkdir()
    (tmp_path / "full/x").write_text("x")
    with pytest.raises(CaseError, match="not empty"):
        render_case(KNOBS, s, tmp_path / "full")


def test_every_template_placeholder_has_a_value():
    from wind_tunnel_model.casegen import placeholder_values

    known = set(placeholder_values(Settings.load()))
    used = set()
    for path in CASE_DIR.rglob("*"):
        if path.is_file():
            used |= set(re.findall(r"@([A-Za-z0-9_]+)@", path.read_text()))
    assert used <= known
