"""Property test of the run bands beside a row's scope (task 15.2).

The records are fixtures from `tests/fixtures/synth.py`, written, verified by the bench and loaded with
`allow_fake=True`. The rows cite experiment and prediction ids of the record, and some ids that do not
exist. The expected parameter groups, ticks, marked spans, spans and hatched parts are computed here from the
raw generated entries (`trial`, `experiment`, `register`, `outcome`) and the record's declaration, not from
`notebook.bands`. No number here is a recorded result.
"""

# Feature: lab-notebook, Property 7: Run band ticks are exact and hatched parts are empty
# **Validates: Requirements 9.2-9.7, 9.9**

import dataclasses
import tempfile
from pathlib import Path
from typing import Any

from bench.specfiles.discovered import Row
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fixtures.synth import SynthRecord, cell_text, records, write_all
from notebook import bands, views
from notebook import records as notebook_records

PREDICTION = "prediction"  # the strengths, written out here, not imported from the model
CITED = "cited"
OTHER = "other"
RANK = {OTHER: 0, CITED: 1, PREDICTION: 2}


def _named(params: list[dict[str, Any]]) -> frozenset[str]:
    return frozenset(p["name"]["text"] for p in params)


def _expected(synth: SynthRecord, record: Any, row: Row) -> list[tuple]:
    """The groups of the row, each as (sorted names, names in declared order, bands), where a band is
    (name, ticks as (value, strength), marked span, span, hatched parts as (low, high, side), knob range)."""
    trials = synth.kinds("trial")
    experiments = synth.kinds("experiment")
    by_id = {t["trial"]: t for t in trials}
    cited_ids = {t["trial"] for t in trials if t["experiment"] in row.experiments}
    predicted_ids = {
        o["trial"]
        for o in synth.kinds("outcome")
        if o["prediction"] in row.predictions and o["trial"] is not None
    }
    strength_of: dict[str, str] = {}
    for tid in cited_ids:
        strength_of[tid] = CITED
    for tid in predicted_ids:
        strength_of[tid] = PREDICTION
    cited_predictions = [
        p for r in synth.kinds("register") for p in r["predictions"] if p["id"] in row.predictions
    ]
    knobs = {k.name: (k.low, k.high) for k in record.declaration.knobs if k.kind == "number"}

    keys = {_named(by_id[tid]["params"]) for tid in cited_ids | predicted_ids}
    out = []
    for key in sorted(keys, key=lambda g: tuple(sorted(g))):
        declaring = [e for e in experiments if frozenset(p["text"] for p in e["params"]) == key]
        assert declaring, "every trial's names are declared by an experiment"
        cited_declaring = [e for e in declaring if e["experiment"] in row.experiments]
        chosen = (cited_declaring or declaring)[0]
        names = tuple(p["text"] for p in chosen["params"])
        session = [t for t in trials if _named(t["params"]) == key]
        bands_out = []
        for n in names:
            per_value: dict[float, str] = {}
            for trial in session:
                (value,) = [p["value"] for p in trial["params"] if p["name"]["text"] == n]
                strength = strength_of.get(trial["trial"], OTHER)
                previous = per_value.get(value)
                if previous is None or RANK[strength] > RANK[previous]:
                    per_value[value] = strength
            ticks = tuple(sorted(per_value.items()))
            cited_values = [
                p["value"]
                for trial in session
                if trial["trial"] in cited_ids
                for p in trial["params"]
                if p["name"]["text"] == n
            ]
            marked = (min(cited_values), max(cited_values)) if cited_values else None
            lo, hi = ticks[0][0], ticks[-1][0]
            if n in knobs:
                knob = knobs[n]
                span = knob
            else:
                knob = None
                extra = [
                    w["value"]
                    for p in cited_predictions
                    if frozenset(w["name"]["text"] for w in p["when"]) == key
                    for w in p["when"]
                    if w["name"]["text"] == n
                ]
                values = [v for v, _ in ticks] + extra
                span = (min(values), max(values))
            hatched = []
            if span[0] < lo:
                hatched.append((span[0], lo, "below"))
            if hi < span[1]:
                hatched.append((hi, span[1], "above"))
            bands_out.append((n, ticks, marked, span, tuple(hatched), knob))
        out.append((tuple(sorted(key)), names, tuple(bands_out)))
    return out


