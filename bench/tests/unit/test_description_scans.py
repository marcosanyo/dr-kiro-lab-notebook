"""Task 26 (design A4): knob descriptions are scanned like all other bench text (Requirements 18.5, 18.7).

A description with a derived term stops `bench-mcp` at startup and stops sealing; the allow list is built from
names only; and the whole session of task 14 runs with a description on one knob of a copy of the declaration.
"""

import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest

from bench.adapter import Declaration, FunctionKnob, NumberKnob
from bench.core.outcome import BenchFailure
from bench.fake.adapter import FakeAdapter
from bench.frontend.server import BenchServer, StartupError
from bench.scan.terms import allow_list
from labkit import Lab

_spec = importlib.util.spec_from_file_location(
    "full_session_task14", Path(__file__).with_name("test_full_session.py")
)
assert _spec is not None and _spec.loader is not None
_full = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_full)
run_full_session = _full.test_full_session

PLAIN = "Larger values push harder; the effect is the same at every sample."
DERIVED = "This one is tied to the zorblat."


class DescribedAdapter(FakeAdapter):
    """The fake application with a description on its number knob."""

    def __init__(self, description: str, budget: int = 12) -> None:
        super().__init__(budget)
        decl = self._declaration
        self._declaration = replace(
            decl,
            knobs=tuple(
                replace(k, description=description) if isinstance(k, NumberKnob) else k for k in decl.knobs
            ),
        )


def described(lab: Lab, description: str) -> Lab:
    lab.config = replace(lab.config, adapter=DescribedAdapter(description))
    return lab


def test_description_with_derived_term_stops_the_server_at_startup(lab: Lab) -> None:
    session = described(lab, DERIVED).start()
    with pytest.raises(StartupError, match="blind scan.*zorblat"):
        BenchServer(session)


def test_description_without_derived_term_starts_the_server(lab: Lab) -> None:
    server = BenchServer(described(lab, PLAIN).start())
    assert PLAIN in server.session.declaration.knobs[1].description


def test_session_with_derived_term_in_description_cannot_be_sealed(lab: Lab) -> None:
    session = described(lab, DERIVED).start()
    failure = session.stop("builder stops the session")
    assert isinstance(failure, BenchFailure), failure
    assert session.sealed_path is None or not session.sealed_path.exists()


def test_allow_list_holds_names_and_no_description_words() -> None:
    plain = FakeAdapter().declaration()
    with_text = DescribedAdapter(PLAIN).declaration()
    assert allow_list(with_text) == allow_list(plain)
    allowed = set(allow_list(with_text))
    assert allowed >= {"drive", "gain", "distance", "turn", "trace", "lost"}
    assert not {w.strip(".;,").lower() for w in PLAIN.split()} & allowed


def test_full_session_with_a_description(lab: Lab) -> None:
    run_full_session(described(lab, PLAIN))
    (sealed,) = (lab.root / "sessions" / "fake").iterdir()
    assert PLAIN in "".join(p.read_text() for p in sealed.glob("*.jsonl"))


def test_declaration_types_are_unchanged() -> None:
    decl: Declaration = DescribedAdapter(PLAIN).declaration()
    assert isinstance(decl.knobs[0], FunctionKnob) and decl.knobs[0].description == ""
