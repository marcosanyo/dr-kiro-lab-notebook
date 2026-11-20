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
REFUSED_END_SHOW = "what the bench said"

# Shared labels (Requirements 4.5, 12.7, 8.2).
WRITTEN_BY_DRKIRO = "written by Dr. Kiro"
CHOSEN_BY_A_PERSON = "chosen by a person"
LEGEND_LINK = "ink legend"
HOW_LINK = "how the lab works"
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
PHOTO_SHEET = "whole picture"
PHOTO_BACK = "magnified picture"
# The magnified picture beside a moving picture (Requirement 7.9, design N32). The alt text is the sentence
# the requirement gives; the picture has no visible caption, because the cover's visible commentary is limited
# to 60 words (Requirement 13.6).
PHOTO_MAGNIFIED_ALT = "Magnified view of the picture beside it"

# Overhead track of a trial (Requirements 10.10, 13.7; design N21).
TRACK_CAPTION = "recorded track seen from above, equal scale on both axes; the circle marks the start"
TRACK_NOT_MEASURED = "No track is drawn: the recorded series is not measured. "
# The cover's one-word caption; the cover explains the drawing in full inside its details (Requirement 13.6).
TRACK_CAPTION_COVER = " track seen from above"

# Run bands beside a row's scope (Requirement 9; design 4). Shown inside the scope cell, after Dr. Kiro's
# scope text, which is never read.
BANDS_INTRO_SUMMARY = "How to read the bands"
BANDS_INTRO = (
    "What the record says was run, per parameter group of this row's cited trials: one tick per value a "
    "trial of the session ran in that group; taller ticks are this row's cited trials, the tallest its "
    "prediction trials; the shaded span runs from the lowest to the highest cited value; hatched parts had "
    "no trial. Untried combinations show only in each cited prediction's condition class."
)
BANDS_NONE = "No trial is cited by this row, so there is no run band."
BANDS_GROUP = "parameter group: "
BANDS_TRIED = " tried "
BANDS_DECLARED = ", declared range "
BANDS_CITED = ", cited "
BANDS_NO_TRIAL = ", no trial "
BANDS_RANGE_OPEN = "["
BANDS_RANGE_CLOSE = "]"
BANDS_OPEN_LOW = "("
BANDS_OPEN_HIGH = ")"