def _actual(groups: tuple[bands.Group, ...]) -> list[tuple]:
    return [
        (
            tuple(sorted(group.names)),
            tuple(group.names),
            tuple(
                (
                    band.name.text,
                    tuple((t.value, t.strength) for t in band.ticks),
                    band.marked,
                    band.span,
                    tuple((h.low, h.high, h.side) for h in band.hatched),
                    band.knob,
                )
                for band in group.bands
            ),
        )
        for group in groups
    ]


def _holds(low: float, high: float, side: str, value: float) -> bool:
    """A value inside a hatched part, as the design words it: `[low, high)` below the ticks, `(low, high]`
    above them."""
    if side == "below":
        return low <= value < high
    return low < value <= high


@settings(max_examples=200, deadline=None)
@given(st.data())
def test_run_band_ticks_are_exact_and_hatched_parts_are_empty(data: st.DataObject) -> None:
    synth = data.draw(records(rounds=st.integers(1, 4)))
    exp_ids = [e["experiment"] for e in synth.kinds("experiment")]
    pred_ids = [p["id"] for r in synth.kinds("register") for p in r["predictions"]]
    row_experiments = data.draw(
        st.lists(st.sampled_from([*exp_ids, "E9"]), max_size=3, unique=True).map(tuple)
    )
    row_predictions = data.draw(
        st.lists(st.sampled_from([*pred_ids, "H9.P1"]), max_size=4, unique=True).map(tuple)
    )
    row = Row(
        line=1,
        id="R1",
        rule=data.draw(cell_text()),
        scope=data.draw(cell_text()),
        experiments=row_experiments,
        predictions=row_predictions,
        status="observed",
        replaced_by="",
    )
    with tempfile.TemporaryDirectory() as tmp:
        (record,) = notebook_records.load(write_all(Path(tmp) / "sessions", [synth]), allow_fake=True)
    view = views.full(record)
    groups = bands.row_bands(view, row)
    expected = _expected(synth, record, row)
    assert _actual(groups) == expected

    # Ticks are exactly the recorded values of the parameter over every trial of its group, and no hatched
    # part holds one of them (Requirements 9.3, 9.4, 9.9).
    for group in groups:
        names = frozenset(group.names)
        session = [t for t in synth.kinds("trial") if _named(t["params"]) == names]
        for band in group.bands:
            recorded = [
                p["value"] for t in session for p in t["params"] if p["name"]["text"] == band.name.text
            ]
            assert [t.value for t in band.ticks] == sorted(set(recorded))
            for hatch in band.hatched:
                assert not any(_holds(hatch.low, hatch.high, hatch.side, v) for v in recorded)
                assert hatch.side in ("below", "above")

    # The scope cell and the rule text are never read (Requirement 8.9): rows that differ only in them give
    # the same bands.
    other = dataclasses.replace(row, rule=data.draw(cell_text()), scope=data.draw(cell_text()))
    assert bands.row_bands(view, other) == groups

    # Coverage of the cases the property must reach.
    if len(groups) >= 2:
        event("a row with two parameter groups")
    shared = {n for g in groups for n in g.names if sum(n in h.names for h in groups) > 1}
    if shared:
        event("a name shared by two parameter groups of one row")
    if any(b.knob is not None for g in groups for b in g.bands):
        event("a number knob band")
    if any(b.knob is None for g in groups for b in g.bands):
        event("a Dr. Kiro parameter band")
    if any(b.hatched for g in groups for b in g.bands):
        event("a hatched no-trial part")
    if any(
        len(
            [
                e
                for e in synth.kinds("experiment")
                if frozenset(p["text"] for p in e["params"]) == frozenset(g.names)
            ]
        )
        > 1
        for g in groups
    ):
        event("two experiments declare the same name set")
