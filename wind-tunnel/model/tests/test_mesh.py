"""Tests of the mesher (design 3; Requirements 6.8, 6.9, 7.2, 10.2)."""

import itertools
import json
import threading

import pytest

from wind_tunnel_model.casegen import MESH_FILE
from wind_tunnel_model.geometry import outline
from wind_tunnel_model.mesh import VOLUME_NAME, FakeMesher, GmshMesher, MeshError, MeshTimeout
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
    list(itertools.product((0.5, 3.0), (0.0, 1.0), (0.0, 3.0), (0.0, 15.0))),
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


def _build_in_worker_thread(outline_value, settings, dest):
    errors = []

    def work():
        try:
            GmshMesher().build(outline_value, settings, dest)
        except BaseException as error:  # noqa: BLE001 - handed to the main thread and asserted on
            errors.append(error)

    thread = threading.Thread(target=work)
    thread.start()
    thread.join()
    return errors


@pytest.mark.needs_gmsh
def test_mesh_builds_in_a_worker_thread_with_the_same_bytes(tmp_path, settings):
    """Trials run in a worker thread in the front end; Gmsh must not need the main thread (Decision 41)."""
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    body = outline(1.5, 0.5, 1.0, 10.0, settings)
    (tmp_path / "main").mkdir()
    (tmp_path / "worker").mkdir()
    GmshMesher().build(body, settings, tmp_path / "main")
    assert _build_in_worker_thread(body, settings, tmp_path / "worker") == []
    assert (tmp_path / "worker" / MESH_FILE).read_bytes() == (tmp_path / "main" / MESH_FILE).read_bytes()


@pytest.mark.needs_gmsh
def test_mesh_builds_in_a_new_thread_after_an_earlier_thread_has_exited(tmp_path, settings):
    """Decision 43: Gmsh in-process crashed the process here (wt-002). The child process does not."""
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    body = outline(1.5, 0.5, 1.0, 10.0, settings)
    for name in ("first", "second", "third"):
        assert _build_in_worker_thread(body, settings, tmp_path / name) == []
    first = (tmp_path / "first" / MESH_FILE).read_bytes()
    assert (tmp_path / "second" / MESH_FILE).read_bytes() == first
    assert (tmp_path / "third" / MESH_FILE).read_bytes() == first


@pytest.mark.needs_gmsh
def test_child_process_writes_the_bytes_of_an_in_process_build(tmp_path, settings):
    pytest.importorskip("gmsh", reason="Gmsh cannot be imported here")
    from wind_tunnel_model.mesh import build_in_this_process  # noqa: PLC0415

    body = outline(2.0, 0.5, 1.0, 10.0, settings)
    mesher = GmshMesher()
    mesher.build(body, settings, tmp_path / "child")
    cells = build_in_this_process(body, settings, tmp_path / "direct.msh")
    assert (tmp_path / "child" / MESH_FILE).read_bytes() == (tmp_path / "direct.msh").read_bytes()
    assert mesher.cells == cells


def test_outline_survives_the_trip_to_the_child_process(settings):
    from wind_tunnel_model.mesh import outline_from_data, outline_to_data  # noqa: PLC0415

    body = outline(2.57819, 0.953007, 1.241, 0.83314, settings)
    assert outline_from_data(json.loads(json.dumps(outline_to_data(body)))) == body


def test_failed_child_is_a_mesh_error_with_status_and_stderr(tmp_path, settings, monkeypatch):
    import wind_tunnel_model.mesh as mesh_module  # noqa: PLC0415

    monkeypatch.setattr(mesh_module, "WORKER_MODULE", "wind_tunnel_model.no_such_worker")
    with pytest.raises(MeshError) as caught:
        GmshMesher().build(outline(1.0, 1.0, 0.0, 0.0, settings), settings, tmp_path)
    assert "status" in str(caught.value)
    assert "no_such_worker" in caught.value.detail
    assert not isinstance(caught.value, MeshTimeout)


def test_time_limit_is_a_mesh_timeout(tmp_path, settings):
    body = outline(1.0, 1.0, 0.0, 0.0, settings)
    with pytest.raises(MeshTimeout):
        GmshMesher().build(body, settings, tmp_path, timeout_s=0.0)
    with pytest.raises(MeshTimeout):
        GmshMesher().build(body, settings, tmp_path, timeout_s=0.05)
