"""The wrapping adapter (design 3.3, Requirement 8).

The session config names the adapter as `build_from_spec.wrap:reader/<application>/<request-id>/<budget>`.
`bench.frontend.config` imports this module and calls the factory of that name with no arguments, or with the
variant setting when the config names one. The factory
builds the application's adapter, with the request's words as the goal and the reader budget, and passes every
trial through unchanged.
"""

import dataclasses
import importlib
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from bench.adapter import Declaration

from build_from_spec.apps import APPS, App, app_for, request_folder
from build_from_spec.request import parse_request

# The repository root. The reader runs in its own working folder, so the request folder is found from here.
ROOT = Path(__file__).resolve().parents[3]
PARTS = ("application", "request", "budget")


class WrapError(Exception):
    """A factory name that cannot build the reader's adapter. The message names what is wrong."""


class ReaderAdapter:
    def __init__(self, wrapped: Any, budget: int, words: str) -> None:
        self.wrapped = wrapped
        self._budget = budget
        self._words = words
        # The variants the wrapped adapter accepts, so the bench checks the setting as it does for any
        # application (lab-bench 23.3).
        variants = getattr(wrapped, "variants", None)
        if variants is not None:
            self.variants = variants
        # The optional methods exist on the instance only when the wrapped adapter has them (bench.adapter).
        for name in ("builder_versions", "check_inputs"):
            method = getattr(wrapped, name, None)
            if method is not None:
                setattr(self, name, method)

    def declaration(self) -> Declaration:
        return dataclasses.replace(self.wrapped.declaration(), budget=self._budget, goal=self._words)

    def run_trial(self, inputs, seed):
        return self.wrapped.run_trial(inputs, seed)


def _load_wrapped(spec: str, variant: str | None) -> Any:
    """Build the wrapped application's adapter from its `module:factory` (App.adapter), with the
    variant the run names (run.py `--variant`), if any. An unknown variant is a refusal (WrapError)."""
    module_name, attribute = spec.split(":")
    factory = getattr(importlib.import_module(module_name), attribute)
    if variant is None:
        return factory()
    try:
        return factory(variant=variant)
    except ValueError as error:
        raise WrapError(str(error)) from error


def build(name: str, apps: Mapping[str, App], root: Path, variant: str | None = None) -> ReaderAdapter:
    """Build the reader's adapter for one factory name, refusing and naming what is wrong (Req 8.5, 8.6).

    The request is read from the request folder of its application under `root` (apps.request_folder), so the
    rehearsal's request folder is read for the rehearsal application only."""
    parts = name.split("/")
    if parts[0] != "reader":
        raise WrapError(f"{name!r} is not a reader factory name; it starts with reader/")
    if len(parts) > 1 + len(PARTS):
        raise WrapError(f"{name!r} has more parts than reader/<application>/<request-id>/<budget>")
    fields = dict(zip(PARTS, parts[1:], strict=False))
    missing = [part for part in PARTS if not fields.get(part)]
    if missing:
        raise WrapError(
            f"{name!r} does not name the {', '.join(missing)}; "
            "the factory name is reader/<application>/<request-id>/<budget>"
        )
    app = app_for(fields["application"], apps)
    if fields["budget"] != str(app.budget):
        raise WrapError(
            f"{name!r}: budget {fields['budget']!r} is not the reader budget of {app.name}, "
            f"which is {app.budget}"
        )
    path = Path(root) / request_folder(app) / f"{fields['request']}.toml"
    if not path.is_file():
        raise WrapError(f"{name!r}: no request file {path}")
    request = parse_request(path, apps)
    if request.application != app.name:
        raise WrapError(f"{name!r}: request {request.id} is for {request.application}, not for {app.name}")
    return ReaderAdapter(_load_wrapped(app.adapter, variant), app.budget, request.words)


def __getattr__(name: str) -> Callable[[], ReaderAdapter]:
    """PEP 562: every name not starting with `__` is a factory name (design 3.3)."""
    if name.startswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    def factory(variant: str | None = None) -> ReaderAdapter:
        return build(name, APPS, ROOT, variant)

    return factory
