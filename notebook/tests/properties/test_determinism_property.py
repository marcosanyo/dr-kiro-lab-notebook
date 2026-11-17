"""Property test of a deterministic build (task 9.3).

The records are fixtures from `tests/fixtures/synth.py`: one to three sealed fake records of the fake
application, written to disk, verified by the bench and built only through `build(..., allow_fake=True)`.
Choice and cover files are derived from each generated record; the layout is the fixture's one-cell entry.
No number here is a recorded result.

For each generated input set, the same inputs are built twice into two output folders, and a copy of the
whole input tree at another absolute path is built a third time while every folder listing (`Path.iterdir`)
returns its entries in a drawn random order. All three sites must hold the same paths and the same bytes, and
no file may hold an output folder's path, an input folder's path, the home folder or the repository path.
"""

# Feature: lab-notebook, Property 15: The build is deterministic
# **Validates: Requirements 11.1, 16.8, 21.1, 21.2, 21.4**

import random
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from fixtures.session import FAKE_SOURCES, REPO, STOP_LIST
from fixtures.synth import record_sets, write_all
from notebook import build
from notebook import records as notebook_records
from notebook.inputs import Inputs
from notebook.records import RecordModel

LAYOUTS = '[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\nsource = "test fixture: one 2 x 2 picture"\n'
WORDS = "# test fixture word list\nlimp\n"
REASON = "test fixture: nothing chosen"


def _choice(record: RecordModel) -> str:
    """A valid choice file for a generated record: the first two trials, the last trial and the first miss,
    or "none" with a reason where the record has none."""
    trials = [t.id for t in record.trials]
    misses = [o.prediction for o in record.outcomes if o.outcome == "miss"]
    lines = []
    if len(trials) >= 2:
        lines.append(f'contrast = ["{trials[0]}", "{trials[1]}"]')
    else:
        lines += ['contrast = "none"', f'contrast_reason = "{REASON}"']
    if trials:
        lines.append(f'best = "{trials[-1]}"')
    else:
        lines += ['best = "none"', f'best_reason = "{REASON}"']
    if trials and misses:
        lines.append(f'missed = "{misses[0]}"')
    else:
        lines += ['missed = "none"', f'missed_reason = "{REASON}"']
    return "\n".join(lines) + "\n"


def _cover(record: RecordModel) -> str:
    misses = [o.prediction for o in record.outcomes if o.outcome == "miss"]
    prediction = misses[0] if misses else "none"
    return (
        f'[miss]\napplication = "{record.application}"\nsession = "{record.session}"\n'
        f'prediction = "{prediction}"\n\n'
        f'[[card]]\napplication = "{record.application}"\nsession = "{record.session}"\n'
        f'trial = "{record.trials[0].id}"\n'
    )


def _write_inputs(root: Path, synthesized) -> Inputs | None:
    """Write the records and the files the build reads under `root`; None when no record can carry the
    cover (an ended record with a trial is needed)."""
    sessions = write_all(root / "sessions", synthesized)
    loaded = notebook_records.load(sessions, allow_fake=True)
    covers = [r for r in loaded if r.seal.end == "ended" and r.trials]
    if not covers:
        return None
    choices = root / "choices"
    for record in loaded:
        (choices / record.application).mkdir(parents=True, exist_ok=True)
        (choices / record.application / f"{record.session}.toml").write_text(_choice(record))
    (choices / "cover.toml").write_text(_cover(covers[0]))
    (root / "layouts.toml").write_text(LAYOUTS)
    (root / "words.txt").write_text(WORDS)
    return Inputs(
        sessions=sessions,
        choices=choices,
        layouts=root / "layouts.toml",
        words=root / "words.txt",
        scan_configs=(FAKE_SOURCES,),
        stop_list=STOP_LIST,
        out=root / "unused",
    )


def _moved(inputs: Inputs, old: Path, new: Path, out: Path) -> Inputs:
    def move(p: Path) -> Path:
        return new / p.relative_to(old)

    return Inputs(
        sessions=move(inputs.sessions),
        choices=move(inputs.choices),
        layouts=move(inputs.layouts),
        words=move(inputs.words),
        scan_configs=inputs.scan_configs,
        stop_list=inputs.stop_list,
        out=out,
    )


@contextmanager
def _shuffled_listings(rng: random.Random) -> Iterator[None]:
    """Every `Path.iterdir` returns its entries in a random order drawn from `rng`."""
    original = Path.iterdir

    def iterdir(self: Path) -> Iterator[Path]:
        entries = list(original(self))
        rng.shuffle(entries)
        return iter(entries)

    with mock.patch.object(Path, "iterdir", iterdir):
        yield


def _site(out: Path) -> dict[str, bytes]:
    return {p.relative_to(out).as_posix(): p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file()}


@settings(
    max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
)
@given(synthesized=record_sets(max_records=3), rng=st.randoms(use_true_random=False))
def test_the_build_is_deterministic(synthesized, rng):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        first_root = tmp_root / "first"
        inputs = _write_inputs(first_root, synthesized)
        assume(inputs is not None)
        out_a = tmp_root / "site-a"
        out_b = tmp_root / "other" / "site-b"
        out_b.parent.mkdir()
        build.build(Inputs(**{**inputs.__dict__, "out": out_a}), allow_fake=True)
        build.build(Inputs(**{**inputs.__dict__, "out": out_b}), allow_fake=True)

        # The same inputs at another absolute path, with every folder listed in a random order.
        second_root = tmp_root / "elsewhere" / "copy"
        shutil.copytree(first_root, second_root)
        out_c = tmp_root / "elsewhere" / "site-c"
        with _shuffled_listings(rng):
            build.build(_moved(inputs, first_root, second_root, out_c), allow_fake=True)

        site_a, site_b, site_c = _site(out_a), _site(out_b), _site(out_c)
        assert site_a.keys() == site_b.keys() == site_c.keys()
        for path, data in site_a.items():
            assert site_b[path] == data, path
            assert site_c[path] == data, path

        forbidden = [str(p) for p in (out_a, out_b, out_c, first_root, second_root, tmp_root)]
        forbidden += [str(Path.home()), str(REPO), str(tmp_root.resolve())]
        for path, data in site_a.items():
            if path.endswith(".png"):
                continue
            content = data.decode("utf-8")
            for value in forbidden:
                assert value not in content, (path, value)
