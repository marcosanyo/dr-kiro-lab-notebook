"""The site checks on a labelled fixture build (task 9.5; Requirements 3.1-3.4, 3.7, 4.5; design 9, N28).

The record is a fake session through the bench (`fixtures.session`), labelled fake in its declaration and
every trial, built only through `build(..., allow_fake=True)` into `tmp_path`. Its numbers are not results.
"""

from pathlib import Path

import pytest

from fixtures import site_checks
from fixtures.session import FAKE_SOURCES, STOP_LIST, accepted_session
from notebook import build, records, tables, text
from notebook.inputs import Inputs

CHOICE = 'contrast = ["T1", "T2"]\nbest = "T7"\nmissed = "H2.P1"\n'
COVER = (
    '[miss]\napplication = "fake"\nsession = "s1"\nprediction = "H2.P1"\n\n'
    '[[card]]\napplication = "fake"\nsession = "s1"\ntrial = "T1"\n'
)
LAYOUTS = '[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\nsource = "test fixture: one 8 x 8 picture"\n'
WORDS = "# test fixture word list\nlimp\n"


@pytest.fixture(scope="module")
def fixture_site(tmp_path_factory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("site-checks")
    made = accepted_session(root / "lab")
    choices = root / "choices"
    (choices / "fake").mkdir(parents=True)
    (choices / "fake" / "s1.toml").write_text(CHOICE)
    (choices / "cover.toml").write_text(COVER)
    (root / "layouts.toml").write_text(LAYOUTS)
    (root / "words.txt").write_text(WORDS)
    out = root / "site"
    inputs = Inputs(
        sessions=made.sessions,
        choices=choices,
        layouts=root / "layouts.toml",
        words=root / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=out,
    )
    build.build(inputs, allow_fake=True)
    return made.sessions, out


def test_every_page_is_at_the_root_and_only_pictures_and_assets_are_in_subfolders(fixture_site):
    _, site = fixture_site
    assert site_checks.layout_problems(site) == []


def test_no_file_holds_a_request_a_namespace_a_form_or_a_frame(fixture_site):
    _, site = fixture_site
    assert site_checks.text_problems(site) == []


def test_every_link_is_relative_into_the_flat_site(fixture_site):
    _, site = fixture_site
    assert site_checks.link_problems(site) == []


def test_every_page_has_the_one_script_and_stylesheet_only_picture_buttons_and_the_footer_links(fixture_site):
    _, site = fixture_site
    assert site_checks.page_problems(site) == []


def test_the_table_and_its_text_are_in_the_html_without_script(fixture_site):
    sessions, site = fixture_site
    (record,) = records.load(sessions, allow_fake=True)
    table = tables.check_end(record)
    page = site_checks.parse(site, "fake-s1.html")
    assert page.tables >= 1
    assert page.row_ids == [row.id for row in table.rows]
    shown = "".join(page.text)
    for row in table.rows:
        assert row.rule in shown
        assert row.status in shown


@pytest.mark.parametrize(
    "value",
    [
        "https://example.org/x.css",
        "http:x",
        "//example.org/x.png",
        "/index.html",
        "../index.html",
        "q/x.html",
        "data:image/png;base64,AA",
        "javascript:void(0)",
    ],
)
def test_the_link_check_refuses_links_that_leave_the_flat_site(value):
    assert site_checks._link_problem(value) is not None


@pytest.mark.parametrize("value", ["legend.html", "#row-R1", "fake-s1.html#E1-T1", "a/notebook.css", ""])
def test_the_link_check_accepts_links_into_the_flat_site(value):
    assert site_checks._link_problem(value) is None


def test_a_planted_forbidden_item_is_found_naming_the_file(fixture_site, tmp_path):
    _, site = fixture_site
    (tmp_path / "x.html").write_text('<a href="legend.html">x</a><iframe src="https://example.org"></iframe>')
    problems = site_checks.text_problems(tmp_path) + site_checks.link_problems(tmp_path)
    assert any(p.startswith("x.html: holds '<iframe'") for p in problems)
    assert any(p.startswith("x.html: holds 'https:'") for p in problems)
    assert any("names a scheme" in p for p in problems)


def test_the_site_s_own_text_is_plain_english_characters():
    # Requirement 3.7: the builder's strings are in English; this checks they hold only ASCII characters.
    for name, value in vars(text).items():
        if name.isupper() and isinstance(value, str):
            assert value.isascii(), name
