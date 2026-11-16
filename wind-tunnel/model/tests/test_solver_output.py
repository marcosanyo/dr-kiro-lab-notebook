import dataclasses

import numpy as np
import pytest
from solver_output_writer import write_force_file, write_vorticity_file

from wind_tunnel_model.settings import Settings
from wind_tunnel_model.solver_output import (
    SolverOutputError,
    parse_force_file,
    parse_vorticity_file,
    picture_grid,
)


@pytest.fixture
def picture():
    # A small grid keeps the tests fast; the layout fields do not matter to the parser.
    return dataclasses.replace(Settings.load().picture, cell_width=8, cell_height=4)


def test_sample_force_file(tmp_path):
    path = tmp_path / "force.dat"
    path.write_text(
        "# Force\n# Time total pressure viscous\n0.1 1.5 -2 0 1 -2 0 0.5 0 0\n\n0.2 2.5 3 0 2 3 0 0.5 0 0\n"
    )
    series = parse_force_file(path)
    assert series.t.tolist() == [0.1, 0.2]
    assert series.fx.tolist() == [1.5, 2.5]
    assert series.fy.tolist() == [-2.0, 3.0]


def test_force_file_round_trip_with_writer(tmp_path):
    t, fx, fy = [0.5, 0.75, 1.0], [0.1, 0.2, 0.3], [-1.0, 0.0, 1.0]
    series = parse_force_file(write_force_file(tmp_path / "f.dat", t, fx, fy))
    assert (series.t.tolist(), series.fx.tolist(), series.fy.tolist()) == (t, fx, fy)


@pytest.mark.parametrize("bad", ["nan", "inf", "-inf"])
def test_force_file_non_finite_is_refused(tmp_path, bad):
    path = tmp_path / "force.dat"
    path.write_text(f"0.1 1 2 0 0 0 0 0 0 0\n0.2 {bad} 2 0 0 0 0 0 0 0\n")
    with pytest.raises(SolverOutputError, match=r"force\.dat:2.*non-finite"):
        parse_force_file(path)


def test_force_file_empty_is_refused(tmp_path):
    path = tmp_path / "force.dat"
    path.write_text("# only a header\n")
    with pytest.raises(SolverOutputError, match="no rows"):
        parse_force_file(path)


def test_force_file_missing_is_refused(tmp_path):
    with pytest.raises(SolverOutputError, match="missing"):
        parse_force_file(tmp_path / "absent.dat")


def test_force_file_unreadable_is_refused(tmp_path):
    path = tmp_path / "force.dat"
    path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(SolverOutputError, match="cannot be read"):
        parse_force_file(path)


@pytest.mark.parametrize("second", ["0.1", "0.05"])
def test_force_file_times_must_increase(tmp_path, second):
    path = tmp_path / "force.dat"
    path.write_text(f"0.1 1 2 0 0 0 0 0 0 0\n{second} 1 2 0 0 0 0 0 0 0\n")
    with pytest.raises(SolverOutputError, match=r"force\.dat:2.*does not increase"):
        parse_force_file(path)


def test_force_file_wrong_columns_is_refused(tmp_path):
    path = tmp_path / "force.dat"
    path.write_text("0.1 1 2 0 0 0 0\n")
    with pytest.raises(SolverOutputError, match=r"force\.dat:1"):
        parse_force_file(path)


def test_vorticity_with_missing_points_becomes_mask(tmp_path, picture):
    omega = np.arange(32, dtype=float).reshape(4, 8) - 10.0
    mask = np.zeros((4, 8), dtype=bool)
    mask[1:3, 2:4] = True
    frame = parse_vorticity_file(write_vorticity_file(tmp_path / "w.xy", picture, omega, mask), picture)
    assert frame.mask.tolist() == mask.tolist()
    assert np.array_equal(frame.omega[~mask], omega[~mask])
    assert np.all(frame.omega[mask] == 0.0)


def test_vorticity_without_missing_points_has_empty_mask(tmp_path, picture):
    omega = np.linspace(-1, 1, 32).reshape(4, 8)
    mask = np.zeros((4, 8), dtype=bool)
    frame = parse_vorticity_file(write_vorticity_file(tmp_path / "w.xy", picture, omega, mask), picture)
    assert not frame.mask.any()
    assert np.array_equal(frame.omega, omega)


def test_vorticity_file_without_points_is_refused(tmp_path, picture):
    path = tmp_path / "w.xy"
    path.write_text("")
    with pytest.raises(SolverOutputError, match="no points"):
        parse_vorticity_file(path, picture)


def test_vorticity_point_off_grid_is_refused(tmp_path, picture):
    xs, ys = (a.tolist() for a in picture_grid(picture))
    path = tmp_path / "w.xy"
    path.write_text(f"{xs[0] + 0.1!r} {ys[0]!r} 0 0 0 1\n")
    with pytest.raises(SolverOutputError, match=r"w\.xy:1.*not a point of the grid"):
        parse_vorticity_file(path, picture)


def test_vorticity_duplicate_point_is_refused(tmp_path, picture):
    xs, ys = (a.tolist() for a in picture_grid(picture))
    row = f"{xs[0]!r} {ys[0]!r} 0 0 0 1\n"
    path = tmp_path / "w.xy"
    path.write_text(row + row)
    with pytest.raises(SolverOutputError, match=r"w\.xy:2.*twice"):
        parse_vorticity_file(path, picture)


def test_vorticity_non_finite_and_short_rows_are_refused(tmp_path, picture):
    xs, ys = (a.tolist() for a in picture_grid(picture))
    path = tmp_path / "w.xy"
    path.write_text(f"{xs[0]!r} {ys[0]!r} 0 0 0 nan\n")
    with pytest.raises(SolverOutputError, match="non-finite"):
        parse_vorticity_file(path, picture)
    path.write_text(f"{xs[0]!r} {ys[0]!r} 0 1\n")
    with pytest.raises(SolverOutputError, match="expected 6 numbers"):
        parse_vorticity_file(path, picture)


def test_vorticity_missing_file_is_refused(tmp_path, picture):
    with pytest.raises(SolverOutputError, match="missing"):
        parse_vorticity_file(tmp_path / "absent.xy", picture)


def test_picture_grid_orientation(picture):
    xs, ys = (a.tolist() for a in picture_grid(picture))
    assert np.all(np.diff(xs) > 0)
    assert np.all(np.diff(ys) < 0)
    x0, x1, y0, y1 = picture.window
    assert x0 < xs[0] and xs[-1] < x1 and y0 < ys[-1] and ys[0] < y1
