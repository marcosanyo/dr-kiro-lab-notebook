"""The build's four phases and the site writer on a labelled fixture (design "Overview", 12, N4, N19, N28;
Requirements 2.1, 2.7, 20.3, 21.1, 21.2).

The record is a fake session through the bench (`fixtures.session`), labelled fake in its declaration and
every trial. It is built only through `build(..., allow_fake=True)` into `tmp_path` and is never published;
its numbers are not results.
"""

import hashlib
import json
from pathlib import Path

import pytest
from bench.scan.levels import SIDECAR_SUFFIX, sidecar_pieces

from fixtures.choices import write_app
from fixtures.session import FAKE_SOURCES, STOP_LIST, Lab, accepted_session
from notebook import addresses, build, cli, records, site, text
from notebook.errors import NotebookError
from notebook.ink import markup
from notebook.inputs import Inputs

LAYOUTS = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
WORDS = "# test fixture word list\nlimp\n"


@pytest.fixture(scope="module")
def fixture_inputs(tmp_path_factory) -> tuple[Path, Inputs]:
    root = tmp_path_factory.mktemp("fixture-build")
    made = accepted_session(root / "lab")
    app = write_app(root / "app")
    (root / "layouts.toml").write_text(LAYOUTS)
    (root / "words.txt").write_text(WORDS)
    inputs = Inputs(
        sessions=made.sessions,
        requests=root / "requests",
        apps=(app,),
        layouts=root / "layouts.toml",
        words=root / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=root / "unused",
    )
    return root, inputs


def _with_out(inputs: Inputs, out: Path) -> Inputs:
    return Inputs(**{**inputs.__dict__, "out": out})


@pytest.fixture(scope="module")
def built(fixture_inputs) -> Path:
    root, inputs = fixture_inputs
    out = root / "site"
    build.build(_with_out(inputs, out), allow_fake=True)
    return out


def _all_files(out: Path) -> set[str]:
    return {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}


def test_a_fixture_build_writes_the_expected_paths_with_a_sidecar_per_text_file(fixture_inputs, built):
    _, inputs = fixture_inputs
    (record,) = records.load(inputs.sessions, allow_fake=True)
    # Pictures shown: every trial's, in its experiment entry (Requirement 10.8), which includes the cover's
    # and the margin's.
    pictures = {f"fake/p/{hashlib.sha256(t.picture.data).hexdigest()}.png" for t in record.trials}
    # The front page at the root and the fake application's folder; each has its own `a/`.
    texts = {
        "index.html",
        "a/notebook.css",
        "a/notebook.js",
        "fake/index.html",
        "fake/legend.html",
        "fake/how.html",
        "fake/s1.html",
        "fake/a/notebook.css",
        "fake/a/notebook.js",
    }
    shipped = {f"{scope}{addresses.FONT_LICENSE}" for scope in ("", "fake/")} | {
        f"{scope}{addresses.ASSET_DIR}/{n}" for scope in ("", "fake/") for n in addresses.FONT_FILES
    }
    # The front page's card shows a picture of the session the application opens on, in p/ at the root.
    hashes = {hashlib.sha256(t.picture.data).hexdigest() for t in record.trials}
    front = {p for p in _all_files(built) if p.startswith("p/")}
    assert front and all(p[2:-4] in hashes for p in front)
    expected = texts | {t + SIDECAR_SUFFIX for t in texts} | pictures | shipped | front
    assert _all_files(built) == expected
    for path in pictures:
        data = (built / path).read_bytes()
        assert path == f"fake/p/{hashlib.sha256(data).hexdigest()}.png"
    assert not (built.parent / ".site.staging").exists()


def test_every_sidecar_is_compact_sorted_and_read_by_the_bench(built):
    for path in sorted(_all_files(built)):
        if not path.endswith((".html", ".css", ".js")):
            continue
        file = built / path
        content = file.read_text(encoding="utf-8")
        raw = (built / (path + SIDECAR_SUFFIX)).read_bytes().decode("utf-8")
        data = json.loads(raw)
        assert raw == json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        pieces = sidecar_pieces(file, content)
        assert "".join(p.text for p in pieces) == content
        if path.startswith("a/"):
            assert data == {"ranges": [{"author": "bench", "end": len(content), "start": 0}]}


