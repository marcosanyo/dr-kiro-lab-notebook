# Feature: build-from-spec, Property 1: Request round trip
"""For any valid request, parsing the printed text gives the same request, and printing it again
gives the same text.

**Validates: Requirements 2.1, 2.4**
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings

from build_from_spec.apps import APPS
from build_from_spec.request import parse_request, print_request
from support import requests


@settings(max_examples=100, deadline=None)
@given(request=requests())
def test_request_round_trip(request):
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / f"{request.id}.toml"
        path.write_text(print_request(request), encoding="utf-8")
        parsed = parse_request(path, APPS)
        assert parsed == request
        path.write_text(print_request(parsed), encoding="utf-8")
        assert parse_request(path, APPS) == parsed
