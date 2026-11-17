"""Property test: a failed build writes nothing (task 9.4, design Property 16, N4).

The valid input set is the labelled fake session of `fixtures.session` (fake in its declaration and every
trial; its numbers are not results) with fixture choice, cover, layout and word files. It builds cleanly
with `allow_fake=True`, which is checked once. Each example copies it into a fresh temporary folder, applies
one generated corruption, and builds into an output folder that is absent or an empty folder. The build must
fail with a `NotebookError` that names the corrupted file (or the source of the planted text), and afterwards
the output folder is as it was (absent, or empty) and no staging folder is left.

Corruptions: a flipped byte in the log or in a blob, a missing seal, a fake record built without
`allow_fake`, a frame layout the picture does not divide into, a choice id that is not in the record, a scan
term planted in a choice reason, and a scan term planted in a builder string of `text.py`. The planted term
is taken at test time from the scanner's own derived terms, so no term is written here.
"""

# Feature: lab-notebook, Property 16: A failed build writes nothing
# **Validates: Requirements 2.1, 2.2, 2.3, 2.7, 7.3, 20.2**

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import pytest
from hypothesis import HealthCheck, event, given, settings
from hypothesis import strategies as st

from fixtures.session import FAKE_SOURCES, STOP_LIST, accepted_session
from notebook import build, scan, text
from notebook.errors import NotebookError
from notebook.inputs import Inputs
from notebook.site import staging_folder

SETTINGS = settings(max_examples=120, deadline=None, suppress_health_check=[HealthCheck.too_slow])

CHOICE = 'contrast = ["T1", "T2"]\nbest = "T7"\nmissed = "H2.P1"\n'
COVER = (
    '[miss]\napplication = "fake"\nsession = "s1"\nprediction = "H2.P1"\n\n'
    '[[card]]\napplication = "fake"\nsession = "s1"\ntrial = "T1"\n'
)
# The fake application's picture is 8 x 8 pixels; this layout shows it as one cell.
SIDE = 8
LAYOUTS = '[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\nsource = "test fixture: one 8 x 8 picture"\n'
WORDS = "# test fixture word list\nlimp\n"
RECORD = Path("sessions") / "fake" / "s1"
CHOICE_FILE = Path("choices") / "fake" / "s1.toml"


@dataclass(frozen=True)
class Base:
    root: Path  # the valid input set: sessions/, choices/, layouts.toml, words.txt
    term: str  # one single-word term the scan derives from the fake scan sources


def _inputs(root: Path, out: Path) -> Inputs:
    return Inputs(
        sessions=root / "sessions",
        choices=root / "choices",
        layouts=root / "layouts.toml",
        words=root / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=out,
    )


@pytest.fixture(scope="module")
def base(tmp_path_factory) -> Base:
    work = tmp_path_factory.mktemp("failed-build")
    made = accepted_session(work / "lab")
    root = work / "valid"
    shutil.copytree(made.sessions, root / "sessions")
    (root / CHOICE_FILE).parent.mkdir(parents=True)
    (root / CHOICE_FILE).write_text(CHOICE)
    (root / "choices" / "cover.toml").write_text(COVER)
    (root / "layouts.toml").write_text(LAYOUTS)
    (root / "words.txt").write_text(WORDS)
    # The uncorrupted input set builds (so every failure below comes from its corruption).
    build.build(_inputs(root, work / "site"), allow_fake=True)
    assert (work / "site" / "index.html").is_file()
    scanner = scan.load([FAKE_SOURCES], STOP_LIST)
    term = sorted(t[0] for t in scanner.terms if len(t) == 1 and t[0].isalpha())[0]
    return Base(root, term)


# Corruptions. `apply` changes the copied input root and returns the text the build's error must contain:
# the record, the choice file, or the source of the planted builder string. `allow_fake` is how the build is
# called; `plant_text` puts the scan term into a `text.py` string for the build.


@dataclass(frozen=True)
class Corruption:
    kind: str
    apply: object  # (root: Path, term: str) -> str, the text the error must contain
    allow_fake: bool = True
    plant_text: bool = False


def _flip(path: Path, offset: int, mask: int) -> None:
    data = bytearray(path.read_bytes())
    data[offset % len(data)] ^= mask
    path.write_bytes(bytes(data))


def flipped_log(offset: int, mask: int) -> Corruption:
    def apply(root: Path, term: str) -> str:
        _flip(root / RECORD / "log.jsonl", offset, mask)
        return RECORD.as_posix()

    return Corruption("flipped byte in the log", apply)


def flipped_blob(index: int, offset: int, mask: int) -> Corruption:
    def apply(root: Path, term: str) -> str:
        blobs = sorted((root / RECORD / "blobs").iterdir())
        _flip(blobs[index % len(blobs)], offset, mask)
        return RECORD.as_posix()

    return Corruption("flipped byte in a blob", apply)


