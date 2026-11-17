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

# Shared labels (Requirements 4.5, 12.7, 8.2).
WRITTEN_BY_DRKIRO = "written by Dr. Kiro"
CHOSEN_BY_A_PERSON = "chosen by a person"
LEGEND_LINK = "ink legend: who wrote each text"
LIST_SEPARATOR = ", "

# Labels below a status stamp (Requirements 8.2, 10.7).
CHECKED = "checked by the bench"
NOT_CHECKED = "not checked by the bench"

# The discovered spec table section of the session page (Requirements 8, 10.1).
TABLE_HEADING = "Discovered spec"
COLUMN_ID = "id"
COLUMN_RULE = "rule"
COLUMN_SCOPE = "scope"
COLUMN_EXPERIMENTS = "experiments"
COLUMN_PREDICTIONS = "predictions"
COLUMN_STATUS = "status"
COLUMN_REPLACED_BY = "replaced by"
REPLACED_BY = "replaced by "
REPLACES = "replaces "

# Why a `rejected` row has no "replaced by" tab (Requirement 8.4, design N12).
REPLACED_NAMES_NO_ROW = "This cell names no row of this table."
REPLACED_NAMES_MANY_ROWS = "This cell names more than one row of this table."
REPLACED_NAMES_ITSELF = "This cell names this row itself."

# A table the bench's table reader does not accept (Requirement 10.14).
UNREADABLE = "the bench's table reader did not accept this table"
UNREADABLE_MESSAGE = "The reader's message: "
UNREADABLE_NO_SECTION = "The snapshot's design file has no discovered spec section to show."

# An ended session without an end snapshot (Requirement 10.9).
NO_TABLE = "no table"
NO_TABLE_NOTE = (
    "The record holds no discovered spec table: "
    "the session ended without a snapshot taken at an accepted end."
)
MISSED_LIST = "Every prediction of this session that missed:"

# The margin of the table page (Requirements 10.1, 10.2).
MISS_POINTER = "A prediction that missed: "
MISS_NONE = "No missed prediction was chosen for this note. The reason given: "
REGISTERED_RANGE = " registered range "
MEASURED = ", measured "
PINNED_CONTRAST = "contrast"
PINNED_BEST = "best result"
PINNED_NONE = "none. The reason given: "

# Moving pictures (Requirements 7.6, 7.8; design 10). The buttons are shown by the page script; without it the
# whole sheet is shown.
PHOTO_ALT = "the trial's picture sheet, every cell in reading order"
PHOTO_TRIAL = "trial "
PHOTO_PLAY = "play"
PHOTO_PAUSE = "pause"
PHOTO_STEP = "step one cell"
PHOTO_SHEET = "whole sheet"

# Overhead track of a trial (Requirements 10.10, 13.7; design N21).
TRACK_CAPTION = "recorded track seen from above, equal scale on both axes; the circle marks the start"
TRACK_NOT_MEASURED = "No track is drawn: the recorded series is not measured. "
# The cover's short caption; the cover explains the drawing in full inside its details (Requirement 13.6).
TRACK_CAPTION_COVER = "track from above"

# The cover, `index.html` (Requirement 13). The commentary visible before any detail is opened is at most 60
# words (13.6), so the visible strings are short and the explanations sit inside `<details>`.
SITE_TITLE = "Dr. Kiro's Lab Notebook"
TAGLINE = "The experiment gets the final edit."
COVER_RANGE = " range "
COVER_MEASURED = " measured "
COVER_MISS_NONE = "This session has no missed prediction."
COVER_NO_ROW = "No row cites it."
COVER_DETAILS = "details"
COVER_ABOUT = (
    "Dr. Kiro registered this prediction, with its range, before the trial ran. "
    "The bench ran the trial, recorded the measured value and recorded the outcome."
)
COVER_HYPOTHESIS = "hypothesis "
COVER_CONDITIONS = "conditions: "
COVER_CLASS = "condition class, classified at registration: "
COVER_FULL_VALUE = "measured value as recorded: "
COVER_ROWS = (
    "The rows of the discovered spec table that cite this prediction, each with the row that replaces it "
    "when it is rejected. The status words are checked by the bench."
)
COVER_OUTCOME_LINK = "this prediction's outcome in its experiment entry"
COVER_TABLE_LINK = "the session's discovered spec table"
COVER_CARDS = "One trial of each lab, chosen by a person. Each card opens the list of that lab's sessions."
