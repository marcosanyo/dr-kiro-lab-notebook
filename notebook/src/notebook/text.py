"""Every commentary string of the site: the one place the builder's words live (design "Package layout").

Each string here is builder-level text: it passes the commentary word check (Requirement 5.5) and the blind
scan at the builder level (Requirement 20.1). No part, joint, actuator or solver name is written here, and no
file or folder outside a lab is named. Pages add their strings to this module; no other module holds
commentary.

`source(name)` is the place a string comes from, used as the `source` of its segment so a scan finding names
it (Requirement 20.2).
"""

SOURCE_FILE = "notebook/src/notebook/text.py"


def source(name: str) -> str:
    """The source of the commentary string `name` of this module, for its segment."""
    if not isinstance(globals().get(name), str):
        raise KeyError(f"text.py has no commentary string {name!r}")
    return f"{SOURCE_FILE}: {name}"


# Refusal messages (Requirements 10.11, 10.13; design 5, N13).

# Shown with every refusal message that holds a quote part; it covers every quote part of that message.
REFUSAL_QUOTE_NOTE = (
    "Quotes in a refusal message are recorded with Dr. Kiro as their author. "
    "Some of them, such as a summary of cited outcomes, are composed by the bench from Dr. Kiro's ids."
)

# The refused-end note, attached to a row whose id a quote of an `end` refusal names exactly. The count N
# sits between the two halves of the heading, in pencil.
REFUSED_END_BEFORE_COUNT = "the bench refused to end this session "
REFUSED_END_AFTER_COUNT = " times"
REFUSED_END_SEALED = "The sealed row's status is the one shown in the table."
REFUSED_END_NO_COPY = "the record holds no copy of the table that was refused"
