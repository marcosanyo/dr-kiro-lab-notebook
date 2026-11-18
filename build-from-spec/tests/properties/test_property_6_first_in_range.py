# Feature: build-from-spec, Property 6: First in-range trial, and judging twice
"""For any run record and request, `first_in_range` is the lowest-numbered counted trial with every named
measurement in range, or `None` when there is none; the result is the same as the result computed without
`first_in_range` (from the relied-on check and the last trial alone); and judging the same record and request
twice gives an equal `Judgement`.

**Validates: Requirements 15.5, 15.7**
"""

from hypothesis import given, settings

from build_from_spec.judge import judge
from support import ALLOWED_IDS, CATEGORIES, EXPECTED_PROBLEM, in_range_by_oracle, judge_cases


def number_of(tid: str) -> int:
    return int(tid[1:])


@settings(max_examples=100, deadline=None)
@given(judge_cases(CATEGORIES))
def test_first_in_range_is_the_lowest_in_range_and_judging_twice_agrees(case):
    judgement = judge(case.entries, case.frozen, case.request, ALLOWED_IDS)

    in_range = [
        tid
        for tid in sorted(case.counted, key=number_of)
        if in_range_by_oracle(case.values[tid], case.request)
    ]
    assert judgement.first_in_range == (in_range[0] if in_range else None)

    # The result from the relied-on check and the last counted trial alone, without first_in_range.
    assert judgement.relied.problem == EXPECTED_PROBLEM[case.category]
    if case.category != "valid":
        expected = "not-counted"
    elif not case.counted:
        expected = "no-trial"
    else:
        last = max(case.counted, key=number_of)
        expected = "pass" if in_range_by_oracle(case.values[last], case.request) else "fail"
    assert judgement.result == expected

    assert judge(case.entries, case.frozen, case.request, ALLOWED_IDS) == judgement
