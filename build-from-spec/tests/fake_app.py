"""The fake application for the run tests: the bench's fake adapter at budget 12 (test table `TEST_APPS`)."""

from bench.fake.adapter import FakeAdapter


def fake_adapter() -> FakeAdapter:
    return FakeAdapter(budget=12)
