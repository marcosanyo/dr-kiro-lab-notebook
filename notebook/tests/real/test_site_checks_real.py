"""The site checks of task 9.5 on a full build of the committed records through the command line into
`tmp_path` (Requirements 3.1-3.4, 4.5; design 9, N28)."""

from pathlib import Path

import pytest

from fixtures import site_checks
from notebook import cli, records, tables

ROOT = Path(__file__).resolve().parents[3]


def _argv(out: Path) -> list[str]:
    return [
        "--sessions", str(ROOT / "sessions"),
        "--choices", str(ROOT / "notebook" / "choices"),
        "--layouts", str(ROOT / "notebook" / "layouts.toml"),
        "--words", str(ROOT / "notebook" / "commentary-words.txt"),
        "--scan-config", str(ROOT / "body-lab" / "adapter" / "scan_sources.toml"),
        "--scan-config", str(ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml"),
        "--stop-list", str(ROOT / ".kiro" / "blind-scan" / "stop-list.txt"),
        "--out", str(out),
    ]  # fmt: skip


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("real-site-checks") / "site"
    assert cli.main(_argv(out)) == 0
    return out


def test_the_real_site_has_its_pages_at_the_root(site):
    assert site_checks.layout_problems(site) == []


def test_no_real_file_holds_a_request_a_namespace_a_form_or_a_frame(site):
    assert site_checks.text_problems(site) == []


def test_every_real_link_is_relative_into_the_flat_site(site):
    assert site_checks.link_problems(site) == []


def test_every_real_page_has_one_script_one_stylesheet_picture_buttons_and_the_legend_link(site):
    assert site_checks.page_problems(site) == []


def test_every_ended_table_is_in_the_html_without_script(site):
    for record in records.load(ROOT / "sessions"):
        table = tables.check_end(record)
        if table is None:
            continue
        page = site_checks.parse(site, f"{record.application}-{record.session}.html")
        assert page.row_ids == [row.id for row in table.rows], record.name
        shown = "".join(page.text)
        for row in table.rows:
            assert row.rule in shown, (record.name, row.id)
