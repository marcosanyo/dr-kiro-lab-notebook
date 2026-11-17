# Feature: build-from-spec, Property 2: Malformed requests are refused by name
"""For any valid request and any one mutation of Requirement 2.2, the parser refuses the file,
and the refusal names the file and the field or line of that mutation.

**Validates: Requirements 2.2**
"""

import copy
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from build_from_spec.apps import APPS
from build_from_spec.request import Request, RequestError, parse_request
from support import base_spec, literal, render, requests

# Each mutation takes the valid spec (see support.base_spec) and the request. It returns the file text
# and the text its refusal must contain.
Mutation = Callable[[dict, Request], tuple[str, str]]


def _missing(key: str) -> Mutation:
    def mutate(spec, request):
        del spec[key]
        return render(spec), f"{key}: missing field"

    return mutate


def _extra_top_level(spec, request):
    spec["unit"] = literal("m")
    return render(spec), "unit: extra field at the top level"


def _extra_in_pass(spec, request):
    spec["pass"][0]["unit"] = literal("m")
    return render(spec), "pass[1].unit: extra field in a [[pass]] table"


def _missing_in_pass(key: str) -> Mutation:
    def mutate(spec, request):
        del spec["pass"][0][key]
        return render(spec), f"pass[1].{key}: missing field"

    return mutate


def _id_differs(spec, request):
    spec["id"] = literal(request.id + "-x")
    return render(spec), "id: "


def _id_bad_pattern(spec, request):
    spec["id"] = literal("Bad_" + request.id)
    return render(spec), "id: "


def _unknown_application(spec, request):
    spec["application"] = literal("wind-tunnel")
    return render(spec), "application: no adapter is known"


def _blank_words(spec, request):
    spec["words"] = literal(" \t ")
    return render(spec), "words: is empty"


def _no_pass_table(spec, request):
    del spec["pass"]
    return render(spec) + "pass = []\n", "pass: needs one or more [[pass]] tables"


def _bound(text: str) -> Mutation:
    def mutate(spec, request):
        spec["pass"][0]["range"] = text
        return render(spec), "pass[1].range: "

    return mutate


def _equal_bounds(spec, request):
    low = request.passes[0].low
    spec["pass"][0]["range"] = f"[{low!r}, {low!r}]"
    return render(spec), "pass[1].range: low"


def _named_twice(spec, request):
    spec["pass"].append(dict(spec["pass"][0]))
    return render(spec), f"pass[{len(spec['pass'])}].measurement: "


def _measurement(name: str) -> Mutation:
    def mutate(spec, request):
        spec["pass"][0]["measurement"] = literal(name)
        return render(spec), "pass[1].measurement: "

    return mutate


def _broken_toml(spec, request):
    return render(spec) + "[[\n", "not valid TOML"


MUTATIONS: list[Mutation] = [
    _missing("id"),
    _missing("application"),
    _missing("words"),
    _missing("pass"),
    _extra_top_level,
    _extra_in_pass,
    _missing_in_pass("measurement"),
    _missing_in_pass("range"),
    _id_differs,
    _id_bad_pattern,
    _unknown_application,
    _blank_words,
    _no_pass_table,
    _bound('["a", 1.0]'),
    _bound("[true, 1.0]"),
    _bound("[-inf, 1.0]"),
    _bound("[nan, 1.0]"),
    _equal_bounds,
    _named_twice,
    _measurement("track_x"),
    _measurement("nosuch"),
    _broken_toml,
]


@settings(max_examples=100, deadline=None)
@given(request=requests(), index=st.integers(min_value=0, max_value=len(MUTATIONS) - 1))
def test_malformed_requests_are_refused_by_name(request, index):
    text, expected = MUTATIONS[index](copy.deepcopy(base_spec(request)), request)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"{request.id}.toml"
        path.write_text(text, encoding="utf-8")
        with pytest.raises(RequestError) as refused:
            parse_request(path, APPS)
    message = str(refused.value)
    assert message.startswith(f"{path}: ")
    assert expected in message
