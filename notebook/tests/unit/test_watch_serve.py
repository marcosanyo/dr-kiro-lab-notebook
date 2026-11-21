"""The watch's command line and loopback server (task 26.2; Requirements 23.1-23.4, 3.2) on the fake fixture
session: nothing here is a result."""

import ast
import hashlib
import json
import re
import shutil
import threading
from pathlib import Path

import pytest

from fixtures.choices import write_app
from fixtures.session import accepted_session
from notebook import text
from notebook.errors import NotebookError
from notebook.watch import cli, serve

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(cli.__file__).resolve().parents[1]
CONFIGS = [
    ROOT / "body-lab" / "adapter" / "scan_sources.toml",
    ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
]
STOP_LIST = ROOT / ".kiro" / "blind-scan" / "stop-list.txt"
WORDS = ROOT / "notebook" / "commentary-words.txt"
LAYOUTS = ROOT / "notebook" / "layouts.toml"
ONE = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
OPTIONS = ["--record", "--state", "--layouts", "--words", "--scan-config", "--stop-list", "--port", "--app"]


def _argv(record, state, port="0"):
    return [
        "--record", str(record), "--state", str(state), "--layouts", str(LAYOUTS), "--words", str(WORDS),
        "--scan-config", str(CONFIGS[0]), "--stop-list", str(STOP_LIST), "--port", port,
        "--app", str(Path(state) / "app"),
    ]  # fmt: skip


@pytest.fixture(scope="module")
def state(tmp_path_factory):
    """A bench state folder holding the fixture record, and the fake application's notebook folder."""
    root = tmp_path_factory.mktemp("serve")
    fixture = accepted_session(root / "lab")
    folder = root / "state"
    shutil.copytree(fixture.sealed, folder / fixture.sealed.name)
    layouts = root / "layouts.toml"
    layouts.write_text(ONE)
    return folder, folder / fixture.sealed.name, write_app(root / "app"), layouts


def _inputs(state, port=0):
    folder, record, app, layouts = state
    return cli.WatchInputs(record, folder, layouts, WORDS, tuple(CONFIGS), STOP_LIST, port, (app,))


def _snapshot(folder: Path):
    return {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        for p in sorted(folder.rglob("*"))
    }


# Command line


@pytest.mark.parametrize("missing", OPTIONS)
def test_each_missing_option_is_named_and_nothing_is_read(missing, capsys, tmp_path):
    argv = _argv(tmp_path / "x" / "r", tmp_path / "x")
    at = argv.index(missing)
    del argv[at : at + 2]
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    assert exit_.value.code == cli.USAGE_EXIT
    assert missing in capsys.readouterr().err


@pytest.mark.parametrize("option", ["--out", "--host", "--choices"])
def test_there_is_no_out_host_or_choices_option(option, tmp_path):
    with pytest.raises(SystemExit) as exit_:
        cli.parse([*_argv(tmp_path / "r", tmp_path), option, "x"])
    assert exit_.value.code == cli.USAGE_EXIT


def test_a_record_outside_state_is_refused(state, tmp_path):
    _, record, _, layouts = state
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(NotebookError, match="--record"):
        cli.check_record(
            cli.WatchInputs(record, other, layouts, WORDS, tuple(CONFIGS), STOP_LIST, 0, (state[2],))
        )


def test_a_start_entry_whose_session_differs_from_the_folder_name_is_refused(state, tmp_path):
    record = state[1]
    renamed = tmp_path / "state" / "other-name"
    shutil.copytree(record, renamed)
    inputs = cli.WatchInputs(
        renamed, renamed.parent, state[3], WORDS, tuple(CONFIGS), STOP_LIST, 0, (state[2],)
    )
    with pytest.raises(NotebookError, match="folder name"):
        cli.check_record(inputs)


def test_the_exit_code_of_a_failed_check_is_1(capsys, tmp_path):
    (tmp_path / "state").mkdir()
    assert cli.main(_argv(tmp_path / "elsewhere", tmp_path / "state")) == cli.CHECK_EXIT
    assert "notebook-watch: --record:" in capsys.readouterr().err


# Server


@pytest.fixture
def running(state):
    server = cli.prepare(_inputs(state), allow_fake=True)
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        yield server
    finally:
        server.stop()
        thread.join()


def test_the_server_binds_127_0_0_1_only(running):
    assert running._http.server_address[0] == "127.0.0.1"
    assert serve.HOST == "127.0.0.1"


