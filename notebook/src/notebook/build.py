"""The four phases of the build (design "Overview"; Requirements 2.1, 2.7, 20.3, 21.1, 21.2).

1. **Check inputs** (`check_inputs`): the output folder and the staging folder, the scanner, the records, the
   site ids, the layouts and every picture sheet, the word list over every commentary string of `text.py`,
   each application's settings and choice files, and the bench's table check on every `end` snapshot.
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

from notebook import (
    addresses,
    choices,
    display,
    layouts,
    readerrequest,
    readerruns,
    records,
    scan,
    tables,
    text,
    views,
    words,
)
from notebook.choices import Apps
from notebook.errors import NotebookError
from notebook.ink import Ink, Segment, markup
from notebook.inputs import Inputs
from notebook.layouts import Layout
from notebook.pages import front, how, legend, parts, shelf
from notebook.pages.photo import PictureFile
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
    apps: Apps
    scanner: Scanner
    allow_fake: bool
    runs: tuple[readerruns.Run, ...]
    requests: dict[str, readerrequest.Request]
    retakes: display.Retakes


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
    apps = choices.load_apps(list(inputs.apps), list(loaded))
    for record in loaded:
        tables.check_end(record)
    runs = tuple(readerruns.load(inputs.sessions))
    requests = readerrequest.load(inputs.requests, list(runs))
    retakes: display.Retakes = {}
    for app in apps.apps:
        mine = [r for r in loaded if r.application == app.application]
        retakes.update(display.load(app.display, mine, table))
    return Checked(loaded, table, word_list, apps, scanner, allow_fake, runs, requests, retakes)


# Phase 2


def model(checked: Checked) -> Model:
    return Model(checked, {r.name: views.full(r) for r in checked.records})


# Phase 3

# One page kind: (model) -> {site path: (segments, pictures)}.
Pages = Callable[[Model], dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]]


def _front(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    return {addresses.COVER: (front.page(m.checked.apps.apps), ())}


def _applications(m: Model) -> dict[str, tuple[list[Segment], tuple[PictureFile, ...]]]:
    """Every page of every application, in its folder: the notebooks, the ink legend and how the lab works."""
    out: dict[str, tuple[list[Segment], tuple[PictureFile, ...]]] = {}
    checked = m.checked
    for app in checked.apps.apps:
        mine = [r for r in checked.records if r.application == app.application]
        out.update(
            shelf.pages(
                app,
                checked.apps.apps,
                mine,
                checked.apps.choices,
                checked.layouts,
                list(checked.runs),
                checked.requests,
                checked.retakes,
            )
        )
        out[f"{app.slug}/{addresses.LEGEND}"] = (legend.legend(app), ())
        out[f"{app.slug}/{addresses.HOW}"] = (how.page(mine, app, list(checked.records)), ())
    return out


# Every page kind of the site, in this order.
PAGES: tuple[tuple[str, Pages], ...] = (
    ("the front page", _front),
    ("the applications", _applications),
)


def _check_words(word_list: words.WordList, path: str, segments: list[Segment]) -> None:
    for segment in segments:
        if segment.ink is Ink.COMMENTARY:
            word_list.check(segment.text, f"{segment.source} (on {path})")


def _scope(path: str) -> str:
    """The folder a site path is in, with its slash: "" at the root, "body-lab/" for an application's file."""
    return path.rsplit("/", 1)[0] + "/" if "/" in path else ""


def render(m: Model) -> dict[str, bytes]:
    """Every file of the site, checked and scanned, as bytes by path (sidecars included)."""
    site = Site()
    pictures: dict[str, tuple[PictureFile, str]] = {}
    scopes: set[str] = set()
    for kind, pages in PAGES:
        for path, (segments, shown) in pages(m).items():
            owner = f"{kind}: {path}"
            scope = _scope(path)
            scopes.add(scope)
            if m.checked.allow_fake:
                segments = parts.with_fixture_banner(segments, owner)
            _check_words(m.checked.words, path, segments)
            site.add_text(path, segments, owner)
            for picture in shown:
                full = scope + picture.path
                known = pictures.get(full)
                if known is None:
                    pictures[full] = (picture, owner)
                elif known[0].data != picture.data:
                    raise NotebookError(owner, f"two different pictures are named {full}")
    for path, (picture, owner) in sorted(pictures.items()):
        site.add_bytes(path, picture.data, owner)
    fonts = ASSETS / "fonts"
    for scope in sorted(scopes):
        for path, name in ASSET_FILES.items():
            source = f"{ASSET_SOURCE}/{name}"
            site.add_text(scope + path, [markup((ASSETS / name).read_text(encoding="utf-8"), source)], source)
        for name in addresses.FONT_FILES:
            site.add_bytes(
                f"{scope}{addresses.ASSET_DIR}/{name}",
                (fonts / name).read_bytes(),
                f"{ASSET_SOURCE}/fonts/{name}",
            )
        site.add_bytes(
            scope + addresses.FONT_LICENSE,
            (fonts / "LICENSE.txt").read_bytes(),
            f"{ASSET_SOURCE}/fonts/LICENSE.txt",
        )
    chosen = m.checked.apps.choices
    extra = [
        *scan.choice_segments((chosen[k] for k in sorted(chosen)), m.checked.apps.apps),
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
