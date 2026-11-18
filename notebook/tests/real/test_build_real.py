"""One full build of the committed records through the command line into `tmp_path` (task 9.2).

The paths asserted are the pages that exist so far; later tasks add `built.html` (22.1). Links to those pages
are listed in `NOT_YET_WRITTEN`. The replay pages are not in this version (Decision 48): no replay page is
written, and no link may name one.
"""

import re
from pathlib import Path

import pytest
from bench.scan.levels import SIDECAR_SUFFIX

from notebook import addresses, cli

ROOT = Path(__file__).resolve().parents[3]
# Pages that pages link to but later tasks write.
NOT_YET_WRITTEN: set[str] = set()
PAGES = {
    "index.html",
    "legend.html",
    "how.html",
    "body-lab.html",
    "wind-tunnel.html",
    "body-lab-body-1.html",
    "body-lab-body-2.html",
    "wind-tunnel-wt-002.html",
    "wind-tunnel-wt-003.html",
    "wind-tunnel-wt-004.html",
}
# The file part of a link: the query and the fragment are not part of it.
_HREF = re.compile(r'(?:href|src)="([^"#?]*)(?:[?#][^"]*)?"')


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
    out = tmp_path_factory.mktemp("real-build") / "site"
    assert cli.main(_argv(out)) == 0
    return out


def test_the_real_build_writes_every_page_written_so_far_with_sidecars(site):
    files = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    texts = PAGES | {"a/notebook.css", "a/notebook.js"}
    shipped = {addresses.FONT_LICENSE, *(f"{addresses.ASSET_DIR}/{n}" for n in addresses.FONT_FILES)}
    assert {f for f in files if not f.startswith("p/")} == texts | {
        t + SIDECAR_SUFFIX for t in texts
    } | shipped
    assert all(re.fullmatch(r"p/[0-9a-f]{64}\.png", f) for f in files if f.startswith("p/"))
    assert not (site.parent / ".site.staging").exists()


def test_the_real_build_has_no_replay_page_and_no_link_to_one(site):
    """Decision 48: the replay steps are not in this version."""
    assert not [p for p in site.rglob("*") if "replay" in p.name]
    for page in PAGES:
        assert "replay" not in (site / page).read_text(encoding="utf-8")


def test_every_link_of_the_real_build_names_a_file_of_the_site_or_a_page_still_to_come(site):
    files = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    targets: set[str] = set()
    for page in PAGES:
        for match in _HREF.finditer((site / page).read_text(encoding="utf-8")):
            if match.group(1):
                targets.add(match.group(1))
    assert all(".." not in t and not t.startswith("/") for t in targets)
    assert targets - files == NOT_YET_WRITTEN
