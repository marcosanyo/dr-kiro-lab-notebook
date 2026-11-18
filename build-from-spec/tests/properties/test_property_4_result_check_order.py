# Feature: build-from-spec, Property 4: Order of the result checks
"""For any run record and request: if H1 is missing, has no relied-on line, has a line of bad syntax,
names an id not in the allowed set, or was registered after the first experiment entry, the result is
`not-counted`, whatever the trials; otherwise, if the record has no counted trial, the result is `no-trial`.

**Validates: Requirements 10.3, 10.4, 15.2, 15.3**
"""

from hypothesis import given, settings

from build_from_spec.judge import judge
from support import ALLOWED_IDS, CATEGORIES, EXPECTED_PROBLEM, judge_cases


@settings(max_examples=100, deadline=None)
@given(judge_cases(CATEGORIES))
def test_result_checks_run_in_their_order(case):
    judgement = judge(case.entries, case.frozen, case.request, ALLOWED_IDS)
    assert judgement.relied.problem == EXPECTED_PROBLEM[case.category]
    if case.category != "valid":
        assert judgement.result == "not-counted"
    elif not case.counted:
        assert judgement.result == "no-trial"
    else:
        assert judgement.result in ("pass", "fail")
