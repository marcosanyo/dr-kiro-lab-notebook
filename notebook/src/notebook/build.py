"""The four phases of the build (design "Overview"; Requirements 2.1, 2.7, 20.3, 21.1, 21.2).

1. **Check inputs** (`check_inputs`): the output folder and the staging folder, the scanner, the records, the
   site ids, the layouts and every picture sheet, the word list over every commentary string of `text.py`,
   the choice files and the cover file, and the bench's table check on every `end` snapshot.
2. **Model** (`model`): one `View` per record, the whole record.
3. **Render** (`render`): every file of the site as segments, in memory; the word check over every
   commentary segment; both blind scan passes.
4. **Write** (`site.write`): a fresh staging folder, then one rename onto the output folder.

Phases 1-3 write nothing, so a failure there leaves the output folder as it was (absent or empty). `PAGES`
is the one place where a page of the site is added: a later task adds its page there.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from bench.scan.scan import Scanner

from notebook import addresses, choices, layouts, records, scan, tables, text, views, words
from notebook.choices import Choices, Cover
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, markup
from notebook.inputs import Inputs
from notebook.layouts import Layout
from notebook.pages import cover, lab, parts, session
from notebook.pages.photo import PictureFile, Pins
from notebook.records import RecordModel
from notebook.site import Site, check_target, write
from notebook.views import View

ASSETS = Path(__file__).resolve().parent / "assets"
ASSET_SOURCE = "notebook/src/notebook/assets"
# Site path -> the file in `assets/`, copied as written (one `bench` author range each).
ASSET_FILES = {addresses.STYLESHEET: "notebook.css", addresses.SCRIPT: "notebook.js"}


@dataclass(frozen=True)
class Checked:
    """Every input, read and checked (phase 1)."""

    records: tuple[RecordModel, ...]
    layouts: dict[str, Layout]
    words: words.WordList
    choices: dict[tuple[str, str], Choices]
    cover: Cover
    scanner: Scanner
    allow_fake: bool


@dataclass(frozen=True)
class Model:
    """The checked inputs and the view of every record (phase 2)."""

    checked: Checked
    views: dict[str, View]  # record name -> the view of the whole record


# Phase 1


def commentary_strings() -> list[tuple[str, str]]:
    """Every commentary string of `text.py` as (source, text)."""
    out = []
    for name, value in sorted(vars(text).items()):
        if name.isupper() and isinstance(value, str) and name != "SOURCE_FILE":
            out.append((text.source(name), value))
    return out


def check_inputs(inputs: Inputs, *, allow_fake: bool) -> Checked:
    """Read and check every input before anything is rendered or written (Requirement 2.1)."""
    check_target(inputs.out)
    scanner = scan.load(inputs.scan_configs, inputs.stop_list)
    loaded = tuple(records.load(inputs.sessions, allow_fake=allow_fake))
    for record in loaded:
        start = f"{record.name}/log.jsonl line 1"
        addresses.site_id("application", record.application, start)
        addresses.site_id("session", record.session, start)
    table = layouts.load(inputs.layouts)
    for record in loaded:
        layout = layouts.layout_for(table, record.application, record.name)
        for trial in record.trials:
            layouts.check_sheet(layout, record.name, trial.id, trial.picture.media, trial.picture.data)
    word_list = words.load(inputs.words)
    for source, value in commentary_strings():
        word_list.check(value, source)
    chosen = choices.load(inputs.choices, list(loaded))
    cover_file = choices.load_cover(inputs.choices, list(loaded))
    for record in loaded:
        tables.check_end(record)
    return Checked(loaded, table, word_list, chosen, cover_file, scanner, allow_fake)


# Phase 2


def model(checked: Checked) -> Model:
    return Model(checked, {r.name: views.full(r) for r in checked.records})


# Phase 3

# One page kind: (model) -> {site path: (segments, pictures)}.
Pages = Callable[[Model], dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]]


def _cover(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    return {addresses.COVER: cover.page(list(m.checked.records), m.checked.cover, m.checked.layouts)}


def _labs(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    return {path: (segments, ()) for path, segments in lab.pages(list(m.checked.records)).items()}


def _legend(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    return {addresses.LEGEND: (lab.legend(), ())}


def _sessions(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    out = {}
    for record in m.checked.records:
        layout = layouts.layout_for(m.checked.layouts, record.application, record.name)
        chosen = m.checked.choices[(record.application, record.session)]
        path = addresses.session(record.application, record.session, f"{record.name}/log.jsonl line 1")
        out[path] = session.page(m.views[record.name], chosen, Pins(record, layout))
    return out


# Every page kind of the site, in this order. A later task adds its page kind here (how.html, built.html,
# the replay steps).
PAGES: tuple[tuple[str, Pages], ...] = (
    ("the cover", _cover),
    ("the lab pages", _labs),
    ("the ink legend", _legend),
    ("the session pages", _sessions),
)


def _check_words(word_list: words.WordList, path: str, segments: list[Segment]) -> None:
    for segment in segments:
        if segment.ink is Ink.COMMENTARY:
            word_list.check(segment.text, f"{segment.source} (on {path})")


def render(m: Model) -> dict[str, bytes]:
    """Every file of the site, checked and scanned, as bytes by path (sidecars included)."""
    site = Site()
    pictures: dict[str, tuple[PictureFile, str]] = {}
    for kind, pages in PAGES:
        for path, (segments, shown) in pages(m).items():
            owner = f"{kind}: {path}"
            if m.checked.allow_fake:
                segments = parts.with_fixture_banner(segments, owner)
            _check_words(m.checked.words, path, segments)
            site.add_text(path, segments, owner)
            for picture in shown:
                known = pictures.get(picture.path)
                if known is None:
                    pictures[picture.path] = (picture, owner)
                elif known[0].data != picture.data:
                    raise NotebookError(owner, f"two different pictures are named {picture.path}")
    for path, (picture, owner) in sorted(pictures.items()):
        site.add_bytes(path, picture.data, owner)
    for path, name in ASSET_FILES.items():
        source = f"{ASSET_SOURCE}/{name}"
        site.add_text(path, [markup((ASSETS / name).read_text(encoding="utf-8"), source)], source)
    extra = [
        *scan.choice_segments(m.checked.choices[k] for k in sorted(m.checked.choices)),
        *scan.drkiro_word_segments(m.checked.records),
    ]
    joined = scan.check(m.checked.scanner, site.texts(), extra)
    return site.files(joined)


# The build


def build(inputs: Inputs, *, allow_fake: bool = False) -> None:
    """Run the four phases. `allow_fake` is for labelled test fixtures only: it accepts fake records and puts
    the "test fixture" banner on every page. The command line never sets it (design N19)."""
    checked = check_inputs(inputs, allow_fake=allow_fake)
    files = render(model(checked))
    write(files, inputs.out)
