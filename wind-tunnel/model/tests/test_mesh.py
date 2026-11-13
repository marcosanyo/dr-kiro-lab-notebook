"""Tests of the mesher (design 3; Requirements 6.8, 6.9, 7.2, 10.2)."""

import itertools

import pytest

from wind_tunnel_model.casegen import MESH_FILE
from wind_tunnel_model.geometry import outline
from wind_tunnel_model.mesh import VOLUME_NAME, FakeMesher, GmshMesher, MeshError
from wind_tunnel_model.settings import Settings


@pytest.fixture(scope="module")
def settings():
    return Settings.load()


def physical_names(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    start = lines.index("$PhysicalNames")
    count = int(lines[start + 1])
    # Each line is: dimension, tag, "name". Returns (dimension, name) pairs.
    rows = [line.split(" ", 2) for line in lines[start + 2 : start + 2 + count]]
    return [(dim, name.strip('"')) for dim, _, name in rows]


def z_values(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    start = lines.index("$Nodes")
    count = int(lines[start + 1])
    return {float(line.split(" ")[3]) for line in lines[start + 2 : start + 2 + count]}


def test_fake_mesher_writes_a_fixed_file(tmp_path, settings):
    FakeMesher().build((), settings, tmp_path)
    assert (tmp_path / MESH_FILE).read_text() == FakeMesher.CONTENT


@pytest.mark.needs_gmsh
def test_empty_outline_is_a_mesh_error(tmp_path, settings):
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    with pytest.raises(MeshError):
        GmshMesher().build((), settings, tmp_path)


@pytest.mark.needs_gmsh
@pytest.mark.parametrize(
    ("aspect", "corner", "splitter", "angle"),
    list(itertools.product((0.5, 3.0), (0.0, 1.0), (0.0, 3.0), (0.0, 30.0))),
)
def test_end_corner_outlines_give_named_groups(tmp_path, settings, aspect, corner, splitter, angle):
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    mesher = GmshMesher()
    mesher.build(outline(aspect, corner, splitter, angle, settings), settings, tmp_path)
    path = tmp_path / MESH_FILE
    p = settings.patches
    names = physical_names(path)
    assert sorted(name for dim, name in names if dim == "2") == sorted(
        [p.inlet, p.outlet, p.lateral, p.obstacle, p.front_and_back]
    )
    assert [name for dim, name in names if dim == "3"] == [VOLUME_NAME]
    assert mesher.cells > 0
    assert z_values(path) == {0.0, settings.flow.depth}


@pytest.mark.needs_gmsh
def test_same_input_gives_identical_file(tmp_path, settings):
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    pieces = outline(2.0, 0.5, 1.0, 10.0, settings)
    first, second = tmp_path / "a", tmp_path / "b"
    GmshMesher().build(pieces, settings, first)
    GmshMesher().build(pieces, settings, second)
    assert (first / MESH_FILE).read_bytes() == (second / MESH_FILE).read_bytes()
