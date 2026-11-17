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

# The opened row: the evidence a row cites (Requirements 8.5-8.8). No status word is written here except in
# the fixed explanation of the bench's check (8.6, 15.2).
EVIDENCE_SUMMARY = "open the evidence this row cites: "
EVIDENCE_EXPERIMENTS = "Cited experiments:"
EVIDENCE_EXPERIMENTS_NONE = "The row cites no experiment."
EVIDENCE_NO_EXPERIMENT = " (no experiment of the record at this point has this id)"
EVIDENCE_PREDICTIONS = "Cited predictions, each with its registered range and what was measured:"
EVIDENCE_PREDICTIONS_NONE = "The row cites no prediction."
EVIDENCE_NO_PREDICTION = " (no prediction registered in the record at this point has this id)"
EVIDENCE_OF_HYPOTHESIS = " of hypothesis "
EVIDENCE_PREDICTED = "; "
EVIDENCE_OBSERVED = "What the bench checks for this status word: "
EVIDENCE_UNTRIED = (
    "Cited hits under conditions no earlier trial covered, with their condition class from registration:"
)
EVIDENCE_UNTRIED_NONE = "No cited hit has the condition class new-combination or outside."
EVIDENCE_CLASS = ", condition class "

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
# After the measurement's name, which stands in its own element (visual steering, sticky note).
MEASURED_NAME_END = ": "
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
# The cover's one-word caption; the cover explains the drawing in full inside its details (Requirement 13.6).
TRACK_CAPTION_COVER = "track"

# The cover, `index.html` (Requirement 13). The commentary visible before any detail is opened is at most 60
# words (13.6), so the visible strings are short and the explanations sit inside `<details>`. To keep the
# stamp labels of the cited rows (8.2) within the limit, the cover's photos show the trial id without the word
# "trial" and the track has a one-word caption (user, checkpoint 11).
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

# The lab pages, `<app>.html` (Requirement 14). Every record shows the same fields (14.1, 14.2).
LAB_TITLE = "Sessions of a lab"
LAB_HEADING = "Every session of the lab "
LAB_INTRO = "Ended and stopped sessions are listed together, in order of their session ids."
BACK_TO_COVER = "back to the cover"
FIELD_SESSION = "session"
FIELD_END = "how the record was sealed"
FIELD_REASON = "the bench's reason"
FIELD_BUDGET = "budget used"
BUDGET_OF = " of "
FIELD_TRIALS = "trials"
FIELD_EXPERIMENTS = "experiments"
FIELD_HITS = "hits"
FIELD_MISSES = "misses"
FIELD_NEVER_RUN = "hypotheses registered and never run"
NEVER_RUN_NONE = "none"
FIELD_TABLE = "discovered spec table"
TABLE_CHECKED_ROWS = "checked by the bench, rows: "
TABLE_NOT_CHECKED_ROWS = "not checked by the bench, rows: "
TABLE_NO_SNAPSHOT = "the record has no snapshot"
FIELD_STOPPED_AT = "action at which the session stopped"
STOPPED_AT_NONE = "the record has no failure entry"
# The one fixed commentary of every stopped session, shown beside the bench's recorded reason (14.3).
STOPPED_NOTE = (
    "The bench stopped this session before Dr. Kiro ended it. "
    "The record is shown as it was sealed, with the bench's reason as written."
)

# The ink legend, `legend.html` (Requirements 4.5, 15.2). Status words are named here in commentary ink.
LEGEND_TITLE = "Ink legend"
LEGEND_INTRO = (
    "Every text in this notebook is shown in the ink of its author. "
    "Each ink has its own typeface, so the inks can be told apart without colour."
)
LEGEND_INKS = "The three inks"
INK_DRKIRO_NAME = "Dr. Kiro's ink"
INK_DRKIRO_ABOUT = (
    "Text whose recorded author is Dr. Kiro, shown exactly as written. "
    "Serif type, dark blue; a block of it has a rule on its left side and the label written by Dr. Kiro."
)
INK_PENCIL_NAME = "Pencil"
INK_PENCIL_ABOUT = (
    "Text the bench recorded, and numbers the notebook computes from it: measurements, outcomes, "
    "condition classes, reasons and counts. Monospace type, dark grey."
)
INK_COMMENTARY_NAME = "Commentary ink"
INK_COMMENTARY_ABOUT = (
    "The notebook's own text, written by the builder of the lab: headings, labels and explanations. "
    "Sans-serif type, dark brown."
)
MISS_RED_NAME = "Miss red"
MISS_RED_ABOUT = (
    "Used only for a prediction that missed and its measured value, always together with the word miss."
)
LEGEND_STATUS = "Status words"
# The four words as the bench accepts them (`bench.specfiles.discovered.STATUSES`); the legend checks this.
STATUS_VALIDATED_WORD = "validated"
STATUS_PARTLY_WORD = "partly"
STATUS_OBSERVED_WORD = "observed"
STATUS_REJECTED_WORD = "rejected"
LEGEND_STATUS_INTRO = (
    "Dr. Kiro gives each row of its discovered spec table one status word. The bench checks the word "
    "against the record when the session ends. In a table, the word is shown as a stamp, with a label that "
    "says whether the bench checked it."
)
STATUS_VALIDATED = (
    "every cited prediction was a hit, and at least one hit was a new combination or outside the tried range."
)
STATUS_PARTLY = "the row cites at least one hit and at least one miss."
STATUS_OBSERVED = "seen in experiments; no cited prediction missed; Dr. Kiro does not claim validated"
STATUS_REJECTED = (
    "the row cites at least one miss and names the row that replaces it. "
    "It is struck through and stays in its place in the table."
)

