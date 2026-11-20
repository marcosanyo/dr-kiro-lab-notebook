"""lab-bench Requirement 23 and design Part E: a named variant of the application."""

from dataclasses import replace

import pytest

from bench.core.outcome import Ran, Refused
from bench.core.session import Session, SessionError
from bench.record.store import Store
from labkit import Lab


class Variants:
    """The lab's fake application, with the variants an adapter may declare (Requirement 23.2)."""

    variants = ("x", "y")

    def __init__(self, inner: object) -> None:
        self.inner = inner

    def declaration(self):  # type: ignore[no-untyped-def]
        return self.inner.declaration()

    def run_trial(self, inputs, seed):  # type: ignore[no-untyped-def]
        return self.inner.run_trial(inputs, seed)


def refused(outcome: object, text: str) -> None:
    assert isinstance(outcome, Refused), outcome
    assert text in outcome.message.plain(), outcome.message.plain()


def start_entry(config) -> dict:  # type: ignore[no-untyped-def]
    store = Store.open(config.state_dir / config.session_id)
    try:
        return store.entries[0]["body"]
    finally:
        store.close()


def test_adapter_with_variants_refuses_a_missing_variant(lab: Lab) -> None:
    config = replace(lab.config, adapter=Variants(lab.config.adapter))
    refused(Session.start(config), "must be one of x, y")


def test_adapter_with_variants_refuses_an_unknown_variant(lab: Lab) -> None:
    config = replace(lab.config, adapter=Variants(lab.config.adapter), variant="z")
    refused(Session.start(config), "must be one of x, y")


def test_adapter_without_variants_refuses_a_variant(lab: Lab) -> None:
    refused(Session.start(replace(lab.config, variant="x")), "has no variants")


def test_known_variant_starts_and_is_recorded(lab: Lab) -> None:
    config = replace(lab.config, adapter=Variants(lab.config.adapter), variant="y")
    outcome = Session.start(config)
    assert isinstance(outcome, Ran), outcome
    outcome.result.close()
    assert start_entry(config)["variant"] == "y"


def test_no_variant_leaves_no_key_in_the_record(lab: Lab) -> None:
    outcome = Session.start(lab.config)
    assert isinstance(outcome, Ran), outcome
    outcome.result.close()
    assert "variant" not in start_entry(lab.config)


def test_reopening_checks_the_variant_against_the_record(lab: Lab) -> None:
    config = replace(lab.config, adapter=Variants(lab.config.adapter), variant="x")
    outcome = Session.start(config)
    assert isinstance(outcome, Ran), outcome
    outcome.result.close()
    Session.open(config).close()
    with pytest.raises(SessionError, match="variant"):
        Session.open(replace(config, variant="y"))
    with pytest.raises(SessionError, match="variant"):
        Session.open(replace(config, variant=None, adapter=lab.config.adapter))
