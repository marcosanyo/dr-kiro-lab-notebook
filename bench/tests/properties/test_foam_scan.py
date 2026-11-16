"""P15: terms planted in each kind of solver source are found in builder-level text and ignored in Dr. Kiro-
level text; an unreadable source file is an error (wind-tunnel Requirements 13.1, 13.2, 13.7)."""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bench.scan.scan import Scanner
from bench.scan.terms import EXTRACTORS, AppSources, ScanError
from labkit import examples

SYLLABLES = ["zor", "quin", "blat", "dle", "frob", "wob", "bet", "nic", "plax", "trov", "gub", "yeld"]
FILLER = ["the", "channel", "rises", "when", "value", "is", "held", "and", "then", "run", "faster", "at"]

# One template per kind of solver source: (extractor, file name, text with the planted term as {term}).
KINDS = {
    "keyword": ("openfoam-dict", "fvSolution", "settings\n{{\n    {term} 0.5;\n}}\n"),
    "patch": (
        "openfoam-dict",
        "boundary",
        "boundaryField\n{{\n    {term}\n    {{\n        type zeroGradient;\n    }}\n}}\n",
    ),
    "function-object": (
        "openfoam-dict",
        "controlDict",
        "functions\n{{\n    {term}\n    {{\n        type forceCoeffs;\n        log on;\n    }}\n}}\n",
    ),
    "script": (
        "shell-words",
        "Allrun",
        '#!/bin/sh\ncd "${{0%/*}}" || exit 1\n./{term}\nrunApplication {term}\n',
    ),
    "toml": ("toml-names", "setup.toml", "[{term}]\nvalue = 1\n"),
    "python": ("python-names", "make.py", "def {term}():\n    return 1\n"),
}

word = st.lists(st.sampled_from(SYLLABLES), min_size=2, max_size=3).map("".join)


@st.composite
def planted_term(draw: st.DrawFn) -> str:
    first, second = draw(st.lists(word, min_size=2, max_size=2, unique=True))
    shape = draw(st.integers(min_value=0, max_value=1))
    return [first, f"{first}_{second}"][shape]


def forms(term: str) -> st.SearchStrategy[str]:
    return st.sampled_from([term, term.upper(), term + "s", "my_" + term + "_amp", term.title()])


def extract(tmp_path: Path, kind: str, term: str) -> list[str]:
    extractor, file_name, template = KINDS[kind]
    path = tmp_path / file_name
    path.write_text(template.format(term=term), encoding="utf-8")
    return EXTRACTORS[extractor](path)


@settings(max_examples=examples(200), deadline=None)
@given(
    kind=st.sampled_from(sorted(KINDS)),
    term=planted_term(),
    data=st.data(),
    filler=st.lists(st.sampled_from(FILLER), max_size=8),
)
def test_planted_solver_terms_are_found(kind: str, term: str, data: st.DataObject, filler: list[str]) -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        extracted = extract(Path(folder), kind, term)
    assert term in extracted
    scanner = Scanner([AppSources(tuple(extracted), (), (), (), None)], [], local_paths=())
    form = data.draw(forms(term))
    at = data.draw(st.integers(min_value=0, max_value=len(filler)))
    text = " ".join(filler[:at] + [form] + filler[at:])
    assert "term" in [f.kind for f in scanner.scan_text(text, "builder", "x")], (kind, text, extracted)
    assert scanner.scan_text(text, "dr-kiro", "x") == []


@pytest.mark.parametrize("extractor", ["openfoam-dict", "shell-words", "toml-names", "python-names"])
@settings(max_examples=examples(100), deadline=None, suppress_health_check=[])
@given(garbage=st.sampled_from(["", "   \n", "\xff\xfe"]))
def test_unreadable_source_is_an_error(
    extractor: str, garbage: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    folder = tmp_path_factory.mktemp("bad")
    with pytest.raises(ScanError, match="missing"):
        EXTRACTORS[extractor](folder / "missing")
    bad = folder / "bad"
    if garbage == "\xff\xfe":
        bad.write_bytes(b"\xff\xfe\x00")
    else:
        bad.write_text(garbage, encoding="utf-8")
    with pytest.raises(ScanError, match="bad"):
        EXTRACTORS[extractor](bad)
