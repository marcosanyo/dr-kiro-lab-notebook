"""The table section, the moving pictures and the tracks of every committed record pass the blind scan as the
site will be scanned (design 11, N7, N28), through `notebook.scan`: pass 1 over every segment at its author's
level, pass 2 over the joined file through its author ranges. Every refusal message of every record and every
choice reason pass at their authors' levels (Requirement 12.8). Every link is relative and holds no `..`
(Requirement 3.2, design N28)."""

from html.parser import HTMLParser
from pathlib import Path

import pytest
from bench.scan.levels import AUTHOR_LEVEL

from notebook import build, choices, ink, records, refusals, scan
from notebook.inputs import Inputs

ROOT = Path(__file__).resolve().parents[3]
SESSIONS = ROOT / "sessions"
CHOICES = ROOT / "notebook" / "choices"
REQUESTS = ROOT / "build-from-spec" / "requests"
LAYOUTS = ROOT / "notebook" / "layouts.toml"


@pytest.fixture(scope="module")
def scanner():
    return scan.load(
        [
            ROOT / "body-lab" / "adapter" / "scan_sources.toml",
            ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
        ],
        ROOT / ".kiro" / "blind-scan" / "stop-list.txt",
    )


@pytest.fixture(scope="module")
def loaded() -> list[records.RecordModel]:
    return records.load(SESSIONS)


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.links += [value for name, value in attrs if name in ("href", "src") and value is not None]


def _links_stay_in_the_site(name: str, written: str) -> None:
    parser = _Links()
    parser.feed(written)
    parser.close()
    assert parser.links, name
    for link in parser.links:
        assert ".." not in link and not link.startswith("/") and ":" not in link, (name, link)


def test_every_page_of_the_site_passes_both_scan_passes_and_links_stay_in_the_site(scanner) -> None:
    # The scanner flags the generic block element and a parent-folder link, so a clean result means something.
    assert {f.kind for f in scanner.scan_text('<div><a href="../x.html">', "builder", "probe")} == {
        "term",
        "path",
    }
    inputs = Inputs(
        sessions=SESSIONS,
        requests=REQUESTS,
        choices=CHOICES,
        layouts=LAYOUTS,
        words=ROOT / "notebook" / "commentary-words.txt",
        scan_configs=(
            ROOT / "body-lab" / "adapter" / "scan_sources.toml",
            ROOT / "wind-tunnel" / "adapter" / "scan_sources.toml",
        ),
        stop_list=ROOT / ".kiro" / "blind-scan" / "stop-list.txt",
        out=ROOT / "notebook" / "does-not-exist",
    )
    files = build.render(build.model(build.check_inputs(inputs, allow_fake=False)))  # scans while rendering
    pages = {n: d.decode("utf-8") for n, d in files.items() if n.endswith(".html")}
    assert sorted(pages) == [
        "body-lab-body-1.html",
        "body-lab-body-2.html",
        "how.html",
        "index.html",
        "legend.html",
        "wind-tunnel-wt-002.html",
        "wind-tunnel-wt-003.html",
        "wind-tunnel-wt-004.html",
    ]
    for name, written in pages.items():
        _links_stay_in_the_site(name, written)
        assert "<div" not in written and "xmlns" not in written and "http" not in written, name


def test_every_refusal_message_and_choice_reason_passes_at_its_authors_level(scanner, loaded) -> None:
    # Includes body-2's `register` refusal, whose bench text names a lab spec file path (task 7.3 open item).
    segments = []
    for record in loaded:
        for refusal in record.refusals:
            message = refusals.message(refusal)
            segments += [*message.parts, *([message.note] if message.note else [])]
    assert {AUTHOR_LEVEL[ink.SCAN_AUTHOR[s.ink]] for s in segments} == {"builder", "dr-kiro"}
    assert any("requirements.md" in s.text and s.ink is ink.Ink.PENCIL for s in segments)
    cover = choices.load_cover(CHOICES, loaded)
    reasons = scan.choice_segments(choices.load(CHOICES, loaded).values(), cover)
    assert reasons
    assert scan.segment_findings(scanner, [*segments, *reasons]) == []


def test_dr_kiros_fixed_words_of_every_record_pass_at_the_builder_level(scanner, loaded) -> None:
    # The verdict words and Dr. Kiro's labels of predictions (Requirement 4.2 exception, design N29).
    words = scan.drkiro_word_segments(loaded)
    assert words
    assert {AUTHOR_LEVEL[ink.SCAN_AUTHOR[s.ink]] for s in words} == {"builder"}
    assert scan.segment_findings(scanner, words) == []


def test_the_stylesheet_passes_the_builder_level_scan(scanner) -> None:
    css = ROOT / "notebook" / "src" / "notebook" / "assets" / "notebook.css"
    assert scanner.scan_text(css.read_text(encoding="utf-8"), AUTHOR_LEVEL["bench"], str(css)) == []
