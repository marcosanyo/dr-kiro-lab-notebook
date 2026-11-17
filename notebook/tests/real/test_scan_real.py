"""The table section, the moving pictures and the tracks of every committed record pass the blind scan as the
site will be scanned (design 11, N7, N28): pass 1 over every segment at its author's level, pass 2 over the
joined file through its author ranges, read back with the bench's `sidecar_pieces`. Every link is relative
and holds no `..` (Requirement 3.2, design N28)."""

import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from bench.scan.levels import AUTHOR_LEVEL, SIDECAR_SUFFIX, sidecar_pieces
from bench.scan.scan import Scanner

from notebook import choices, ink, layouts, plots, records, views
from notebook.pages import cover, lab, parts, photo, session

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
CHOICES = ROOT / "notebook" / "choices"
LAYOUTS = ROOT / "notebook" / "layouts.toml"


@pytest.fixture(scope="module")
def scanner() -> Scanner:
    return Scanner.from_config(
        [
            ROOT / "body-lab" / "adapter" / "scan_sources.toml",
            ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
        ],
        ROOT / ".kiro" / "blind-scan" / "stop-list.txt",
    )


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


def _segments(
    record: records.RecordModel, chosen: choices.Choices, table: layouts.Layout
) -> list[ink.Segment]:
    def pin(trial: records.Trial) -> list[ink.Segment]:
        figure, _ = photo.photo(record, trial, table)
        return [*figure, *plots.track(record, trial)]

    out: list[ink.Segment] = [*parts.decoration()]
    if record.snapshots or record.seal.end == "ended":
        out += session.table_section(views.full(record), chosen, pin)
    for trial in record.trials:
        out += pin(trial)
    out += parts.legend_link()
    return out


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.links += [value for name, value in attrs if name in ("href", "src") and value is not None]


def test_every_record_passes_both_scan_passes_and_links_stay_in_the_site(scanner, loaded, tmp_path) -> None:
    # The scanner flags the generic block element and a parent-folder link, so a clean result means something.
    assert {f.kind for f in scanner.scan_text('<div><a href="../x.html">', "builder", "probe")} == {
        "term",
        "path",
    }
    chosen = choices.load(CHOICES, loaded)
    table = layouts.load(LAYOUTS)
    findings = []
    names = []
    for record in loaded:
        segments = _segments(record, chosen[(record.application, record.session)], table[record.application])
        # Pass 1: every segment at its author's level, named by its source.
        for segment in segments:
            level = AUTHOR_LEVEL[ink.SCAN_AUTHOR[segment.ink]]
            findings += scanner.scan_text(segment.text, level, segment.source)
        # Pass 2: the joined file through its author ranges, as the sidecar describes it.
        written, ranges = ink.join(segments)
        path = tmp_path / f"{record.application}-{record.session}.html"
        path.write_text(written, encoding="utf-8")
        sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
        sidecar.write_text(
            json.dumps({"ranges": ranges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        for piece in sidecar_pieces(path, written):
            findings += scanner.scan_piece(piece)
        parser = _Links()
        parser.feed(written)
        parser.close()
        assert parser.links, record.name
        for link in parser.links:
            assert ".." not in link and not link.startswith("/") and ":" not in link, (record.name, link)
        assert "<div" not in written
        names.append(record.name)
    assert [str(f) for f in findings] == []
    assert len(names) == 5


def test_the_cover_passes_both_scan_passes_and_links_stay_in_the_site(scanner, loaded, tmp_path) -> None:
    segments, _ = cover.page(loaded, choices.load_cover(CHOICES, loaded), layouts.load(LAYOUTS))
    findings = []
    for segment in segments:
        level = AUTHOR_LEVEL[ink.SCAN_AUTHOR[segment.ink]]
        findings += scanner.scan_text(segment.text, level, segment.source)
    written, ranges = ink.join(segments)
    path = tmp_path / "index.html"
    path.write_text(written, encoding="utf-8")
    path.with_name(path.name + SIDECAR_SUFFIX).write_text(
        json.dumps({"ranges": ranges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for piece in sidecar_pieces(path, written):
        findings += scanner.scan_piece(piece)
    assert [str(f) for f in findings] == []
    parser = _Links()
    parser.feed(written)
    parser.close()
    assert parser.links
    for link in parser.links:
        assert ".." not in link and not link.startswith("/") and ":" not in link, link
    assert "<div" not in written and "xmlns" not in written and "http" not in written


def test_the_lab_pages_and_the_legend_pass_both_scan_passes_and_links_stay_in_the_site(
    scanner, loaded, tmp_path
) -> None:
    pages = {**lab.pages(loaded), "legend.html": lab.legend()}
    assert sorted(pages) == ["body-lab.html", "legend.html", "wind-tunnel.html"]
    findings = []
    for name, segments in pages.items():
        for segment in segments:
            level = AUTHOR_LEVEL[ink.SCAN_AUTHOR[segment.ink]]
            findings += scanner.scan_text(segment.text, level, segment.source)
        written, ranges = ink.join(segments)
        path = tmp_path / name
        path.write_text(written, encoding="utf-8")
        path.with_name(path.name + SIDECAR_SUFFIX).write_text(
            json.dumps({"ranges": ranges}, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        for piece in sidecar_pieces(path, written):
            findings += scanner.scan_piece(piece)
        parser = _Links()
        parser.feed(written)
        parser.close()
        assert parser.links, name
        for link in parser.links:
            assert ".." not in link and not link.startswith("/") and ":" not in link, (name, link)
        assert "<div" not in written and "xmlns" not in written and "http" not in written, name
    assert [str(f) for f in findings] == []


def test_the_stylesheet_passes_the_builder_level_scan(scanner) -> None:
    css = ROOT / "notebook" / "src" / "notebook" / "assets" / "notebook.css"
    assert scanner.scan_text(css.read_text(encoding="utf-8"), AUTHOR_LEVEL["bench"], str(css)) == []
