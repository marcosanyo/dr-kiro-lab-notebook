"""Static checks of `watch.js` (task 26.3; Requirements 23.4, 23.9, 3.2; design Component 13, N28, N36).
No browser and no Node: the script is read as text. The fixture record is fake and shows no result."""

import re
from pathlib import Path

import pytest

from fixtures.choices import write_app
from fixtures.session import FAKE_SOURCES, STOP_LIST, accepted_session
from notebook import addresses, build, choices, layouts, records, scan
from notebook.inputs import Inputs
from notebook.pages import shelf
from notebook.watch import serve

WATCH = Path(serve.__file__).resolve().parent / "assets" / "watch.js"
NOTEBOOK = Path(addresses.__file__).resolve().parent / "assets" / "notebook.js"
ONE = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)


@pytest.fixture(scope="module")
def source() -> str:
    return WATCH.read_text(encoding="utf-8")


def test_it_polls_the_version_every_1000_ms(source):
    assert re.search(r"var INTERVAL = 1000;", source)
    assert re.search(r"setInterval\(poll, INTERVAL\)", source)
    assert re.search(r'get\("/version"\)', source)
    assert len(re.findall(r"setInterval\(", source)) == 1


def test_it_saves_and_restores_the_scroll_position_and_the_open_states_by_id(source):
    assert "var left = scrollY;" in source
    assert "scrollTo(0, left)" in source
    assert 'querySelectorAll("details[id]")' in source
    assert "states[note.id] = note.open;" in source
    assert "note.open = states[note.id];" in source


def test_it_replaces_the_content_of_main_and_shows_the_stop_text_with_text_content(source):
    assert "replaceChildren" in source
    assert 'getElementById("watch-stop")' in source
    assert "note.textContent = text;" in source
    assert "innerHTML" not in source


def test_the_event_name_is_the_same_in_both_scripts(source):
    sent = re.findall(r'CustomEvent\("([^"]+)"\)', source)
    heard = re.findall(r'addEventListener\("(notebook:[^"]+)"', NOTEBOOK.read_text(encoding="utf-8"))
    assert sent == heard == ["notebook:refresh"]


def test_every_request_is_a_relative_address_on_the_same_origin(source):
    calls = re.findall(r"fetch\(([^,)]*)", source)
    assert calls == ["address"]
    gets = re.findall(r"\bget\(([^)]*)\)", source)
    assert sorted(g for g in gets if g != "address") == ['"/version"', "location.pathname"]
    assert not re.search(r"XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts|@import", source)


@pytest.mark.parametrize("word", ["window.", "tagName", "http", "//cdn", "https", "ftp:", "ws:"])
def test_the_script_has_no_forbidden_word(source, word):
    assert word not in source


def test_the_script_passes_the_blind_scan_at_the_builder_level():
    scanner = scan.load([FAKE_SOURCES], STOP_LIST)
    text = WATCH.read_text(encoding="utf-8")
    ranges = [{"author": "bench", "start": 0, "end": len(text)}]
    assert scan.file_findings(scanner, "watch.js", text, ranges) == []


def test_the_script_is_served_by_the_watch_when_the_file_exists():
    assert WATCH.is_file()
    assert serve.ASSETS / "watch.js" == WATCH
    assert addresses.WATCH_SCRIPT == "a/watch.js"


def test_the_build_does_not_link_or_write_the_script(tmp_path):
    made = accepted_session(tmp_path / "lab")
    app = write_app(tmp_path / "app")
    (tmp_path / "layouts.toml").write_text(ONE)
    (tmp_path / "words.txt").write_text("# test fixture word list\nlimp\n")
    inputs = Inputs(
        sessions=made.sessions,
        requests=tmp_path / "requests",
        apps=(app,),
        layouts=tmp_path / "layouts.toml",
        words=tmp_path / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=tmp_path / "site",
    )
    build.build(inputs, allow_fake=True)
    files = [p for p in (tmp_path / "site").rglob("*") if p.is_file() and p.suffix != ".png"]
    assert files
    assert not [p for p in files if p.name == "watch.js"]
    assert not [p for p in files if "watch.js" in p.read_bytes().decode("utf-8", "ignore")]


def test_only_the_page_at_the_bench_links_the_script(tmp_path):
    made = accepted_session(tmp_path / "lab")
    (full,) = records.load(made.sessions, allow_fake=True)
    (app,) = choices.load_apps([write_app(tmp_path / "app")], [full]).apps
    table = layouts.parse(ONE, "test fixture")
    segments, _ = shelf.at_bench_page(full, app, table, {})
    page = "".join(s.text for s in segments)
    assert page.count('<script src="a/watch.js" defer="defer"></script>') == 1
    assert page.index("a/notebook.js") < page.index("a/watch.js")
