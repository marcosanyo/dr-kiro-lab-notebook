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
    "wind-tunnel/index.html",
    "wind-tunnel/legend.html",
    "wind-tunnel/how.html",
    "wind-tunnel/wt-002.html",
    "wind-tunnel/wt-003.html",
    "wind-tunnel/wt-004.html",
    "body-lab/index.html",
    "body-lab/legend.html",
    "body-lab/how.html",
    "body-lab/body-1.html",
    "body-lab/body-2.html",
    "body-lab/body-3.html",
}
SCOPES = ("", "wind-tunnel/", "body-lab/")
# The file part of a link: the query and the fragment are not part of it.
_HREF = re.compile(r'(?:href|src)="([^"#?]*)(?:[?#][^"]*)?"')


def _argv(out: Path) -> list[str]:
    return [
        "--sessions", str(ROOT / "sessions"),
        "--requests", str(ROOT / "build-from-spec" / "requests"),
        "--app", str(ROOT / "wind-tunnel" / "notebook"),
        "--app", str(ROOT / "body-lab" / "notebook"),
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
    texts = PAGES | {f"{scope}a/{name}" for scope in SCOPES for name in ("notebook.css", "notebook.js")}
    shipped = {
        f"{scope}{path}"
        for scope in SCOPES
        for path in (addresses.FONT_LICENSE, *(f"{addresses.ASSET_DIR}/{n}" for n in addresses.FONT_FILES))
    }
    pictures = {f for f in files if "/p/" in f or f.startswith("p/")}
    assert files - pictures == texts | {t + SIDECAR_SUFFIX for t in texts} | shipped
    # The notebooks' pictures are in each application's p/; the front page's cards' are in p/ at the root.
    assert all(re.fullmatch(r"((wind-tunnel|body-lab)/)?p/[0-9a-f]{64}\.png", f) for f in pictures)
    assert any(f.startswith("p/") for f in pictures)
    assert not (site.parent / ".site.staging").exists()


def test_the_real_build_has_no_replay_page_and_no_link_to_one(site):
    """Decision 48: the replay steps are not in this version."""
    assert not [p for p in site.rglob("*") if "replay" in p.name]
    for page in PAGES:
        assert "replay" not in (site / page).read_text(encoding="utf-8")


def test_every_link_of_the_real_build_names_a_file_of_the_site(site):
    """A relative link names a file next to its page; the only other links are to the front page and to
    another application's first page."""
    files = {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()}
    for page in PAGES:
        folder = page.rsplit("/", 1)[0] + "/" if "/" in page else ""
        for match in _HREF.finditer((site / page).read_text(encoding="utf-8")):
            target = match.group(1)
            if not target:
                continue
            assert ".." not in target, (page, target)
            if target.startswith("/"):
                assert re.fullmatch(r"/index\.html|/(wind-tunnel|body-lab)/index\.html", target), (
                    page,
                    target,
                )
                continue
            assert folder + target in files or target in files and folder == "", (page, target)