def test_version_and_session_page_are_served_and_the_page_is_at_the_bench(running, state):
    status, _, body = serve.fetch(running.port, "/version")
    assert status == 200
    assert json.loads(body) == {"version": running.version.number, "stop": None}
    assert running.version.number >= 1
    page_path = "/fake-s1.html"
    status, _, page = serve.fetch(running.port, page_path)
    assert status == 200
    assert serve.fetch(running.port, "/")[2] == page
    html = page.decode()
    assert text.AT_BENCH in html
    assert text.SEALED_BANNER in html  # the record in the fixture is sealed (23.10)


def test_links_resolve_to_served_paths_and_no_request_goes_to_another_host(running):
    _, _, page = serve.fetch(running.port, "/")
    html = page.decode()
    assert not re.search(r"(?:https?:)?//", html)
    refs = re.findall(r'(?:href|src|data-[a-z-]*src)="([^"]*)"', html)
    assert refs
    for ref in refs:
        if ref.startswith("#"):
            continue
        assert ".." not in ref
        path = "/" + ref.split("#")[0].lstrip("/")
        status, _, _ = serve.fetch(running.port, path)
        assert status == 200, ref
    for path in ("/legend.html", "/a/notebook.css", "/a/notebook.js"):
        assert serve.fetch(running.port, path)[0] == 200


@pytest.mark.parametrize(
    "path",
    ["/nope", "/..", "/a/", "/p/x.png", "/a/../a/notebook.css", "/version?x=1", "/a/watch.js", "/index.html"],
)
def test_only_the_fixed_routes_exist(running, path):
    expected = 200 if path == "/a/watch.js" else 404
    assert serve.fetch(running.port, path)[0] == expected


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "HEAD", "PATCH", "OPTIONS"])
def test_only_get_is_answered(running, method):
    status, headers, _ = serve.fetch(running.port, "/", method)
    assert status == 405 and headers["Allow"] == "GET"


def test_a_stop_is_in_version(state, tmp_path):
    folder, record, app, layouts = state
    broken = tmp_path / "state" / record.name
    shutil.copytree(record, broken)
    log = broken / "log.jsonl"
    lines = log.read_bytes().split(b"\n")
    lines[2] = b"{"  # the third line is not JSON
    log.write_bytes(b"\n".join(lines))
    inputs = cli.WatchInputs(broken, broken.parent, layouts, WORDS, tuple(CONFIGS), STOP_LIST, 0, (app,))
    server = cli.prepare(inputs, allow_fake=True)
    try:
        server.start()
        _, _, body = serve.fetch(server.port, "/version")
        assert json.loads(body)["stop"] == f"line 3: {text.WATCH_NOT_JSON}"
        assert serve.fetch(server.port, "/")[0] == 200  # the last good version stays
    finally:
        server.close()


def test_the_watch_changes_nothing_on_disk(state, tmp_path):
    folder, record, app, layouts = state
    copy = tmp_path / "state"
    shutil.copytree(folder, copy)
    before = _snapshot(copy)
    inputs = cli.WatchInputs(copy / record.name, copy, layouts, WORDS, tuple(CONFIGS), STOP_LIST, 0, (app,))
    server = cli.prepare(inputs, allow_fake=True)
    thread = threading.Thread(target=server.run)
    thread.start()
    try:
        for path in ("/", "/version", "/legend.html", "/a/notebook.css"):
            assert serve.fetch(server.port, path)[0] == 200
        server.watch.poll()
    finally:
        server.stop()
        thread.join()
    assert _snapshot(copy) == before
    assert not list(copy.rglob("*.lock")) and not list(copy.rglob(".lock"))


# Imports


def _imports(path: Path) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
            out |= {f"{node.module}.{a.name}" for a in node.names}
    return out


def test_no_build_module_imports_the_watch_and_only_serve_imports_http():
    http_users = []
    for path in sorted(PACKAGE.rglob("*.py")):
        names = _imports(path)
        in_watch = PACKAGE / "watch" in path.parents
        if not in_watch:
            assert not {n for n in names if n == "notebook.watch" or n.startswith("notebook.watch.")}, path
        if {n for n in names if n.split(".")[0] in ("http", "socket", "urllib", "socketserver")}:
            http_users.append(path.name)
        assert not {n for n in names if n.split(".")[0] in ("socket", "urllib", "socketserver")}, path
    assert http_users == ["serve.py"]
