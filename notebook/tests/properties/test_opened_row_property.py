"""Property test of the opened row of the discovered spec table (task 12.3).

The records are fixtures from `tests/fixtures/synth.py`: ended with an accepted `end` table (rows the bench's
end check accepts, so every status word occurs with the outcomes it needs), and stopped sessions whose last
snapshot holds arbitrary rows citing experiments and predictions that may or may not exist. Each record is
written, verified by the bench and loaded with `allow_fake=True`. No number here is a recorded result.

The expected evidence of each row is computed from the generated entries (`register`, `experiment`,
`outcome`) and the rows the bench's table reader returns for the shown snapshot, not from the notebook's
model. The builder's fixed words are taken from `notebook.text`.
"""

# Feature: lab-notebook, Property 6: An opened row shows exactly its cited evidence
# **Validates: Requirements 8.5, 8.6, 8.7, 8.8**

import tempfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from bench.specfiles.discovered import TableError, parse_table
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import DESIGN_FILE, SynthRecord, design_text, records, table_rows, write_all
from notebook import ink, text, views
from notebook import records as notebook_records
from notebook.choices import Choice, Choices
from notebook.pages import session

UNTRIED = ("new-combination", "outside")  # Requirement 8.7
_VOID = frozenset({"img", "br", "hr", "input", "meta", "link", "source", "wbr", "col"})


@dataclass
class Node:
    tag: str
    attrs: dict[str, str]
    children: list["Node | str"] = field(default_factory=list)

    @property
    def classes(self) -> frozenset[str]:
        return frozenset(self.attrs.get("class", "").split())

    def text(self) -> str:
        return "".join(c if isinstance(c, str) else c.text() for c in self.children)

    def elements(self) -> list["Node"]:
        return [c for c in self.children if isinstance(c, Node)]

    def walk(self):
        yield self
        for child in self.elements():
            yield from child.walk()

    def all(self, tag: str | None = None, classes: frozenset[str] | None = None) -> list["Node"]:
        return [
            n
            for n in self.walk()
            if (tag is None or n.tag == tag) and (classes is None or classes <= n.classes)
        ]


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs) -> None:
        node = Node(tag, {k: v or "" for k, v in attrs})
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_endtag(self, tag) -> None:
        if tag in _VOID:
            return
        assert self.stack[-1].tag == tag, f"</{tag}> closes <{self.stack[-1].tag}>"
        self.stack.pop()

    def handle_data(self, data) -> None:
        self.stack[-1].children.append(data)


def _parse(page: str) -> Node:
    tree = _Tree()
    tree.feed(page)
    tree.close()
    assert tree.stack == [tree.root]
    return tree.root


def _none(key: str) -> Choice:
    return Choice(None, "fixture choice", f"fixture choices key {key}")


def _choices(name: str) -> Choices:
    return Choices(name, "fixture choices", _none("contrast"), _none("best"), _none("missed"))


def _short(v: float) -> str:
    return format(v, ".4g")  # design "Number formatting"


def _shown_design(synth: SynthRecord) -> str | None:
    """The design text of the snapshot the session page shows: the `end` snapshot, else the last one."""
    snapshots = synth.kinds("snapshot")
    ends = [s for s in snapshots if s["for"] == "end"]
    shown = ends[0] if ends else (snapshots[-1] if snapshots else None)
    if shown is None:
        return None
    return synth.blobs[shown["files"]["design"]["blob"]].decode("utf-8")


# Expected evidence, from the generated entries


def _expected_experiment(synth: SynthRecord, cited: str) -> tuple[str, list[str]]:
    found = [e for e in synth.kinds("experiment") if e["experiment"] == cited]
    if not found:
        return cited + text.EVIDENCE_NO_EXPERIMENT, []
    (entry,) = found
    return f"{cited} {entry['title']['text']}", [f"#{cited}"]


