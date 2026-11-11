"""EARS shape check for hypothesis statements (Requirement 6.3, design 5.1).

The statement must be one sentence in one of five shapes, with the keywords in capitals. Only the shape is
checked, never the content.
"""

import re

_X = r"\S.*?"
SHAPES = {
    "ubiquitous": re.compile(rf"THE ({_X}) SHALL ({_X})\.", re.DOTALL),
    "event": re.compile(rf"WHEN ({_X}), THE ({_X}) SHALL ({_X})\.", re.DOTALL),
    "state": re.compile(rf"WHILE ({_X}), THE ({_X}) SHALL ({_X})\.", re.DOTALL),
    "unwanted": re.compile(rf"IF ({_X}), THEN THE ({_X}) SHALL ({_X})\.", re.DOTALL),
    "optional": re.compile(rf"WHERE ({_X}), THE ({_X}) SHALL ({_X})\.", re.DOTALL),
}
# A full stop followed by white space and more text ends a sentence. Decimal points (0.5) do not.
_SENTENCE_BREAK = re.compile(r"\.\s+\S")


def ears_shape(statement: str) -> str | None:
    """The name of the EARS shape the statement has, or None. White space runs count as one space."""
    text = " ".join(statement.split())
    if not text or _SENTENCE_BREAK.search(text):
        return None
    for name, pattern in SHAPES.items():
        if pattern.fullmatch(text):
            return name
    return None
