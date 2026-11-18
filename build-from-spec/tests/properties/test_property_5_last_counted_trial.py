# Feature: build-from-spec, Property 5: Only the last counted trial decides
"""For any run record with a valid relied-on line and at least one counted trial, and any pass ranges, the
result is `pass` exactly when every named measurement of the highest-numbered counted trial is a number with
`low <= value <= high`, and `fail` otherwise. Changing the other trials does not change the result.

**Validates: Requirements 2.3, 15.4, 15.6, 15.8, 15.9, 15.10**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.judge import judge
from support import ALLOWED_IDS, SCALARS, in_range_by_oracle, judge_cases, value_of


def number_of(tid: str) -> int:
    return int(tid[1:])


@settings(max_examples=100, deadline=None)
@given(judge_cases(("valid",)), st.data())
def test_only_the_last_counted_trial_decides(case, data):
    judgement = judge(case.entries, case.frozen, case.request, ALLOWED_IDS)
    assert judgement.relied.problem is None
    if not case.counted:
        assert judgement.result == "no-trial"
        return
    last = max(case.counted, key=number_of)
    expected = "pass" if in_range_by_oracle(case.values[last], case.request) else "fail"
    assert judgement.result == expected
    assert judgement.last_trial == last

    recorded = case.values[last]
    expected_values = {}
    for p in case.request.passes:
        value = recorded[p.measurement]
        expected_values[p.measurement] = value["not_measured"] if isinstance(value, dict) else float(value)
    assert judgement.last_values == expected_values

    experiments = [e["body"] for e in case.entries if e["kind"] == "experiment"]
    phase = next(body["phase"] for body in experiments if last in body["trials"])
    assert judgement.last_phase == phase

    # Every other trial may hold any values; the result and the last trial do not move.
    altered = []
    for entry in case.entries:
        if entry["kind"] == "trial" and entry["body"]["trial"] != last:
            measurements = {name: data.draw(value_of(case.request)) for name in SCALARS}
            entry = {**entry, "body": {**entry["body"], "measurements": measurements}}
        altered.append(entry)
    again = judge(altered, case.frozen, case.request, ALLOWED_IDS)
    assert again.result == judgement.result
    assert again.last_trial == last
    assert again.last_values == judgement.last_values