def _expected_outcome(outcome: dict[str, Any]) -> tuple[str, list[str]]:
    line, hrefs = "", []
    if outcome["trial"] is not None:
        line += text.OUTCOME_TRIAL + outcome["trial"]
        hrefs.append(f"#{outcome['experiment']}-{outcome['trial']}")
    if outcome["value"] is not None:
        line += text.OUTCOME_MEASURED + _short(outcome["value"])
    elif outcome["not_measured"] is not None:
        line += text.OUTCOME_NOT_MEASURED + outcome["not_measured"]
    return line + text.OUTCOME_IS + outcome["outcome"], hrefs


@dataclass(frozen=True)
class Expected:
    text: str
    hrefs: list[str]
    misses: int  # miss outcomes: each a `.miss` span with the word "miss"
    miss_values: int  # miss outcomes with a measured value: each a `.miss-value` span


def _expected_prediction(synth: SynthRecord, cited: str) -> Expected:
    found = [(r, p) for r in synth.kinds("register") for p in r["predictions"] if p["id"] == cited]
    if not found:
        return Expected(cited + text.EVIDENCE_NO_PREDICTION, [], 0, 0)
    ((register, prediction),) = found
    hid = register["hypothesis"]
    outcomes = [o for o in synth.kinds("outcome") if o["prediction"] == cited]
    hrefs = [f"#{outcomes[0]['experiment']}-{cited}" if outcomes else f"#{cited}"]
    entries = [e for e in synth.kinds("experiment") if e["hypothesis"] == hid]
    if entries:
        hrefs.append(f"#{entries[0]['experiment']}")
    low, high = prediction["range"]
    line = (
        cited
        + text.EVIDENCE_OF_HYPOTHESIS
        + hid
        + " "
        + register["title"]["text"]
        + text.EVIDENCE_PREDICTED
        + prediction["measurement"]
        + text.PREDICTION_RANGE
        + f"[{_short(low)}, {_short(high)}]"
    )
    if prediction["when"]:
        line += text.PREDICTION_WHEN + text.LIST_SEPARATOR.join(
            f"{w['name']['text']} = {_short(w['value'])}" for w in prediction["when"]
        )
    line += text.PREDICTION_CLASS + prediction["class"] + text.PREDICTION_LABEL + prediction["label"]
    if outcomes:
        for outcome in outcomes:
            part, links = _expected_outcome(outcome)
            line += part
            hrefs += links
    else:
        line += text.PREDICTION_STATE + "not-run"
    misses = [o for o in outcomes if o["outcome"] == "miss"]
    return Expected(line, hrefs, len(misses), sum(o["value"] is not None for o in misses))


def _expected_untried(synth: SynthRecord, cited: tuple[str, ...]) -> list[str]:
    classes = {p["id"]: p["class"] for r in synth.kinds("register") for p in r["predictions"]}
    out = []
    for pid in cited:
        if classes.get(pid) not in UNTRIED:
            continue
        out += [pid for o in synth.kinds("outcome") if o["prediction"] == pid and o["outcome"] == "hit"]
    return out


# The opened rows on the page


def _opened(page: Node) -> list[Node]:
    """The `<details class="evidence">` of each `tr.row-evidence`, in table order, one per drawn row."""
    (tbody,) = page.all("tbody")
    drawn = 0
    out: list[Node] = []
    for tr in tbody.elements():
        if tr.attrs.get("id", "").startswith("row-"):
            drawn += 1
        elif "row-evidence" in tr.classes:
            assert len(out) == drawn - 1, "an opened row that does not follow its row"
            (details,) = tr.all("details", frozenset({"evidence"}))
            out.append(details)
    assert len(out) == drawn
    return out


def _list(details: Node, kind: str | None) -> Node | None:
    want = frozenset({"evidence-list"} | ({kind} if kind else set()))
    found = [n for n in details.all("ul") if n.classes == want]
    assert len(found) <= 1
    return found[0] if found else None