def test_every_page_of_a_fixture_build_carries_the_banner(built):
    for path in ("index.html", "fake/index.html", "fake/legend.html", "fake/how.html", "fake/s1.html"):
        page = (built / path).read_text(encoding="utf-8")
        assert page.count(text.FIXTURE_BANNER) == 1
        assert page.index(text.FIXTURE_BANNER) > page.index("<body>")


def test_the_command_line_refuses_fake_records(fixture_inputs, tmp_path, capsys):
    _, inputs = fixture_inputs
    argv = [
        "--sessions", str(inputs.sessions),
        "--requests", str(inputs.requests),
        "--app", str(inputs.apps[0]),
        "--layouts", str(inputs.layouts),
        "--words", str(inputs.words),
        "--scan-config", str(FAKE_SOURCES),
        "--stop-list", str(STOP_LIST),
        "--out", str(tmp_path / "out"),
    ]  # fmt: skip
    assert cli.main(argv) == 1
    assert "fake" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_a_staging_folder_left_in_place_is_refused(fixture_inputs, tmp_path):
    _, inputs = fixture_inputs
    out = tmp_path / "out"
    staging = tmp_path / ".out.staging"
    staging.mkdir()
    (staging / "index.html").write_text("left from an earlier build")
    with pytest.raises(NotebookError) as caught:
        build.build(_with_out(inputs, out), allow_fake=True)
    assert caught.value.where == str(staging)
    assert not out.exists()
    assert (staging / "index.html").read_text() == "left from an earlier build"


def test_an_empty_output_folder_is_filled(fixture_inputs, tmp_path):
    _, inputs = fixture_inputs
    out = tmp_path / "empty"
    out.mkdir()
    build.build(_with_out(inputs, out), allow_fake=True)
    assert (out / "index.html").is_file()


def test_a_failed_check_writes_nothing(fixture_inputs, tmp_path):
    _, inputs = fixture_inputs
    words = tmp_path / "words.txt"
    # A listed word that a commentary string of the site uses fails the word check in phase 1.
    words.write_text("the\n")
    out = tmp_path / "out"
    with pytest.raises(NotebookError):
        build.build(Inputs(**{**inputs.__dict__, "words": words, "out": out}), allow_fake=True)
    assert not out.exists()
    assert not (tmp_path / ".out.staging").exists()


def test_two_files_with_one_path_are_refused_naming_both_owners():
    s = site.Site()
    s.add_text("x-replay-1.html", [markup("a")], "the session pages: x-replay-1.html")
    with pytest.raises(NotebookError) as caught:
        s.add_text("x-replay-1.html", [markup("b")], "the replay steps: x-replay-1.html")
    assert caught.value.where == "the replay steps: x-replay-1.html"
    assert "the session pages: x-replay-1.html" in caught.value.problem
    with pytest.raises(NotebookError):
        s.add_text("X-Replay-1.html", [markup("c")], "a page that differs by case")
    with pytest.raises(NotebookError):
        s.add_bytes("x-replay-1.html.authors.json", b"{}", "a file on a sidecar path")


@pytest.mark.parametrize(
    "path", ["../index.html", "/index.html", "q/x.html", "p/q/x.png", "a//x.js", "./x.html"]
)
def test_paths_outside_the_flat_layout_are_refused(path):
    with pytest.raises(NotebookError):
        site.Site().add_bytes(path, b"x", "test")


def test_a_session_id_that_cannot_name_a_page_fails_before_anything_is_written(fixture_inputs, tmp_path):
    _, inputs = fixture_inputs
    lab = Lab(tmp_path / "lab")
    session = lab.start(session_id="S_1")
    session.stop("test fixture: stopped at once")
    out = tmp_path / "out"
    with pytest.raises(NotebookError) as caught:
        build.build(Inputs(**{**inputs.__dict__, "sessions": lab.sessions, "out": out}), allow_fake=True)
    assert "'S_1'" in caught.value.problem and "cannot name a page" in caught.value.problem
    assert not out.exists()
