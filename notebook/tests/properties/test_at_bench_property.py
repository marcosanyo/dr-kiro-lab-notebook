"""Property test of the at-bench data (task 25.4; design N34, N35).
The records are fixtures from `tests/fixtures/synth.py` (fake = true): any ending, any number of rounds,
refusals before a round and before the end. No number here is a recorded result.
Interface compared: the segments that `book.body` returns, the list the page is made of, read in order. Of
each segment only the ink and the text are kept, and only the two inks that carry the record: Dr. Kiro's ink
(hypotheses, rules, refusal text quoted from Dr. Kiro) and the pencil (trial values, outcome names, ids,
bench refusal text, rows and their statuses). The commentary ink and the markup are the wording and the
structure, which differ on purpose (labels, headings, the open entry, "waiting"), so they are not compared.
The one pencil segment that is not data of the record, the session id in the page head of the page at the
bench, is dropped by cutting the page's `book-title` element from both lists. This is the stable interface
because both modes build the segments from the same model: a difference in a value, an outcome, a refusal or
a table row shows in them, and a change of wording does not.
For each prefix (from the start entry alone to every entry) the at-bench body (`AT_BENCH`, no choice file) is
compared with the sealed body (`SEALED`, a choice file with nothing in it but its words) of the same model
from `records.from_entries`. One named difference of the data is allowed (Requirement 23.8): while the prefix
has no seal entry, a prediction without an outcome entry shows "waiting" at the bench and the pencil word
"not run" on the sealed page; the test compares the two counts and then the rest.
"""

# Feature: lab-notebook, Property 19: The at-bench page shows what the sealed page shows for the same prefix
# **Validates: Requirements 23.1, 23.8**
import tempfile
from pathlib import Path

from hypothesis import HealthCheck, event, given, settings

from fixtures.synth import records, write_all
from notebook import layouts, text
from notebook import records as notebook_records
from notebook.choices import App, Choices
from notebook.ink import Ink, Segment
from notebook.pages import book

LAYOUTS = (
    "[fake]\nframes = 1\nrows = 1\ncolumns = 1\ngap = 0\ninterval = 200\n"
    'source = "test fixture: one 8 x 8 picture"\n'
)
DATA_INKS = (Ink.PENCIL, Ink.DRKIRO)


def _data(segments: list[Segment]) -> list[tuple[str, str]]:
    """(ink, text) of the data segments, without the page head's title element."""
    out = []
    inside = False
    for s in segments:
        if s.ink is Ink.MARKUP:
            if 'class="book-title"' in s.text:
                inside = True
            if inside and "</h2>" in s.text:
                inside = False
            continue
        if not inside and s.ink in DATA_INKS:
            out.append((s.ink.value, s.text))
    return out


NOT_RUN = ("p", "not run")


def _waiting(segments: list[Segment]) -> int:
    return sum(1 for s in segments if s.ink is Ink.COMMENTARY and s.text == text.PREDICTION_WAITING)


@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=list(HealthCheck),
)
@given(records())
def test_the_page_at_the_bench_shows_the_data_of_the_sealed_page(synth):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (full,) = notebook_records.load(write_all(root / "sessions", [synth]), allow_fake=True)
        folder = root / "sessions" / full.application / full.session
        app = App(
            "fake",
            1,
            "case",
            "door",
            "line",
            "about",
            "s1",
            "runs",
            "day",
            "blue",
            "none",
            None,
            None,
            root,
            "app",
        )
        layout = layouts.layout_for(layouts.parse(LAYOUTS, "test fixture"), full.application, full.name)
        for upto in range(1, len(full.entries) + 1):
            prefix = notebook_records.from_entries(
                folder, full.name, list(full.entries[:upto]), allow_fake=True
            )
            chosen = Choices(
                prefix.name, "choice", "t", "s", "u", "l", "m", "2026-01-01", "violet", None, (), (), None
            )
            at_bench, _ = book.body(prefix, layout, None, app, [], {}, {}, None, book.AT_BENCH)
            sealed, _ = book.body(prefix, layout, chosen, app, [], {}, {}, None, book.SEALED)
            shown = _data(at_bench)
            other = _data(sealed)
            if prefix.seal is None:
                # The named difference (Requirement 23.8): a prediction with no outcome entry shows "waiting"
                # at the bench and the pencil word "not run" on the sealed page. Same data, same count.
                assert _waiting(at_bench) == other.count(NOT_RUN), f"waiting, prefix of {upto} entries"
                other = [d for d in other if d != NOT_RUN]
            else:
                assert _waiting(at_bench) == 0
            assert shown == other, f"prefix of {upto} entries"
            if prefix.trials:
                event("a prefix with a trial")
            if prefix.refusals:
                event("a prefix with a refusal")
        assert shown, "the whole record shows data"
