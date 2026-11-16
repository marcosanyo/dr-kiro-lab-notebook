"""P30: a file name is found in full; its stem is found unless the stem is one character or is on the stop
list; a name without a dot is a full name and is always found; at both levels (Requirement 20)."""

import string

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.scan.scan import Scanner
from bench.scan.terms import AppSources
from labkit import examples

SYLLABLES = ["zor", "quin", "blat", "dle", "frob", "wob", "bet", "nic", "plax", "trov", "gub", "yeld"]
EXTENSIONS = ["in", "py", "dat", "json"]
FILLER = ["the", "channel", "rises", "when", "value", "is", "held", "and", "then", "faster", "at", "0.5"]

stem = st.lists(st.sampled_from(SYLLABLES), min_size=1, max_size=3).map("".join)


def cased(word: str, flips: list[bool]) -> str:
    return "".join(
        c.upper() if flip else c for c, flip in zip(word, flips + [False] * len(word), strict=False)
    )


@st.composite
def case(draw: st.DrawFn) -> dict:
    long_stems = draw(st.lists(stem, min_size=2, max_size=5, unique=True))
    listed = [s for s in long_stems if draw(st.booleans())]
    short = draw(st.lists(st.sampled_from(string.ascii_letters), min_size=1, max_size=3, unique_by=str.lower))
    dotless = draw(
        st.lists(stem, min_size=1, max_size=2, unique=True).filter(lambda d: not set(d) & set(long_stems))
    )
    ext = st.sampled_from(EXTENSIONS)
    dotted = [f"{s}.{draw(ext)}" for s in long_stems + short]
    return {
        "long": long_stems,
        "listed": listed,
        "short": short,
        "dotless": dotless,
        "dotted": dotted,
        "files": dotted + dotless,
        "flips": draw(st.lists(st.booleans(), min_size=3, max_size=3)),
        "filler": " ".join(draw(st.lists(st.sampled_from(FILLER), min_size=2, max_size=5))),
    }


def hits(scanner: Scanner, text: str, level: str) -> list[str]:
    return sorted(f.match.lower() for f in scanner.scan_text(text, level, "x") if f.kind == "file name")


# Feature: lab-bench, Property 30: file-name stems skip one character and the stop list; full names match
# Validates: Requirements 20.1-20.4
@settings(max_examples=examples(200), deadline=None)
@given(c=case(), level=st.sampled_from(["builder", "dr-kiro"]))
def test_stems_and_stop_list(c: dict, level: str) -> None:
    sources = AppSources((), tuple(c["files"]), (), (), None)
    scanner = Scanner([sources], c["listed"], local_paths=[])
    filler = c["filler"]
    for word in c["short"]:  # a one-character stem is not a file name
        assert hits(scanner, f"{filler} {word} {filler}", level) == []
    for word in c["listed"]:  # a stop-listed stem is not a file name, in any case
        assert hits(scanner, f"{filler} {cased(word, c['flips'])} {filler}", level) == []
    for word in c["long"]:
        if word not in c["listed"]:  # an unlisted stem is still a file name
            assert hits(scanner, f"{filler} {cased(word, c['flips'])} {filler}", level) == [word]
    for name in c["dotted"]:  # a full name is always a file name
        found = hits(scanner, f"{filler} {name} {filler}", level)
        base = name.split(".", 1)[0]
        stem_found = base in c["long"] and base not in c["listed"]
        assert found == sorted(n.lower() for n in ([name, base] if stem_found else [name]))
    for name in c["dotless"]:  # no dot: the stem is the full name, so it is found, listed or not
        assert hits(scanner, f"{filler} {name} {filler}", level) == [name]