def missing_seal() -> Corruption:
    def apply(root: Path, term: str) -> str:
        log = root / RECORD / "log.jsonl"
        lines = log.read_bytes().splitlines(keepends=True)
        log.write_bytes(b"".join(lines[:-1]))
        return RECORD.as_posix()

    return Corruption("missing seal", apply)


def fake_without_allow() -> Corruption:
    def apply(root: Path, term: str) -> str:
        return RECORD.as_posix()

    return Corruption("fake record without allow_fake", apply, allow_fake=False)


def _divides(side: int, cells: int, gap: int) -> bool:
    """Whole cells of at least 1 pixel exist: side == cells * c + (cells - 1) * gap."""
    rest = side - (cells - 1) * gap
    return rest >= cells and rest % cells == 0


def bad_layout(rows: int, columns: int, gap: int) -> Corruption:
    def apply(root: Path, term: str) -> str:
        (root / "layouts.toml").write_text(
            f"[fake]\nframes = {rows * columns}\nrows = {rows}\ncolumns = {columns}\ngap = {gap}\n"
            'source = "test fixture: a layout the picture does not divide into"\n'
        )
        return RECORD.as_posix()

    return Corruption("picture does not divide into its layout", apply)


def wrong_choice_id(key: str, bogus: str) -> Corruption:
    values = {
        "contrast": f'contrast = ["T1", "{bogus}"]\nbest = "T7"\nmissed = "H2.P1"\n',
        "best": f'contrast = ["T1", "T2"]\nbest = "{bogus}"\nmissed = "H2.P1"\n',
        "missed": f'contrast = ["T1", "T2"]\nbest = "T7"\nmissed = "{bogus}"\n',
    }

    def apply(root: Path, term: str) -> str:
        (root / CHOICE_FILE).write_text(values[key])
        return str(root / CHOICE_FILE)

    return Corruption(f"wrong choice id in {key}", apply)


def term_in_reason(key: str) -> Corruption:
    def apply(root: Path, term: str) -> str:
        lines = {
            "contrast": 'contrast = ["T1", "T2"]\n',
            "best": 'best = "T7"\n',
            "missed": 'missed = "H2.P1"\n',
        }
        lines[key] = f'{key} = "none"\n{key}_reason = "test fixture: no {term} was chosen"\n'
        (root / CHOICE_FILE).write_text("".join(lines.values()))
        return str(root / CHOICE_FILE)

    return Corruption(f"scan term in the {key} reason", apply)


def term_in_text() -> Corruption:
    def apply(root: Path, term: str) -> str:
        return text.source("LEGEND_LINK")

    return Corruption("scan term in a text.py string", apply, plant_text=True)


_masks = st.integers(1, 255)
_offsets = st.integers(0, 1 << 20)

corruptions = st.one_of(
    st.builds(flipped_log, _offsets, _masks),
    st.builds(flipped_blob, st.integers(0, 1 << 10), _offsets, _masks),
    st.just(missing_seal()),
    st.just(fake_without_allow()),
    st.tuples(st.integers(1, 4), st.integers(1, 6), st.integers(0, 6))
    .filter(lambda t: not (_divides(SIDE, t[0], t[2]) and _divides(SIDE, t[1], t[2])))
    .map(lambda t: bad_layout(*t)),
    st.builds(wrong_choice_id, st.sampled_from(["contrast", "best", "missed"]), st.just("T99")),
    st.builds(wrong_choice_id, st.just("missed"), st.sampled_from(["H9.P9", "H1.P1"])),
    st.builds(term_in_reason, st.sampled_from(["contrast", "best", "missed"])),
    st.just(term_in_text()),
)


@SETTINGS
@given(corruption=corruptions, out_exists=st.booleans())
def test_a_failed_build_writes_nothing(base: Base, corruption: Corruption, out_exists: bool) -> None:
    event(corruption.kind)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "inputs"
        shutil.copytree(base.root, root)
        named = corruption.apply(root, base.term)
        out = Path(temp) / "site"
        if out_exists:
            out.mkdir()
        planted = f"ink legend of the {base.term}" if corruption.plant_text else text.LEGEND_LINK
        with mock.patch.object(text, "LEGEND_LINK", planted), pytest.raises(NotebookError) as caught:
            build.build(_inputs(root, out), allow_fake=corruption.allow_fake)
        assert named in str(caught.value), (corruption.kind, str(caught.value))
        if out_exists:
            assert out.is_dir() and not any(out.iterdir()), corruption.kind
        else:
            assert not out.exists(), corruption.kind
        assert not staging_folder(out).exists(), corruption.kind
        assert sorted(p.name for p in Path(temp).iterdir()) == sorted(
            ["inputs"] + (["site"] if out_exists else [])
        )