def _hrefs(node: Node) -> list[str]:
    return [a.attrs["href"] for a in node.all("a")]


def _check_row(synth: SynthRecord, row: Any, details: Node) -> None:
    # Cited experiments, exactly and in the row's order (8.8).
    experiments = _list(details, None)
    if row.experiments:
        assert experiments is not None
        items = experiments.all("li")
        assert len(items) == len(row.experiments)
        for li, cited in zip(items, row.experiments, strict=True):
            line, hrefs = _expected_experiment(synth, cited)
            assert li.text() == line
            assert _hrefs(li) == hrefs
    else:
        assert experiments is None
        assert text.EVIDENCE_EXPERIMENTS_NONE in details.text()

    # Cited predictions, each with what was registered and measured, linked into its entry (8.8); a miss in
    # miss red with the word "miss" (8.5).
    predictions = _list(details, "cited-predictions")
    if row.predictions:
        assert predictions is not None
        items = predictions.all("li")
        assert len(items) == len(row.predictions)
        for li, cited in zip(items, row.predictions, strict=True):
            expected = _expected_prediction(synth, cited)
            assert li.text() == expected.text
            assert _hrefs(li) == expected.hrefs
            red = li.all("span", frozenset({"miss"}))
            assert [s.text() for s in red] == ["miss"] * expected.misses
            assert len(li.all("span", frozenset({"miss-value"}))) == expected.miss_values
            if expected.misses:
                event(f"a cited miss in a {row.status!r} row")
    else:
        assert predictions is None
        assert text.EVIDENCE_PREDICTIONS_NONE in details.text()

    # The fixed explanation for exactly the `observed` rows (8.6).
    observed = details.all("p", frozenset({"evidence-observed"}))
    if row.status == "observed":
        assert [p.text() for p in observed] == [text.EVIDENCE_OBSERVED + text.STATUS_OBSERVED]
    else:
        assert observed == []

    # The untried hits for exactly the `validated` rows (8.7).
    untried = _list(details, "untried-hits")
    if row.status == "validated":
        expected = _expected_untried(synth, row.predictions)
        if expected:
            assert untried is not None
            assert [li.all("a")[0].text() for li in untried.all("li")] == expected
            event("a validated row with untried hits")
        else:
            assert untried is None
            assert text.EVIDENCE_UNTRIED_NONE in details.text()
    else:
        assert untried is None
        assert text.EVIDENCE_UNTRIED_NONE not in details.text()

    # The status word is only in the row's stamp, never in the opened row (15.2).
    assert details.all(classes=frozenset({"stamp"})) == []


_STOPPED_ROWS = table_rows(
    experiments=st.sampled_from(("E1", "E2", "E3", "E9")),
    predictions=st.sampled_from(("H1.P1", "H1.P2", "H1.P3", "H2.P1", "H2.P2", "H3.P1", "H9.P1")),
)


@settings(max_examples=150, deadline=None)
@given(
    st.one_of(
        # An accepted `end` table: every status word with the outcomes it needs.
        records(rounds=st.integers(1, 4), endings=("table",)),
        # A stopped session whose last snapshot holds arbitrary rows, citing ids that may not exist.
        records(
            rounds=st.integers(1, 4), endings=("stopped", "failure"), designs=_STOPPED_ROWS.map(design_text)
        ),
    )
)
def test_an_opened_row_shows_exactly_its_cited_evidence(synth: SynthRecord) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    design = _shown_design(synth)
    if design is None:
        event("no snapshot")
        return
    try:
        rows = parse_table(design, DESIGN_FILE).rows
    except TableError:
        event("the reader does not accept the shown table")
        return
    page, _ = ink.join(session.table_section(views.full(record), _choices(record.name)))
    opened = _opened(_parse(page))
    assert len(opened) == len(rows)
    event(f"{len(rows)} rows")
    for row, details in zip(rows, opened, strict=True):
        _check_row(synth, row, details)
