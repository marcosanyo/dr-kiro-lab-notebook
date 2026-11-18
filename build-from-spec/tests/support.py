"""Generators and writers shared by the property tests (tests/properties/)."""

import json

from hypothesis import strategies as st

from build_from_spec.request import PassRange, Request

SCALARS = ("x", "y", "heading")  # the scalar measurements of body-lab (its declaration)

request_ids = st.from_regex(r"\A[a-z0-9-]{1,40}\Z", fullmatch=True)
request_words = st.text(min_size=1, max_size=200).filter(lambda text: text.strip() != "")


@st.composite
def requests(draw) -> Request:
    """A valid request for body-lab: distinct scalar measurements, finite bounds with low < high."""
    names = draw(st.lists(st.sampled_from(SCALARS), min_size=1, max_size=3, unique=True))
    passes = []
    for name in names:
        # high is drawn above low, so no draw is thrown away (a filter here made hypothesis give up).
        low = draw(st.floats(min_value=-1e6, max_value=1e6, exclude_max=True, allow_nan=False))
        high = draw(st.floats(min_value=low, max_value=1e6, exclude_min=True, allow_nan=False))
        passes.append(PassRange(name, low, high))
    return Request(draw(request_ids), "body-lab", draw(request_words), tuple(passes))


def literal(text: str) -> str:
    """A TOML basic string for text: JSON escapes are TOML escapes, and DEL is written as an escape."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def base_spec(request: Request) -> dict:
    """The request as TOML literals, in the fields and order of a request file. Mutations edit this dict."""
    return {
        "id": literal(request.id),
        "application": literal(request.application),
        "words": literal(request.words),
        "pass": [
            {"measurement": literal(p.measurement), "range": f"[{p.low!r}, {p.high!r}]"}
            for p in request.passes
        ],
    }


def render(spec: dict) -> str:
    """Write a spec dict as request-file text. Keys missing from the dict are missing from the file."""
    lines = [f"{key} = {value}" for key, value in spec.items() if key != "pass"]
    for table in spec.get("pass", []):
        lines += ["", "[[pass]]"] + [f"{key} = {value}" for key, value in table.items()]
    return "\n".join(lines) + "\n"


# A relied-on id: any run of characters other than a comma or whitespace, and not `none` (which stands alone).
relied_ids = st.from_regex(r"\A[^,\s]{1,12}\Z", fullmatch=True).filter(
    lambda identifier: identifier != "none"
)


@st.composite
def relied_id_tuples(draw) -> tuple[str, ...]:
    """Either `("none",)` or distinct ids that do not include `none`."""
    if draw(st.booleans()):
        return ("none",)
    return tuple(draw(st.lists(relied_ids, min_size=1, max_size=6, unique=True)))
