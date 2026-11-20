"""lab-bench Requirement 23 through the reader: the run's variant reaches the wrapped body
(body-lab Requirement 7)."""

import pytest

from build_from_spec import wrap
from build_from_spec.apps import APPS
from build_from_spec.wrap import ReaderAdapter, WrapError, build

FACTORY = "reader/body-lab/stop-ahead/12"


def test_variant_is_passed_to_the_wrapped_body() -> None:
    adapter = build(FACTORY, APPS, wrap.ROOT, variant="b")
    assert isinstance(adapter, ReaderAdapter)
    assert adapter.variants == ("a", "b")
    assert adapter.wrapped.body is not None


def test_no_variant_gives_the_declaration_and_no_body() -> None:
    adapter = build(FACTORY, APPS, wrap.ROOT)
    assert adapter.wrapped.body is None
    assert adapter.declaration().budget == 12


def test_unknown_variant_is_a_wrap_refusal() -> None:
    with pytest.raises(WrapError, match="one of a, b"):
        build(FACTORY, APPS, wrap.ROOT, variant="c")


def test_factory_takes_the_variant_as_a_keyword() -> None:
    factory = getattr(wrap, FACTORY)
    assert factory(variant="a").variants == ("a", "b")