# The session page, `<app>-<session>.html` (Requirement 10).
SESSION_TITLE = "A session"
SESSION_HEADING = "Session "
SESSION_OF_LAB = " of the lab "
BACK_TO_LAB = "back to the lab's sessions"

# The page of a session whose record has no snapshot (Requirements 14.2, 14.6, 16.9): only what the record
# holds, and the sentence in place of the replay.
NO_SNAPSHOT_HEADING = "What the record holds"
REPLAY_HEADING = "Replay"
NO_REPLAY = "the record has no snapshot to replay"

# The highlight (Requirements 10.3, 10.4, 12.7).
HIGHLIGHT_HEADING = "Highlight"
HIGHLIGHT_CONTRAST = "A contrast: two trials side by side"
HIGHLIGHT_BEST = "The best result"
HIGHLIGHT_NONE = "none. The reason given: "

# Measured values of a trial (Requirements 5.3, 5.4). Lists round to 4 significant digits; the opened trial
# shows every recorded value in full.
VALUES_ROUNDED = "Measured, rounded to 4 significant digits:"
VALUE_SEPARATOR = ": "
SERIES_OF = "a series of "
SERIES_SAMPLES = " recorded samples, listed in full when the trial is opened"
NOT_MEASURED_REASON = ", the bench's reason: "
VALUES_FULL = "every recorded value in full"
PARAMS_FULL = "Parameter values as recorded:"
MEASURED_FULL = "Measured values as recorded:"

# The progress (Requirement 10.5).
PROGRESS_HEADING = "Progress"
PROGRESS_BUDGET = "Budget used: "
PROGRESS_PHASES = "Experiments by phase:"
PROGRESS_OUTCOMES = "Prediction outcomes, one for each registered prediction:"

# Dr. Kiro's plan (Requirement 10.6, design N18).
PLAN_HEADING = "Dr. Kiro's plan"
PLAN_NOTE = "The plan file of the session's last snapshot, as written."
PLAN_REQUIREMENTS = "Dr. Kiro's requirements file of the same snapshot, as written"

# The experiment entries (Requirements 10.8, 11, 15.1, 15.3).
ENTRIES_HEADING = "Experiments"
ENTRIES_NONE = "The record holds no experiment."
ENTRY_PHASE = " phase "
ENTRY_MODE = ", mode "
ENTRY_HYPOTHESIS = "Hypothesis "
ENTRY_FROZEN = ", the part frozen at registration:"
ENTRY_PREDICTIONS = "Predictions registered with it:"
PREDICTION_RANGE = " registered range "
PREDICTION_WHEN = " when "
PREDICTION_CLASS = "; condition class, classified at registration: "
PREDICTION_LABEL = "; Dr. Kiro's label: "
PREDICTION_STATE = "; outcome: "
ENTRY_FILE = "The experiment file "
ENTRY_FILE_END = ", as run:"
ENTRY_PARAMS = "Parameter names declared: "
ENTRY_SWEEP = "; swept: "
ENTRY_TRIALS = "Trials"
TRIAL_SEED = ", seed "
TRIAL_PARAMS = "Parameter values: "
ENTRY_OUTCOMES = "Prediction outcomes"
OUTCOMES_NONE = "No prediction outcome is recorded for this experiment."
OUTCOME_TRIAL = " in trial "
OUTCOME_MEASURED = ", measured "
OUTCOME_NOT_MEASURED = ", not measured: "
OUTCOME_IS = ", outcome "
VERDICT_ON = "verdict on "
VERDICT_COLON = ": "
VERDICT_NONE = "No verdict is recorded for this experiment."
FLAG_NOTE = (
    "Bench note: the bench flagged this verdict against the recorded outcomes of its predictions. Counts: "
)
FLAG_COUNT = " "

# Hypotheses that no experiment names (Requirement 11.3).
NEVER_RUN_HEADING = "Hypotheses registered and never run"
NEVER_RUN_NONE_SESSION = "Every registered hypothesis has an experiment."

# Refusals (Requirements 10.13, 18.4).
REFUSALS_HEADING = "Refusals"
REFUSALS_INTRO = (
    "Each action the bench refused, with its message as recorded. A refused action runs nothing and "
    "uses no budget."
)
REFUSALS_NONE = "The bench refused no action in this session."
REFUSAL_ACTION = "Refused action: "
REFUSAL_GIVEN = "; given "
REFUSAL_MESSAGE = "The bench's message: "

# The banner of a build from labelled test fixtures (design N19). The command line never shows it.
FIXTURE_BANNER = (
    "test fixture: this page is built from labelled fixture records, and nothing on it is a result."
)
