"""P18: derived terms planted in builder-level text are found in every token form, and ignored in Dr. Kiro-
level text; paths, file names and credentials are found at both levels; allow-list and stop-list words are
never found (Requirements 15.3-15.6, 16.7)."""

from hypothesis import given, settings
from hypothesis import strategies as st

from bench.scan.scan import Scanner
from bench.scan.terms import AppSources

SYLLABLES = ["zor", "quin", "blat", "dle", "frob", "wob", "bet", "nic", "plax", "trov", "gub", "yeld"]
FILLER = [
    "the",
    "channel",
    "rises",
    "when",
    "value",
    "is",
    "held",
    "and",
    "then",
    "run",
    "faster",
    "at",
    "0.5",
]

word = st.lists(st.sampled_from(SYLLABLES), min_size=2, max_size=3).map("".join)


@st.composite
def names_without_shared_words(draw: st.DrawFn) -> list[str]:
    """Three to six names. No word appears in two names, so one name can never match inside another."""
    count = draw(st.integers(min_value=3, max_value=6))
    words = draw(st.lists(word, min_size=2 * count, max_size=2 * count, unique=True))
    names = []
    for i in range(count):
        shape = draw(st.integers(min_value=0, max_value=2))
        first, second = words[2 * i], words[2 * i + 1]
        names.append([first, f"{first}_{second}", f"{first}_{draw(st.integers(1, 99)):02d}"][shape])
    return names


def forms(term: str) -> st.SearchStrategy[str]:
    parts = term.split("_")
    camel = parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    return st.sampled_from(
        [
            term,
            term.upper(),
            " ".join(parts),
            "-".join(parts),
            camel,
            term + "s",
            "my_" + term + "_amp",
            camel + "Amp",
            term.title(),
        ]
    )


@st.composite
def scenario(draw: st.DrawFn) -> tuple[Scanner, str, str, str, str]:
    names = draw(names_without_shared_words())
    planted, allowed, stopped = names[0], names[1], names[2]
    if "_" in stopped:
        stopped = stopped.split("_")[0]
        names[2] = stopped
    app = AppSources(
        names=tuple(names),
        file_names=(f"{names[0]}_model.xml",),
        solver_dirs=("casefolder",),
        allow=(allowed,),
        lab=None,
    )
    scanner = Scanner([app], [stopped])
    filler = draw(st.lists(st.sampled_from(FILLER), min_size=0, max_size=8))
    at = draw(st.integers(min_value=0, max_value=len(filler)))
    form = draw(forms(planted))
    text = " ".join(filler[:at] + [form] + filler[at:])
    harmless = " ".join(filler[:at] + [allowed, stopped] + filler[at:])
    return scanner, text, harmless, form, f"{names[0]}_model.xml"


@settings(max_examples=300, deadline=None)
@given(case=scenario())
def test_planted_terms(case: tuple[Scanner, str, str, str, str]) -> None:
    scanner, text, harmless, form, _ = case
    builder = scanner.scan_text(text, "builder", "x")
    assert [f.kind for f in builder] == ["term"], (text, builder)
    assert scanner.scan_text(text, "dr-kiro", "x") == []
    assert scanner.scan_text(harmless, "builder", "x") == []


LEAKS = st.sampled_from(
    [
        ("see ../model/{file}", {"path", "file name"}),
        ("open {file}", {"file name"}),
        ("from /projects/sandbox/x", {"path"}),
        ("casefolder/0/U", {"path"}),
        ("key AKIA" + "QWERTYUIOPASDFGH", {"credential"}),
        ("token: " + "x" * 24, {"credential"}),
    ]
)


@settings(max_examples=200, deadline=None)
@given(case=scenario(), leak=LEAKS, level=st.sampled_from(["builder", "dr-kiro"]))
def test_paths_file_names_and_credentials_at_both_levels(
    case: tuple[Scanner, str, str, str, str], leak: tuple[str, set[str]], level: str
) -> None:
    scanner, _, harmless, _, file_name = case
    template, kinds = leak
    text = harmless + " " + template.format(file=file_name)
    found = {f.kind for f in scanner.scan_text(text, level, "x")}
    assert kinds <= found
    if level == "dr-kiro":
        assert "term" not in found