# The cover, `index.html` (Requirement 13). The commentary visible before any detail is opened is at most 60
# words (13.6), so the visible strings are short and the explanations sit inside `<details>`. To keep the
# stamp labels of the cited rows (8.2) within the limit, the cover's photos show the trial id without the word
# "trial" and the track has a one-word caption (user, checkpoint 11).
SITE_TITLE = "Dr. Kiro's Lab Notebook"
TAGLINE = "The experiment gets the final edit."
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
COVER_CARDS = (
    "Each tab shows one trial of the lab, chosen by a person, beside the ended sessions of that lab."
)
# The cover after the polish pass (user, 2026-11-19). Headings are written in lower case and shown as small
# capitals by the stylesheet.
COVER_KICKER = "laboratory notebook · one skeleton, two labs"
COVER_INK_BLUE = "blue pen: Dr. Kiro's words"
COVER_INK_RED = "red: a rewritten rule, a missed prediction"
COVER_INK_PENCIL = "pencil: measured values"
COVER_MISS_HEADING = "a prediction that missed"
COVER_PREDICTED = "predicted"
COVER_MEASURED_HEAD = "measured"
COVER_MISSED_STAMP = "missed"
COVER_STICKY_WHEN = "when "
COVER_STICKY_EXPECTED = "expected "
COVER_STICKY_BETWEEN = " between "
COVER_STICKY_AND = " and "
COVER_STICKY_MEASURED = ", measured "
COVER_STICKY_BELOW = ": below the range"
COVER_STICKY_ABOVE = ": above the range"
COVER_STICKY_OPPOSITE = ", on the other side of zero"
COVER_STICKY_TO_GO = "to go "
COVER_STICKY_FORWARD = "forward "
COVER_STICKY_BACK = "back "
COVER_STICKY_TO = " to "
COVER_STICKY_WENT = ", went "
COVER_RULES_HEAD = "rules that cite it"
COVER_CAPTION_MOVING = " the whole picture, moving, one cell at a time"
COVER_CAPTION_MAGNIFIED = " magnified around the body, one recorded frame at a time"
COVER_CAPTION_WHOLE = " the whole picture, one recorded frame at a time"
COVER_READER_HEADING = "the reader"
COVER_READER_ABOUT = (
    "Another Kiro, which never saw the experiments, was given only the spec, only the raw record, "
    "or nothing, and was asked to carry out this request. "
    "A run passes when its last trial measures inside the committed ranges."
)
COVER_READER = "runs that passed: "
COVER_READER_OTHER = " "
COVER_SESSION_ROWS = "rows "
COVER_SESSION_NO_TABLE = "no table"
COVER_ALL_SESSIONS = "all sessions of this lab"
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
    "Green ink; a block of it has the label written by Dr. Kiro."
)
INK_PENCIL_NAME = "Pencil"
INK_PENCIL_ABOUT = (
    "Text the bench recorded, and numbers the notebook computes from it: measurements, outcomes, "
    "condition classes, reasons and counts. Monospace type, grey."
)
INK_COMMENTARY_NAME = "Commentary ink"
INK_COMMENTARY_ABOUT = (
    "Our own text, written by the builder of the lab: the titles and summaries, headings, labels and "
    "explanations. Ordinary type, with a small mark saying our notes."
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
NO_STEP = "the record has no step to replay: it has no verdict snapshot and no end snapshot"
REPLAY_INTRO = "Each step shows the session as the record holds it at that snapshot, in record order."
REPLAY_LABEL = "replay of a sealed record"
REPLAY_STEP = "Step "
REPLAY_STEP_OF = " of "
REPLAY_AFTER_VERDICT = ", after a verdict"
REPLAY_AT_END = ", the end of the session"
REPLAY_BACK = "back"
REPLAY_FORWARD = "forward"
REPLAY_PLAY = "play"
REPLAY_TO_SESSION = "back to the session page"
REPLAY_NOT_RUN = "This item has not been run at this step, so it is left out here."
NOT_YET_CHECKED = "not yet checked by the bench"

# The highlight (Requirements 10.3, 10.4, 12.7).
HIGHLIGHT_CONTRAST = "A contrast: two trials side by side"
HIGHLIGHT_BEST = "The best result"

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
# The prediction chart (Requirements 5.4, 17.1-17.5; task 17.1).
CHART_HEADING = "Prediction chart"
CHART_INTRO = (
    "Every registered prediction, in the order it was registered. Each measurement has one scale, which "
    "spans the lowest and the highest registered bound and measured value of that measurement in this "
    "session. A filled circle marks a hit, and a circle in miss red with the word miss marks a miss. A "
    "prediction that was not run or not checkable has its registered range only."
)
CHART_NONE = "No prediction is registered in this session, so the chart has nothing to show."
CHART_SCALE = "; scale of the measurement "
CHART_NO_VALUE = "; no measured value is drawn"

# Dr. Kiro's plan (Requirement 10.6, design N18).
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
PREDICTION_LABEL = "Dr. Kiro's label: "
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

# How the lab works, `how.html` (Requirement 18). No builder spec is quoted, and no file or folder outside a
# lab is named or linked (18.5, design N24).
HOW_TITLE = "How the lab works"
HOW_INTRO = (
    "Dr. Kiro is an agent that experiments on a system it has no description of, and writes that "
    "system's spec from the evidence of its trials."
)
HOW_LEVELS_HEADING = "Two levels of spec"
HOW_LEVEL_BUILDER = (
    "The builder's specs built the lab: the bench, which holds Dr. Kiro to the method, the two "
    "applications that plug into it, and this notebook. Dr. Kiro never sees them."
)
HOW_LEVEL_DRKIRO = (
    "Dr. Kiro's lab spec is written by Dr. Kiro from evidence: its requirements hold the hypotheses and "
    "their predictions, its design holds the discovered spec table, and its tasks hold the plan. Before a "
    "session can end, the bench checks the table against the record."
)
HOW_TOUCH_HEADING = "What Dr. Kiro can and cannot touch"
HOW_CAN = (
    "Dr. Kiro can read and write the spec files and the experiment files of its own lab folder, and it can "
    "call the four bench tools:"
)
HOW_TOOL_REGISTER = "register_hypothesis: register a hypothesis and its predictions before any trial of it."
HOW_TOOL_RUN = "run_experiment: run one experiment file, one trial at a time, within the budget."
HOW_TOOL_VERDICT = "record_verdict: give a verdict on a hypothesis after its experiment."
HOW_TOOL_END = "end_session: end the session; the bench first checks the discovered spec table."
HOW_CANNOT = (
    "Dr. Kiro has no shell and cannot open any other folder. The bench returns measurements, pictures and "
    "the remaining budget, and nothing else."
)
HOW_WORDING = (
    "The notebook's own text describes motion by direction, distance, heading, speed, symmetry and which "
    "channels were active. Dr. Kiro's text is shown as written."
)
HOW_APPS_HEADING = "The two applications"
HOW_APPS_INTRO = (
    "What each application declares, as the bench recorded it at the start of each session. Records of one "
    "application that hold different declarations are shown apart."
)
HOW_APP_SESSIONS = "Sessions with this declaration: "
HOW_GOAL = "Goal: "
HOW_KNOBS = "Knobs, each with its kind and declared range:"
HOW_KNOB_KIND = ", kind "
HOW_KNOB_RANGE = ", range "
HOW_RANGE_OPEN = "["
HOW_RANGE_CLOSE = "]"
HOW_MEASUREMENTS = "Measurements, each with its unit and kind:"
HOW_MEASUREMENT_UNIT = ", unit "
HOW_MEASUREMENT_KIND = ", "
HOW_BUDGET = "Budget, in trials per session: "
HOW_PICTURE = "Picture of each trial: "
HOW_REFUSALS_HEADING = "Refusals, per session"
HOW_REFUSALS_INTRO = (
    "How often the bench refused an action of Dr. Kiro, and why, as recorded. A refused action runs "
    "nothing and uses no budget."
)
HOW_REFUSALS_BY_ACTION = "Refusals by action: "
HOW_SESSION_OF = ", session "

# The banner of a build from labelled test fixtures (design N19). The command line never shows it.
FIXTURE_BANNER = (
    "test fixture: this page is built from labelled fixture records, and nothing on it is a result."
)


# The shelf and the opened notebook (notebook-shelf design). Orange-pen commentary of the builder.
SHELF_TITLE = "Dr. Kiro's Lab Notebook"
KICKER = "laboratory notebook · discover the spec"
MASTHEAD_TITLE = "Dr. Kiro's Lab Notebook"
KEY_GREEN = "green ink: Dr. Kiro's own words"
KEY_PENCIL = "pencil: values the bench measured"
CARD_BEST = "best "
CARD_HITS = " predictions came true"
CHIP_MODEL = "model "
CHIP_DATE = "date "
CHIP_PREDICTIONS = " predictions, written before the run, came true"
CHIP_STOPPED = "stopped: "
CHIP_NO_TABLE = "no discovered spec in the record"
HIGHLIGHT_HEADING = "The highlight and progress"
HIGHLIGHT_NONE = "No trial ran in this session, so there is nothing to show here."
NEW_BEST = "new best"
NOTE_BEST_BEFORE = "best "
NOTE_BEST_AFTER = " so far, set by "
NOTE_NO_BEST = "No trial counts toward the best yet."
NOTE_HITS = "predictions, written before the run, came true"
NOTE_REJECTED_RULES = "rules rejected, each kept in the table beside its replacement"
NOTE_REJECTED_VERDICTS = "hypotheses Dr. Kiro rejected (this record holds no table)"
PROGRESS_NONE = "No trial counts toward the best, so there is no line to draw."
PROGRESS_LINE = "The line is the best "
PROGRESS_BETTER_HIGHER = " after each trial (higher is better). Each step up names the hypothesis behind it."
PROGRESS_BETTER_LOWER = " after each trial (lower is better). Each step down names the hypothesis behind it."
PROGRESS_ONLY_WHEN = " Only trials with "
PROGRESS_OFF = " count."
SPEC_HEADING = "The discovered spec"
SPEC_NONE = "The record holds no discovered spec table that can be shown."
SPEC_UNCHECKED = (
    "This table is the last one in the record. The bench did not check it, because the session "
    "did not end through the bench's check."
)
REWRITTEN_AS = "rewritten as "
REWRITTEN_NOWHERE = "rewritten nowhere: "
FROM_EXPERIMENTS = "from "
FROM_PREDICTIONS = " · predictions "
PLAN_HEADING = "Dr. Kiro's plan"
ALL_BEFORE = "All "
ALL_AFTER = " experiments and hypotheses"
ALL_HINT = "Press a row to open the note: Dr. Kiro's words and every trial of that hypothesis."
EXPECTS = "expects "
NEVER_RUN = "never run"
OUTCOME_NOT_RUN = " not run"
READER_HEADING = "The reader's test"
READER_ABOUT = (
    "A second Kiro, the reader, never saw the experiments. It answered this request three ways. "
    "Pass or fail is decided by the bench against ranges written before the runs."
)
READER_SETUP_SPEC = "Spec only"
READER_SETUP_RECORD = "Raw record only"
READER_SETUP_NONE = "Nothing"
READER_PASSED = "runs passed"
READER_SETUP_BORROWED = "Spec of an earlier session: "
READER_BORROWED_RULES = "Rules it relied on, as that session's table states them:"
CHIP_BODY = "body "
STORY_BORROWED_A = " Given the spec of "
STORY_BORROWED_B = ", written before the body changed, "
READER_RUN_FIRST = ": first in range at "
READER_RUN_LAST = ", last trial "
READER_RUN_NEVER = ": never in range; last trial "
READER_RUN_CITED = ". Relied on "
READER_RUN_CITED_NONE = ". Named no rule it relied on."
READER_RUN_LIMIT = "Noted by the run: "
CLOCK_FORWARD = "forward "
CLOCK_BACK = "back "
CLOCK_AT = "at the start"
OURS = "our notes"
RULE_MORE = "conditions and evidence"
PLAN_HINT = "Press a step to read all of it."
SYNC_PLAY = "Play"
SYNC_PAUSE = "Pause"
SYNC_LABEL = "Time"
PREDICTION_IN = " in "
NOTE_MISSED = " missed: "
NOTE_EXPECTED = " was expected in "
NOTE_TRIALS_USED = " used, of the whole budget"
FRONT_LINK = "both labs"
KEY_NOTES_BLUE = "blue pen: our notes"
KEY_NOTES_ORANGE = "orange label: our notes"
FRONT_KICKER = "a laboratory · two cases"
FRONT_TAGLINE = "The experiment gets the final edit."
FRONT_LEAD = (
    "Dr. Kiro, a Kiro agent, studies a system it has no description of and writes down the spec it finds. "
    "Two applications stand on one skeleton. Choose a door."
)
DOOR_DAY = "opens by day"
DOOR_NIGHT = "opens at night"
SKELETON_HEADING = "The skeleton under both"
SKELETON_NOTEBOOK = (
    "The notebook: one page maker for both. It reads the sealed records and tells each session as a story."
)
SKELETON_BENCH = (
    "The bench: one method for both. A hypothesis before every experiment, a fixed budget, and a record "
    "that is sealed and cannot be edited."
)
OF = " of "
STORY_HEADING = "What happened here"
STORY_NONE = "No prediction was written, so there is nothing to tell."
STORY_WROTE_BEFORE = "Dr. Kiro wrote "
STORY_WROTE_AFTER = " predictions, each before its experiment ran."
STORY_CHECKED_STOPPED = " checked predictions came true before the session stopped."
STORY_MISSED = " missed. "
STORY_STRUCK = " rules were struck out and rewritten."
STORY_MISSED_NONE_STRUCK = " missed, and no rule had to be struck out."
STORY_MISSED_LEFT = " missed. No rule was struck out, but the miss kept "
STORY_MISSES_LEFT = " missed. No rule was struck out, but the misses kept "
STORY_LEFT_AS = " at "
STORY_LEFT_END = " instead of validated."
STORY_MISSED_NO_TABLE = " missed. This record has no final spec table, so no rule was checked."
STORY_READER_A = "Another Kiro, given only this spec, did the task in "
STORY_READER_B = " tries. With nothing, "
STORY_END = "."
STORY_TRUST_A = " rows are validated and can be trusted; "
STORY_TRUST_B = (
    " are only partly tested or observed, so a reader knows what to test next. "
    "No second Kiro has been run on this spec yet."
)
STORY_NO_SPEC = "This record has no final spec, so there is nothing yet for a next Kiro to read."
HIGHLIGHT_INTRO = "The two moments that tell the story, three numbers, and how the best result grew."
SPEC_INTRO = (
    "What Dr. Kiro now believes about this system. A struck line was believed, tested, and proved wrong; "
    "the line under it replaced it."
)
PLAN_INTRO = "The steps Dr. Kiro wrote for itself, in order. A solid circle is a step it finished."
ALL_INTRO = "Each card: what Dr. Kiro predicted before the run, and what happened."
READER_INTRO = "The test of the spec: another Kiro, who never saw the experiments, is given one task."
PROGRESS_MARK_A = " The dashed line marks the first trial where "
PROGRESS_MARK_B = "."
OTHER_LAB = "the other lab: "
STOPPED_HEADING = "Sessions that stopped early, kept as they ended"
