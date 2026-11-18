# Feature: build-from-spec, Property 9: Turn loop
"""For any sequence of turn outcomes (exit code, entries added, sealed after the turn),
`run_turns` sends the start line once, first, and the continue line on every later turn it
runs. It stops at the first turn that seals the record, exits non-zero, or is the second turn
in a row without a new entry, with the matching reason. The recorded prompts are one per turn,
in order, with matching entry counts, and the number of continue lines is the number of
prompts minus one.

**Validates: Requirements 9.6, 11.6**
"""

import hashlib

from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.turns import CONTINUE_LINE, IDLE_REASON, START_LINE, exit_reason, run_turns

# A turn that exits non-zero ends every generated sequence, so the loop always stops.
TERMINAL = (1, 0, False)


@st.composite
def outcomes(draw):
    """Turn outcomes as (exit code, entries added, sealed). A sealing turn adds at least its seal entry."""
    turns = draw(
        st.lists(
            st.tuples(st.sampled_from([0, 0, 0, 1, 2, 255]), st.integers(0, 2), st.booleans()),
            min_size=1,
            max_size=12,
        )
    )
    turns = [(code, added + 1 if sealed else added, sealed) for code, added, sealed in turns]
    return [*turns, TERMINAL]


class FakeBench:
    """A state record and a reader driven by a list of turn outcomes."""

    def __init__(self, turns):
        self.turns = turns
        self.turn = 0
        self.count = 0
        self.sealed = False
        self.kinds: list[str] = []
        self.saves: list[tuple] = []

    def launch(self, kind):
        self.kinds.append(kind)
        code, added, sealed = self.turns[self.turn]
        self.turn += 1
        self.count += added
        self.sealed = sealed
        return code

    def entries(self):
        return (self.count, self.sealed)

    def save(self, prompts):
        self.saves.append(prompts)


def expected(turns):
    """The rules of design 3.10 on the outcomes: rows of (kind, exit, before, after), sealed, reason."""
    rows = []
    count = 0
    previous_idle = False
    for k, (code, added, sealed) in enumerate(turns):
        kind = "start" if k == 0 else "continue"
        before = count
        count += added
        rows.append((kind, code, before, count))
        if sealed:
            return rows, True, None
        if code != 0:
            return rows, False, exit_reason(code)
        idle = added == 0
        if idle and previous_idle:
            return rows, False, IDLE_REASON
        previous_idle = idle
    raise AssertionError("the terminal turn must stop the loop")


@settings(max_examples=200, deadline=None)
@given(outcomes())
def test_turn_loop_sends_the_lines_its_rules_allow_and_stops_as_they_say(turns):
    bench = FakeBench(turns)
    end = run_turns(bench.launch, bench.entries, bench.save)

    rows, sealed, reason = expected(turns)
    assert end.sealed is sealed
    assert end.stop_reason == reason
    assert bench.kinds == [row[0] for row in rows]
    assert len(end.prompts) == len(rows) == bench.turn

    for prompt, (kind, code, before, after) in zip(end.prompts, rows, strict=True):
        assert prompt.kind == kind
        assert prompt.exit == code
        assert (prompt.entries_before, prompt.entries_after) == (before, after)
        line = START_LINE if kind == "start" else CONTINUE_LINE
        assert prompt.sha256 == hashlib.sha256(line.encode("utf-8")).hexdigest()

    # Only the first prompt is the start line, and every later prompt is the continue line.
    assert end.prompts[0].kind == "start"
    assert all(prompt.kind == "continue" for prompt in end.prompts[1:])
    assert sum(prompt.kind == "continue" for prompt in end.prompts) == len(end.prompts) - 1

    # Every turn followed by a continue line exited 0, and no two such turns in a row were idle.
    idle = [prompt.entries_after == prompt.entries_before for prompt in end.prompts]
    for index, prompt in enumerate(end.prompts[:-1]):
        assert prompt.exit == 0
        if index > 0:
            # The first turn has no turn before it, so only later turns are compared.
            assert not (idle[index] and idle[index - 1])

    # One save per turn, in order; the last save equals the result.
    assert [len(prompts) for prompts in bench.saves] == list(range(1, len(rows) + 1))
    assert bench.saves[-1] == end.prompts
