# Requirements Document

Spec: `lab-notebook`.

## Introduction

The lab notebook is a static website built from the sealed session records. A visitor (for example a hackathon
judge) should understand in 60 seconds what Dr. Kiro discovered, and see that every line of it has evidence. The
notebook is built around Dr. Kiro's `## Discovered spec` table (`lab-bench` Requirement 12). It shows the table as
the sealed record holds it and never makes up a status, a row or a replacement.

Source: `docs/brief.md` sections 1-3 and 4.4 (with 4.1 and 4.5), `lab-bench` requirements (Requirements 6, 7, 10,
12, 13 and 15 in particular), `bench/src/bench/conditions.py` (the bench's condition classes) and
`bench/src/bench/scan/levels.py` (the blind scan's per-author sidecar files), the `body-lab`
and `wind-tunnel` specs (the picture sheets), the sealed records in `sessions/`, and the user's answers recorded
under "Decisions". All steering in `.kiro/steering/` applies, in particular `rules.md`.

Which Kiro: the notebook is built by **the builder** and read by **visitors** (people). **Dr. Kiro** and **the
reader** (`build-from-spec`) never see the notebook: it is built outside every `lab/` folder and is not given to
either of them. Every requirement names whom it concerns.

The records the notebook is built from today (facts read from `sessions/`, used to make the requirements testable;
they are not results restated by the notebook):

- `body-lab/body-1`: ended, 40 trials, 11 hypotheses, 18 prediction outcomes of which 8 are misses, 22 snapshots
  (after each run and after each verdict), no `end` snapshot; every snapshot's `## Discovered spec` table has no
  rows. Parameter names are declared per experiment by Dr. Kiro, and one name can mean different things in
  different experiments.
- `wind-tunnel/wt-004`: ended, 18 of 24 trials, 6 experiments, 17 outcomes of which 1 is a miss. The `end`
  snapshot holds a table with rows R1-R6 (four `validated`, one `partly`, one `observed`, no `rejected`). One trial
  has the not-measured outcome `not_settled` for all five measurements.
- `wind-tunnel/wt-002`: stopped, 3 trials, 1 experiment, 2 hits, one hypothesis registered and never run, no table
  rows.
- `wind-tunnel/wt-003`: stopped at its first action, 0 trials, no snapshots.
- `body-lab/body-2`: ended by Dr. Kiro, 39 of 40 trials (remaining budget 1), 11 hypotheses, 11 experiments, 24
  prediction outcomes, 23 snapshots, 3 refusals (one `register`, two `end`), one verdict flag (E5, verdict
  `partly`, counts hit 0, miss 1). Every snapshot before `end` has a `## Discovered spec` table with no rows, which
  the bench's table reader does not accept (Decision 45). The
  `end` snapshot has 14 rows: `validated` R9, R11; `observed` R1, R5, R7, R13; `rejected` R2 (replaced by R1), R3
  (R11), R4 (R5), R6 (R7), R8 (R9), R10 (R11), R12 (R13), R14 (R13). One row can replace several rows (R11, R13), a
  replacing row can come before the row it replaces (R2 by R1), and a replacing row can be `observed`. Cells contain
  escaped pipes (`\|heading\|`). Dr. Kiro was taught by its templates to keep a refuted rule as a `rejected` row
  (`dr-kiro` Requirement 3.7).
- body-2's two `end` refusals carry the same message, recorded as parts: bench text "the discovered spec table does
  not agree with the record: ", ".kiro/specs/lab/design.md line 32: ", "row ", a quote (author `dr-kiro`) "R13",
  ": ", "a validated rule needs at least one hit that is a new combination or outside the tried range (", a quote
  (author `dr-kiro`) "H11.P3: hit/not-comparable", ")". The record holds no copy of the refused `design.md`
  (snapshots are taken only at an accepted end); the sealed R13 is `observed`. The second quote is recorded with
  author `dr-kiro` on purpose: the bench treats the cited-outcome summary as a quote because prediction ids are Dr.
  Kiro's (`bench/src/bench/specfiles/discovered.py`, `_summary`), although "hit" and "not-comparable" are the
  bench's words.
- In body-2, H11.P3 is `not-comparable` because E11 declared a new parameter name `sq`, so the parameter group
  {a1, s3, f, sq} had no earlier trials. R13 cites E10 ({a1, s3, f}) and E11 ({a1, s3, f, sq}): two parameter
  groups.
- 9 trials of body-2 have the same trial key as trials of body-1 (body-1/body-2: T7/T7, T8/T8, T3/T4, T2/T3, T4/T5,
  T6/T25, T1/T2, T5/T6, T9/T9), all with exactly equal measurements, although their parameter names differ (`k` in
  one, `a0`..`a4` in the other).
- body-2 H4.P1 (trial T12, parameters `a` 1, `f` 1, `ph` 1.5): registered range for `x` [0.2, 3.0], measured `x`
  -0.2047 (heading -84.25, `y` 0.097). It is cited by R4 (`rejected`, replaced by R5; R5 is `observed`, cites E4 and
  E5 and no predictions). The T12 sheet shows the body turning about a quarter turn; the backward drift of 0.2 m is
  faint in the picture (the body is about 30 px in a 320 by 180 cell), and the recorded track shows it clearly.
- body-lab goal, from the declaration: "Move the body as far as possible in the direction it faces at the start:
  maximise x."

Scope: the notebook build (a Python program run through `uv`), the site it writes, the visual system written as
steering, the committed choice files, the frame layout table, and the tests. Deployment is in `publish`. The runs
shown in "Built from the spec" are made by `build-from-spec`; this spec only shows them.

## Glossary

- **Notebook**: the static website specified here.
- **Build**: the Python program that reads the inputs (Requirement 1) and writes the site.
- **Site**: the files the build writes: HTML, CSS, JavaScript, PNG files, and nothing fetched from elsewhere.
- **Visitor**: a person reading the site.
- **Record**: a sealed session record in `sessions/<application>/<session-id>/` (`lab-bench` Requirement 13).
- **Ended session, stopped session**: a record whose seal entry has `end` `ended` or `stopped`.
- **Snapshot**: a copy of Dr. Kiro's three lab spec files in a record, taken after a run (`for` `experiment`),
  after a verdict (`for` `verdict`), or at an accepted end (`for` `end`) (`lab-bench` Requirement 10).
- **Discovered spec table**: the `## Discovered spec` table in a snapshot's `design.md`, read with the bench's own
  table reader.
- **Row**: one row of a discovered spec table, with the columns id, rule, scope, experiments, predictions, status
  and replaced by.
- **Status word**: one of `validated`, `partly`, `observed`, `rejected`, as written in a row and checked by the
  bench at the end (`lab-bench` Requirement 12.3).
- **Verdict**: Dr. Kiro's judgement of a hypothesis after an experiment: `supported`, `partly` or `rejected`, with
  Dr. Kiro's words (`lab-bench` Requirement 8).
- **Prediction outcome**: hit, miss, not checkable or not run, as recorded by the bench.
- **Condition class**: the bench's class of a prediction's conditions, recorded at registration: `inside`,
  `new-combination`, `outside` or `not-comparable` (`bench/src/bench/conditions.py`).
- **Dr. Kiro's label**: the class Dr. Kiro gave a prediction itself, recorded beside the condition class.
- **Cited experiments, cited predictions**: the experiment ids and prediction ids a row names.
- **Cited trials**: all trials of a row's cited experiments.
- **Prediction trials**: the trials whose outcome entries belong to a row's cited predictions.
- **Parameter group**: within one session, the trials of all experiments that declare the same set of parameter
  names. This is the set of trials the bench compares a prediction with (`lab-bench` Requirement 6.4).
- **Run band**: the drawing, for one parameter of one parameter group, of what was run (Requirement 9).
- **Picture sheet**: the one PNG of a trial: equal cells laid out in rows, in time order from left to right, then
  top to bottom.
- **Frame layout table**: the notebook's table of each application's picture sheet layout (Requirement 7).
- **Moving picture**: a picture sheet shown one cell at a time, in time order, repeated.
- **Choice file**: a committed file, written or approved by the user, that names a session's highlight and missed
  prediction (Requirement 12).
- **Cover file**: a committed file, written or approved by the user, that names what the cover shows
  (Requirement 13).
- **Ink**: one of three fixed text styles that say who wrote a text: Dr. Kiro's ink, commentary ink, pencil.
- **Commentary**: text written by the builder for the notebook (headings, explanations, labels).
- **Replay**: the session page shown as of one step of the session (Requirement 16).
- **Step**: one snapshot taken after a verdict, or the `end` snapshot.
- **Build-from-spec run**: one sealed run record of `build-from-spec` (`docs/brief.md` 4.5).
- Other terms as in `lab-bench`.

---

## Requirements

### Requirement 1: Inputs of the build

**Concerns:** the builder.

**User Story:** As the builder, I want the notebook built only from sealed and committed inputs, so that every
line on the site can be traced to the record.

#### Acceptance criteria

1. THE build SHALL read only: the records in `sessions/`; the choice files and the cover file; the frame layout
   table; the commentary word list (Requirement 5.5); the build-from-spec runs and their committed requests, in the
   places the `build-from-spec` spec defines; the files the bench's blind scan reads (the applications' model and
   solver files and the stop list, `lab-bench` Requirement 15), read only through the bench's scan
   (Requirement 20); and the notebook's own source files.
2. THE build SHALL NOT read `discovered/`, any `lab/` folder, `bench-run/`, or any file that is not listed in 1.1.
3. THE build SHALL take every folder it reads and the output folder as explicit arguments, and SHALL refuse to run,
   naming the missing argument, if one is missing. It SHALL NOT fill in a default folder.
4. IF the output folder exists and is not empty, THEN THE build SHALL refuse, naming it, and SHALL NOT overwrite or
   merge into it.
5. THE build SHALL run with Python 3.12 through `uv`, as its own `uv` project in `notebook/`, SHALL need no Node
   and no Docker, and SHALL run no simulator or solver. It SHALL depend on the bench and on both applications'
   adapter packages by path only, so that the bench's blind scan can import each adapter's declaration for the
   allow list (`bench/src/bench/scan/terms.py`) (Decision 42).

### Requirement 2: Checks before anything is written

**Concerns:** the builder.

**User Story:** As the builder, I want the build to stop at the first input that is not what the record promises,
so that the site never shows a broken or altered record.

#### Acceptance criteria

1. WHEN the build starts, THE build SHALL run every check of this spec (Requirements 1.3, 1.4, 2, 4.2, 7, 12, 13,
   19.2 and 20) on all inputs before it writes any file to the output folder.
2. IF a hash chain check (`lab-bench` Requirement 13.4) fails, THEN THE build SHALL fail, naming the record and the
   first entry or file that does not match.
3. IF a record in the sessions folder given to the build is not sealed, or has a trial labelled fake (`lab-bench`
   Requirement 14.5), THEN THE build SHALL fail, naming the record. Tests MAY build fixture records into a
   temporary output folder that is never published.
4. IF a record is an ended session with an `end` snapshot, THEN THE build SHALL run the bench's own discovered spec
   table check (`lab-bench` Requirement 12) on that snapshot's `design.md` against the record, and SHALL fail,
   naming the row, if the check fails.
5. IF an ended session has no `end` snapshot (body-1), THEN THE build SHALL show the session as "no table"
   (Requirement 10.9) and SHALL NOT run the table check.
6. THE build SHALL read discovered spec tables with the bench's own table reader, and SHALL NOT have a second
   reader.
7. IF any check of this spec fails, THEN THE build SHALL fail, naming the file and the problem, and SHALL leave the
   output folder absent or empty.
8. THE build SHALL NOT skip a record, a row, a trial or a picture to make a build pass.

### Requirement 3: What the site is

**Concerns:** the builder and the visitor.

**User Story:** As a visitor, I want a plain website that works on my phone and asks nothing of other servers, so
that it is fast, private and lasts.

#### Acceptance criteria

1. THE site SHALL be plain HTML, CSS and JavaScript, written by the build, with no framework, no third-party
   library and no build step in Node.
2. THE site SHALL make no request to any host other than its own: no CDN, remote font, analytics, embed or remote
   image. Every asset SHALL be a file of the site, referenced by a relative URL that contains no `..`. Every page SHALL be at
   the site root, and only pictures and assets SHALL be in subfolders (Decision 46).
3. THE site SHALL have no chat box and no control that starts an experiment, a session or a build-from-spec run,
   and SHALL send no data anywhere.
4. THE text, the discovered spec tables and the experiment entries SHALL be present in the HTML as written by the
   build, and SHALL need no script to be shown; moving pictures and the replay controls MAY need JavaScript.
5. WHEN the viewport is 360 CSS pixels wide, THE page's scroll width SHALL NOT exceed the viewport width; a wide
   table MAY scroll inside its own box.
6. WHEN a visitor's browser asks for reduced motion, THE site SHALL show each moving picture stopped on its first
   cell, with a control to step and to play it.
7. THE site's own text SHALL be in English.

### Requirement 4: Text by its author, shown as written

**Concerns:** the builder and the visitor. The rule protects Dr. Kiro's words.

**User Story:** As a visitor, I want to see who wrote every text and to read Dr. Kiro's words exactly as it wrote
them, so that I can tell its claims from our comments and from the measurements.

#### Acceptance criteria

1. THE site SHALL show every text in one of three inks, with fixed meanings used everywhere: Dr. Kiro's ink for
   text whose recorded author is Dr. Kiro; pencil for text whose recorded author is the bench (measurements,
   outcomes, condition classes, reasons, counts) and for numbers the build computes from them; commentary ink for
   the builder's text. Status words are the one exception: they are shown in the bench's stamp style
   (Requirements 8.2, 15.2).
2. THE ink of a text SHALL follow from the author recorded with it in the record (`lab-bench` Requirement 9.5), or,
   for the notebook's own text, from the build source. IF the author of a text cannot be determined, THEN THE build
   SHALL fail, naming the text's place in the record. Exception: values Dr. Kiro passed to the bench that the bench
   records as fixed words without an author (the verdict word and Dr. Kiro's label of a prediction) SHALL be shown
   in Dr. Kiro's ink (Requirements 15.1, 17.4), and THE build SHALL scan each of them at the builder level as well
   as at Dr. Kiro's level (Requirement 20.1) (Decision 47).
3. THE site SHALL show text written by Dr. Kiro as written: the same characters in the same order, with its line
   breaks, HTML-escaped, and not rendered as Markdown or HTML. The cells of a discovered spec table are shown as
   the bench's table reader gives them.
4. FOR ALL texts written by Dr. Kiro, the text content of the element that shows the text, parsed from the
   written HTML, SHALL equal the text in the record character for character, including line breaks (round-trip
   property).
5. THE ink SHALL be distinguishable without colour: each ink SHALL also differ in typeface or style, and a legend of
   the three inks SHALL be reachable from every page.
6. Text SHALL have a contrast ratio of at least 4.5:1 against its background.

### Requirement 5: Honest numbers and words

**Concerns:** the builder.

**User Story:** As a visitor, I want every number on the site to come from a recorded run, so that nothing is made
to look better than it was.

#### Acceptance criteria

1. EVERY number THE site shows as a result SHALL be taken by the build from a record field (a measurement, a range,
   a count, a budget, a condition value) or computed by the build from record fields in a way this spec names.
2. THE notebook's source files SHALL contain no number presented as a result; tests use fixtures that are labelled
   as fixtures and are never written to a site (`rules.md` 4).
3. THE site SHALL show measured values in lists, tables, charts and the cover rounded to 4 significant digits,
   and SHALL show the recorded value in full in the opened trial. Counts, budgets and ids SHALL NOT be rounded.
4. WHEN a measurement is a not-measured outcome, THE site SHALL show the outcome name and the bench's reason as
   recorded, and SHALL NOT show or plot a value for it.
5. THE commentary SHALL describe the body's motion only by direction, distance, heading, speed, symmetry and which
   channels were active, and SHALL contain no word that suggests human injury or disability (`rules.md` 4). A test
   SHALL check the commentary against a word list kept in `notebook/` and approved by the user; adding or removing
   a word needs the user's approval. Dr. Kiro's text is shown as written (4.3) and is not changed by this rule.

### Requirement 6: The visual system

**Concerns:** the builder (later parts stay consistent) and the user (compares the result with a reference).

**User Story:** As a visitor, I want a scientist's paper notebook, not a dashboard, so that the page reads like a
record of work.

#### Acceptance criteria

1. THE builder SHALL write the visual system as a steering file, `.kiro/steering/notebook-visual.md`, before the
   pages are built: paper, the three inks, the miss red, the status stamp, pinned instant photos, sticky notes, the
   strike-through of a rejected row, type, spacing, and the narrow-screen layout.
2. THE site SHALL have one look in two palettes, the day paper and the night lab, chosen only by the visitor's
   system colour scheme (`prefers-color-scheme`), with no theme switch, no script and no stored choice. Every text
   pair SHALL reach the ratio of Requirement 4.6 in both palettes, and the recorded pictures SHALL be shown as
   recorded in both (Decision 52).
3. Moving pictures SHALL be shown as instant photos pinned to the page; side notes in commentary ink SHALL be shown
   as sticky notes.
4. THE miss red SHALL be used only for missed predictions and their measured values, and SHALL always come with
   the word "miss"; on the cover the stamp "missed" says it (13.9).
5. Halloween SHALL appear only as small decoration that holds no text, does not overlap any text, table, chart or
   experiment entry, and does not lower the contrast of any text below the ratio of Requirement 4.6. THE decoration SHALL be inline in the
   page markup, not a separate file, and SHALL carry no namespace URL (Decision 46).
6. WHEN the user describes a difference from the reference, THE builder SHALL update this requirement or the
   steering file first, and the pages after.

### Requirement 7: Picture sheets and moving pictures

**Concerns:** the builder and the visitor.

**User Story:** As a visitor, I want to see each trial move, so that I understand what happened without reading
numbers.

#### Acceptance criteria

1. THE notebook SHALL keep a frame layout table, `notebook/layouts.toml`, with one entry per application: the
   number of frames, rows, columns, the gap in pixels between cells, and the interval in milliseconds at which a
   moving picture shows one cell (body-lab 220, wind-tunnel 150), with the application's spec named as the
   source of each entry (`body-lab` design: 10 frames, 2 rows of 5, no gap; `wind-tunnel` Requirement 9.4: 6
   frames, 2 rows of 3, a gap of 4 pixels).
2. IF an entry's number of frames does not equal its rows times its columns, THEN THE build SHALL fail, naming the
   entry.
3. WHEN the build reads a trial's picture, THE build SHALL check that the media type is `image/png`, that the file
   passes the bench's picture check, and that its width and height divide exactly into the layout of its
   application (columns times the cell width plus the gaps, and likewise for rows). IF a check fails, THEN THE
   build SHALL fail, naming the record, the trial and the sizes.
4. THE notebook SHALL NOT change any file in `bench/`.
5. IF a record's application has no entry in the frame layout table, THEN THE build SHALL fail, naming it.
6. THE site SHALL show a moving picture by showing the cells of the sheet in reading order (left to right, then top
   to bottom), one at a time at the rate of the application's entry in the frame layout table (7.1), and then starting again. THE
   site SHALL show only the cells of the sheet, with no frame made between two of them.
7. THE site SHALL copy each picture as recorded, byte for byte, under a name made from its blob hash, and SHALL NOT
   re-encode it.
8. A moving picture SHALL have controls to pause, to step one cell, and to see the whole picture at once; on a
   narrow screen and on a touch screen each control SHALL be at least 44 by 44 CSS pixels.
9. FOR each body-lab trial's moving picture, except the small pictures of the lab cards (Requirement 13.4), THE site
   SHALL show beside it (on the cover, in the top row of the miss: 13.1) an enlarged picture of the moving body: a magnified view, derived by the build from the record's own
   picture sheet, in which the body in its cell is readable. THE build SHALL choose the region of the enlarged picture
   as the box, over all frames of the sheet, of the pixels that change between frames, plus a margin of 4 pixels,
   clipped to its cell; SHALL scale it by the smallest whole-number factor (nearest neighbour) that makes it at least
   as large as the frame; and, WHEN no pixel changes, SHALL use the whole cell. THE build SHALL NOT use the track to
   choose the region, because the records hold no mapping from track coordinates to picture pixels. THE build SHALL
   derive the enlarged picture at build time, SHALL NOT change the recorded PNG file (Requirement 7.7 still holds for it), SHALL write the
   enlarged picture as a file of the site with a name made from the blob hash, and SHALL give it the alt text
   "Magnified view of the picture beside it", which uses no word of the commentary word list (Requirement 5.5)
   (Decision 50). THE enlarged picture SHALL move as a moving picture does (7.6, 7.8), with the interval of the
   trial's application; the whole picture of a body-lab trial SHALL NOT be on the page at first, because its cells side by side read as many small bodies; the control "whole picture" of the enlarged picture SHALL swap it in at the same place, and it SHALL then move one cell at a time with the same interval. On the cover, the enlarged picture's caption SHALL say what the picture is and that it plays one recorded frame at a time, and SHALL change with the swap to a caption of the whole picture (and back), without the script showing the caption of the first frame. A body-lab picture without an enlarged one (a lab card) SHALL show its first cell only. THE site SHALL NOT show an enlarged picture beside a wind-tunnel trial's moving picture, because
   the flow moves through the whole sheet and no region of it is the moving body (Decision 50).

### Requirement 8: The discovered spec table

**Concerns:** the visitor and the builder. Dr. Kiro wrote the table; the bench checked it.

**User Story:** As a visitor, I want the discovered spec table at the centre, with each rule's status in the bench's
word and its evidence one press away, so that I see what was found and how sure it is.

#### Acceptance criteria

1. THE site SHALL show each table as the snapshot it comes from holds it (the `end` snapshot on the session page,
   or the step's snapshot in the replay): every row, in the order written, with every cell, and SHALL NOT add,
   drop, merge, reorder or edit a row, a status or a replacement.
2. EVERY row SHALL show its status word written out, in the style of the bench's stamp, labelled "checked by the
   bench" for a table from an accepted `end` snapshot and "not checked by the bench" for any other table. Colour
   MAY add to the word and SHALL NOT replace it.
3. WHERE a row has the status `rejected`, THE site SHALL strike the row through, keep its text readable, keep it in
   its place in table order, and show directly beside it a tab "replaced by <id>" with the id named in its
   "replaced by" cell; WHEN a visitor opens the tab, THE site SHALL show the replacing row's rule text in small type
   with a link to that row in its own place in the table (Decision 32).
4. IF the "replaced by" cell of a `rejected` row names no row of the same table, THEN THE site SHALL show the cell
   as written, with commentary that it names no row of this table, and SHALL NOT pick a row or open a tab with a
   rule text.
5. WHERE a row has the status `partly`, THE site SHALL show each cited prediction whose outcome is miss in the miss
   red, with the word "miss", the registered range and the measured value.
6. WHERE a row has the status `observed`, THE site SHALL explain the word with the bench's check: "seen in
   experiments; no cited prediction missed; Dr. Kiro does not claim validated", and SHALL show, when the row is
   opened, the condition class of each cited prediction as recorded.
7. WHERE a row has the status `validated`, THE site SHALL show, when the row is opened, each cited hit whose
   condition class is `new-combination` or `outside`, with its condition class.
8. WHEN a visitor presses a row, THE site SHALL open the row's cited experiments and cited predictions: for each
   prediction, the hypothesis it belongs to, its conditions, its registered range, its condition class and Dr.
   Kiro's label, its outcome, and the measured value, each linking to its experiment entry (Requirement 11).
9. THE scope cell SHALL be shown as Dr. Kiro wrote it, in Dr. Kiro's ink, with the run bands of the row
   (Requirement 9) beside it. THE build SHALL NOT read the scope text to compute anything.
10. WHERE one or more `rejected` rows name a row in their "replaced by" cell, THE site SHALL show on that row the
    reverse links "replaces <id>, <id>", one per such row, in table order, each linked to the rejected row.
11. THE site SHALL draw each row in full exactly once per table; a replacing row's rule text in a "replaced by" tab
    is the only repeated text.
12. FOR ALL generated tables, each row SHALL be drawn in full exactly once, each `rejected` row whose "replaced by"
    cell names a row of the table SHALL have exactly one tab naming that row, and each row's reverse links SHALL be
    exactly the `rejected` rows that name it (property test).
13. WHERE a row has the status `rejected` and its "replaced by" cell names exactly one other row of the table, THE
    site SHALL show the row's "replaced by" tab open by default, so that the replacing row's rule text and the link
    to that row are readable when the table is shown, without a click. THE tab's content and link SHALL be as in 8.3,
    and a visitor MAY close the tab (Decision 49).
14. THE site SHALL show each row of the table as a card, one block per row, with its stamp, its rule text and its
    other cells, each of the other cells with the name of its column as a small caption; the row's refused-end note
    and its opened row (8.8) SHALL be inside the card. THE header row SHALL stay in the HTML and out of sight. THE
    table and its parts SHALL carry the ARIA roles `table`, `rowgroup`, `row`, `columnheader` and `cell`, so that a
    screen reader still reads a table where the browser drops the table semantics of the card layout. THE card of a
    `rejected` row SHALL be in the rewrite red (Decision 51). WHERE the column beside the margin has room for two
    cards, THE cards SHALL stand side by side. A card SHALL show its rule text, its stamp and its "replaced by" line;
    its scope with the run bands, its experiments, its predictions and its opened row SHALL be closed until the visitor
    opens the card's `<details>`, without a script. THE explanation of the run bands SHALL be on the page once, above the
    cards, in a closed `<details>` with the summary "How to read the bands", without a script. In a `rejected` card only the rule text SHALL be struck through (8.3).

### Requirement 9: What was run, beside each row

**Concerns:** the visitor and the builder.

**User Story:** As a visitor, I want to see, beside a rule's scope, what the record says was actually run and what
no trial ever ran, so that I can compare the claim with the evidence myself.

#### Acceptance criteria

1. THE build SHALL choose a row's parameter groups, its cited ticks, its prediction ticks and its marked span only
   from the row's cited trials and prediction trials; the other ticks of each run band SHALL be the remaining
   trials of those parameter groups in the same session (9.3).
2. THE build SHALL divide the cited trials into parameter groups by the exact set of parameter names their
   experiments declare, the bench's definition (`lab-bench` Requirement 6.4). Experiments whose name sets differ
   SHALL never be one group, even if they share names, and a name shared by two groups SHALL NOT be treated as one
   parameter.
3. FOR each parameter of each parameter group of a row, THE site SHALL draw one run band: a tick for each value of
   the parameter among all trials of that parameter group in the session; the ticks of the cited trials stronger;
   the ticks of the prediction trials strongest; and the span between the lowest and highest cited value marked.
4. WHERE the parameter is a number knob, THE run band SHALL span the knob's declared range from the record's
   declaration, and the parts of the declared range outside the lowest and highest value of the parameter group in
   the session SHALL be hatched and labelled "no trial".
5. WHERE the parameter is one Dr. Kiro declared (it has no declared range), THE run band SHALL span from the lowest
   to the highest value among the parameter group's trials and the cited predictions' conditions, and only the
   parts outside the tried values SHALL be hatched as "no trial".
6. THE site SHALL show combinations of tried values that no trial ran only through the condition class word of each
   cited prediction (`new-combination`), and SHALL NOT draw a grid of combinations.
7. THE parameter names Dr. Kiro declared SHALL be shown in Dr. Kiro's ink, with a link to the experiment file that
   declares them.
8. WHERE an application's knobs are functions of time (body-lab), THE site SHALL also show, for each cited trial,
   one small line plot per channel of its computed input over time, from the record's `inputs`, against the
   declared range [-1, 1] of the channel, in pencil.
   Not in this version (Decision 48).
9. FOR ALL records and rows, the ticks of a run band SHALL be exactly the recorded values of that parameter for
   all trials of its parameter group in the session, and no hatched part SHALL contain such a value (property test
   over generated records).

### Requirement 10: The session page

**Concerns:** the visitor.

**User Story:** As a visitor, I want one page per session that starts with what was discovered and lets me go down
to every experiment, so that I can check any claim.

#### Acceptance criteria

1. THE session page SHALL show these sections first, in this order: the discovered spec table as a notebook page,
   with a sticky note pointing to the chosen missed prediction (Requirement 12) and the moving pictures of the
   chosen trials pinned in its margin; the highlight; the progress; Dr. Kiro's plan; and every experiment entry.
   The other sections of the session page (Requirement 17; Requirement 14.5 is not in this version and Requirement 16 is on hold, Decision 48) SHALL follow them.
2. IF the missed-prediction choice is "none", THEN THE sticky note SHALL show the choice file's reason.
3. THE highlight SHALL show the chosen contrast (two trials side by side) and the chosen best result as moving
   pictures with their measured values, labelled "chosen by a person".
4. IF the contrast or the best result is "none", THEN THE highlight SHALL show "none" and the choice file's reason
   in its place.
5. THE progress SHALL show the budget used and the budget, the experiments by phase, and the counts of each
   prediction outcome, from the record.
6. Dr. Kiro's plan SHALL be the `tasks.md` of the session's last snapshot, shown as written (Requirement 4.3).
7. WHERE a session is an ended session with an `end` snapshot, THE table SHALL come from that snapshot; WHERE a
   session is a stopped session with snapshots, THE table SHALL come from its last snapshot, with its status words
   labelled "not checked by the bench" (10.14 applies where the reader does not accept the table).
8. EACH experiment entry SHALL show: the hypothesis's frozen part as written; its predictions, with conditions,
   range, condition class (labelled "classified at registration") and Dr. Kiro's label; the experiment file as
   written; each trial with its parameter values, its measurements or not-measured outcomes, and its moving
   picture; each prediction outcome; the verdict with Dr. Kiro's words; and the verdict flag if the bench recorded
   one.
9. IF an ended session's record has no `end` snapshot (body-1), THEN THE session page SHALL show "no table" in
   place of the table, with commentary that the record holds no table, and SHALL list every missed prediction of
   the session in its place. THE build SHALL NOT fill in a table. "No table" SHALL be used for no other case
   (Decision 45).
10. WHERE an application's measurements include series (body-lab `track_x`, `track_y`, `track_heading`), THE
   experiment entry SHALL show the recorded track of each trial as a small overhead path in pencil, unless the
   series is a not-measured outcome. Not in this version (Decision 48).
11. WHERE a record holds refusal entries with action `end`, and a quote part of a refusal message equals the id of
    a row of the shown table exactly, character for character, THE session page SHALL attach to that row a sticky
    note in the bench's stamp style: "the bench refused to end this session N times", with N the number of such
    refusal entries, each refusal message shown as recorded with each part in the ink of its recorded author, the
    note that the sealed row's status is the one shown in the table, and the commentary "the record holds no copy of
    the table that was refused" (Decision 33; body-2 R13).
12. THE build SHALL attach the note of 10.11 only by exact equality of a quote part with a row id, SHALL NOT read
    any other meaning from a refusal message, and SHALL NOT infer or show what changed between refusals or between
    a refused table and the sealed table.
13. WHEREVER the site shows a refusal message, THE site SHALL show with it a commentary note that quotes in a
    refusal message are recorded with Dr. Kiro as author, and that some quotes, such as a summary of cited
    outcomes, are composed by the bench from Dr. Kiro's ids; the quote itself SHALL be shown as recorded, in Dr.
    Kiro's ink (Decision 34). Which quotes the note points to is decided in the design; without parsing the
    message, the note covers every quote part of the message.
14. IF the bench's table reader does not accept the table of the snapshot the page shows (this includes a table
    with no rows, which the reader refuses; every snapshot of the real records before `end` is such a table), THEN
    THE site SHALL show that snapshot's `## Discovered spec` section as written, in Dr. Kiro's ink; the message
    the reader returned, as returned, in pencil; and the commentary "the bench's table reader did not accept this
    table"; and, WHERE the table is not from an accepted `end` snapshot, the label "not checked by the bench".
    THE build SHALL NOT parse the message, SHALL NOT guess rows, and SHALL NOT call such a case "no table"
    (Decision 45).

### Requirement 11: Links to one experiment

**Concerns:** the visitor.

**User Story:** As a visitor, I want a link straight to one experiment of one session, so that I can point someone
to the evidence.

#### Acceptance criteria

1. EACH experiment entry SHALL have an address made from the application, the session id and the experiment id,
   and the same inputs SHALL give the same address in every build.
2. WHEN a visitor opens that address, THE site SHALL show the session page at that experiment entry, opened.
3. EACH trial and each prediction SHALL have its own address within its experiment entry.

### Requirement 12: Choice files

**Concerns:** the builder (proposes) and the user (chooses).

**User Story:** As the user, I want the highlight and the missed prediction of each session chosen by a person and
labelled so, so that nothing on the site claims a choice the bench did not make.

#### Acceptance criteria

1. EVERY record SHALL have one committed choice file, `notebook/choices/<application>/<session-id>.toml`, that
   names: a contrast (two different trial ids of the record) or "none"; a best result (one trial id) or "none"; a
   missed prediction (one prediction id) or "none"; and, for each "none", a reason written by the user of 1 to 300
   characters.
2. THE builder SHALL propose candidates for each choice file, drawn from the record, and the user SHALL approve or
   change them before the file is committed.
3. IF a record has no choice file, or a choice file names no record, THEN THE build SHALL fail, naming it.
4. IF a choice names a trial or prediction that is not in the record, or a missed prediction whose outcome is not
   miss, THEN THE build SHALL fail, naming the choice.
5. IF a choice file says "none" for the missed prediction while the record has a missed prediction, THEN THE build
   SHALL accept it only with its reason, and the session page SHALL still list every missed prediction.
6. IF a record has no trial (wt-003) and its choice file does not say "none" for all three choices, THEN THE build
   SHALL fail, naming the choice file.
7. THE site SHALL label every chosen item "chosen by a person".
8. THE reasons in a choice file are builder-level text and SHALL pass the blind scan at the builder level
   (Requirement 20).

### Requirement 13: The cover

**Concerns:** the visitor.

**User Story:** As a visitor, I want a quiet first screen that shows one prediction that missed, so that I see at
once that the experiment gets the final edit.

#### Acceptance criteria

1. THE cover SHALL show, in this order: a head (a kicker, the title, the tagline and one line naming the three
   inks, linked to the ink legend); the missed prediction; the reader (13.11); and one tab per lab (13.4). THE
   missed prediction SHALL be a top row, a row of evidence below it, and the card of rules below that (13.2). THE top
   row SHALL hold the claim card (the prediction in Dr. Kiro's ink; the registered range and the measured value in
   pencil, one under the other, each with a small heading; and the stamp "missed" in the miss red), the sticky note
   (13.8) and, WHERE the trial is a body-lab trial, the magnified picture of Requirement 7.9. THE row of evidence
   SHALL hold one large instant photo playing the image sheet of the trial recorded with the outcome of the
   missed prediction that the cover file names, and the track (13.7).
2. WHEN the table of that session's `end` snapshot has rows, THE card of rules SHALL show every row that cites the
   prediction as a card of its own and, for each such row that is `rejected`, one line in its card with the id and
   the rule text of the row that replaces it (the replacing row is not drawn again as a card); IF no row cites the
   prediction, THEN THE cover SHALL say so.
3. IF the cover file says "none" for the prediction, THEN THE cover SHALL say that the session has no missed
   prediction, in place of the photo.
4. BELOW, THE cover SHALL show one tab per lab, in the order of the cover file. THE panel of a tab SHALL show a
   small moving picture, the trial of which the cover file names, the lab's ended sessions (each with its trial
   count and the number of rows of its `end` table per status word, or "no table"), and a link to the lab's list of
   sessions. Only the panel of the checked tab SHALL show, with no script. WHEN the page is loaded, THE tab of the
   lab of the missed prediction SHALL be the checked one; IF the cover file says "none", THEN the first tab. IF the
   lab of the missed prediction has no tab, THEN THE build SHALL fail, naming the cover file.
5. THE cover file, `notebook/choices/cover.toml`, SHALL name the session of 13.1 and either a prediction or
   "none", and the session and trial of each lab tab, with the four words of the tab (kicker, title, engine, unit);
   the cover SHALL label the choices "chosen by a person"; and the
   build SHALL fail, naming the entry, if the file is missing, names a stopped session, names a session, trial or
   prediction that is not in the records, names a prediction whose outcome is not miss, or says "none" while that
   session has a missed prediction.
6. THE cover's commentary visible before any detail is opened SHALL be at most 240 words, counted as
   whitespace-separated tokens, excluding Dr. Kiro's text and recorded values. Details SHALL open on demand.
7. WHERE the trial of 13.1 has recorded series measurements (body-lab track), THE cover SHALL also show the
   recorded track of that trial as an overhead path in pencil in the row of the photo, unless the series is a
   not-measured outcome (Decision 36). THE track SHALL be drawn in a box cropped to the drawing, so that no empty
   band stands above or below it on a narrow screen (Decision 51).
8. THE sticky note SHALL show the measured value with the name of the measurement and its unit, one sentence of what
   happened, and the conditions of the prediction, from the record alone: "expected <measurement> between <low> and
   <high> <unit>, measured <value> <unit>: below the range" (or "above the range"), with ", on the other side of
   zero" added WHEN the range lies on one side of zero and the value on the other. THE sentence SHALL NOT name a
   direction of travel unless the declaration's `measured_by` text says the measurement is taken in the direction the
   body faces at the start ("x in the direction the body faces at the start"); WHEN it does and the range lies on one
   side of zero, THE sentence SHALL read "expected to go forward <low> to <high> <unit>, went back <value> <unit>"
   ("forward" for a positive number, "back" for a negative one, each number as its size, from the record alone). The
   build SHALL fail IF a missed prediction has no
   value or its value lies inside its range, because the bench records neither (a prediction it cannot check is
   `not-checkable`, not a miss).
9. THE cover SHALL NOT show a row for the outcome of the missed prediction; the stamp "missed" says it.
10. THE `<details>` of the cover SHALL be the last part of the card of rules, inside it.
11. WHERE the build has build-from-spec runs, THE cover SHALL show, after the missed prediction, a section of the
    reader: what the runs were, the committed request in words, and the number of runs that passed per setup, each
    number from the run files.
12. WHEN the viewport is 1000 CSS pixels wide or wider and the top row has a magnified picture (13.1), THE top row
    SHALL have two columns, the magnified picture at the left and, at its right, the claim card and the sticky note
    side by side; WHERE the top row has no magnified picture, THE claim card and the sticky note SHALL stand side by
    side in its one column. THE row of evidence SHALL follow below the top row, so that the prediction, the measured
    value and the stamp stand in the first screen with the picture (Decision 51). On a narrow screen the cover SHALL
    be one column in this order: the claim card, the sticky note, the magnified picture, the moving picture, the
    track and the card of rules.

### Requirement 14: Lab pages and stopped sessions

**Concerns:** the visitor and the builder.

**User Story:** As a visitor, I want to see every session of a lab, including the ones that stopped, so that
nothing that went wrong is hidden.

#### Acceptance criteria

1. EACH lab SHALL have a page listing all its records, ended and stopped, in one list, with the same fields and
   the same type size for every record, ordered by session id in code-point order.
2. FOR each stopped session, THE site SHALL show the seal's end and the bench's reason as written, the budget used
   (the budget minus the recorded remaining budget), and what the record contains: the numbers of trials,
   experiments, hits and misses, the hypotheses registered and never run, whether there is a table, and, if the
   record has a failure entry, the action at which the session stopped.
3. THE commentary about a stopped session SHALL be one fixed text from the notebook's source, the same for every
   stopped session, with the bench's recorded reason shown as written beside it, and SHALL pass the blind scan at
   the builder level.
4. A stopped session SHALL NOT appear on the cover.
5. IF two or more trials of the same application, in any records, have the same recorded trial key (the hash of
   the computed inputs), THEN THE session page of each of those records SHALL show a compact list of those pairs:
   for each pair, the session and trial ids, each trial's parameter names and values as written, and whether all
   their recorded measurements are exactly equal (for example wt-002 T1 and wt-004 T1; the 9 pairs of body-1 and
   body-2). WHEN a visitor opens an entry of the list, THE site SHALL show the two trials' moving pictures side by
   side (Decision 35). Not in this version (Decision 48).
6. A stopped session with snapshots SHALL have a session page with every section of Requirement 10, its table as
   in 10.7 and 10.14 (wt-002: its last snapshot's section as written, with the bench reader's message); a stopped
   session without snapshots (wt-003) SHALL
   have a page that shows only the content of 14.2 (the sentence of 16.9 is on hold, Decision 48).

### Requirement 15: Verdicts and status words kept apart

**Concerns:** the visitor.

**User Story:** As a visitor, I want never to confuse Dr. Kiro's verdict on a hypothesis with the bench-checked
status of a rule, so that `partly` and `rejected` mean one thing where I read them.

#### Acceptance criteria

1. THE site SHALL show a verdict only inside an experiment entry or a replay step, always as "verdict on H<n>:"
   followed by the word, in Dr. Kiro's ink, as Dr. Kiro's judgement.
2. THE site SHALL show a status word only in a discovered spec table row or in a reference to a row by its id, in
   the bench's stamp style, never in Dr. Kiro's ink. This is the one exception to Requirement 4.1. Commentary that
   defines a status word (Requirement 8.6, the ink legend, Requirement 18) MAY name the word in commentary ink, not
   in the stamp style.
3. WHERE the bench recorded a verdict flag, THE site SHALL show the flag as a bench note beside the verdict, with
   the recorded counts of each prediction outcome.

### Requirement 16: Replay

**On hold (Decision 48).** Every criterion below stays as written; the build does not implement it now and the site
has no replay page.

**Concerns:** the visitor and the builder.

**User Story:** As a visitor, I want to step through a session one experiment at a time and see the page as it was,
so that I see a rule struck through and replaced as it happened.

#### Acceptance criteria

1. THE replay SHALL have one step for each snapshot taken after a verdict, in record order, and one final step for
   the `end` snapshot if the record has one. Snapshots taken after a run SHALL NOT be steps.
2. AT each step, everything on the session page SHALL show the state as of that step: the table, Dr. Kiro's plan
   and requirements from that step's snapshot; and the experiments, trials, outcomes, verdicts and budget from the
   record entries before that snapshot's entry in record order, plus that entry. WHERE a chosen item or a pinned
   picture is not among those entries, THE replay SHALL leave it out, with commentary that it has not been run at
   this step.
3. AT a step other than the `end` step, THE status words SHALL be shown with the characters Dr. Kiro wrote, in the
   bench's stamp style, labelled "not yet checked by the bench".
4. WHERE a step's table holds a `rejected` row, THE replay SHALL strike it through and show its replacement beside
   it (Requirement 8.3). Strike-through SHALL appear only where a step's table holds such a row.
5. IF a `rejected` row's "replaced by" cell at a step is empty or names no row of that step's table, THEN THE
   replay SHALL strike the row through, show the cell as written, and show commentary that the named row is not in
   the table at this step, and SHALL NOT pick a replacement.
6. IF the bench's table reader does not accept the table of a step's snapshot (including a table with no rows),
   THEN THE replay SHALL show that step's table as in 10.14, and SHALL NOT guess its rows.
7. THE replay SHALL be labelled "replay of a sealed record" on every step, and SHALL NOT be presented as live.
8. THE replay SHALL have controls to step back, step forward and play. THE address of a step SHALL include its
   1-based step number in record order, SHALL be the same in every build from the same inputs, and opening it SHALL
   show that step.
9. IF a record has no step, THEN THE session page SHALL show, in place of the replay controls, that the record has
   no snapshot to replay; for wt-003 this is shown in addition to the content of 14.2.
10. FOR ALL steps of all records, THE replay test SHALL check that the shown table equals the bench reader's rows
    of that step's snapshot, and that the shown entries are exactly the record entries before that snapshot's
    entry in record order, plus that entry.
11. A test fixture record, labelled as a fixture and never written to a site, SHALL have a middle step whose table
    holds a `rejected` row and its replacement, and the test SHALL check 16.4 against it.
12. WHERE a record holds refusal entries, THE replay SHALL show each refusal as an event of the step whose entries
    it belongs to by 16.2 (the first step whose snapshot entry comes after it in record order), with its message as
    in 10.11 and 10.13; in body-2 the two `end` refusals are shown in the `end` step, after the step of the E11
    verdict. THE replay SHALL attach the refused-end note of 10.11 to a row only at a step whose table holds that
    row.

### Requirement 17: The prediction chart

**Concerns:** the visitor.

**User Story:** As a visitor, I want every prediction against what was measured, so that misses are as visible as
hits.

#### Acceptance criteria

1. THE session page SHALL show, within the progress (Requirement 10.5), a prediction chart of every registered
   prediction of the session.
2. EACH prediction SHALL show its registered range and its measured value on one scale per measurement, spanning
   the lowest to the highest of all registered range bounds and measured values of that measurement in the
   session, with the same mark size for a hit and a miss; a miss SHALL be in the miss red with the word "miss".
3. A prediction that is not run or not checkable SHALL be shown with that word and its range, and with no measured
   value.
4. EACH prediction SHALL show its condition class in the bench's word, labelled "classified at registration", and
   Dr. Kiro's label beside it in Dr. Kiro's ink. WHERE they differ, THE site SHALL show both as they are, without
   comment on which is right.
5. EACH prediction SHALL link to its experiment entry.

### Requirement 18: How the lab works

**Concerns:** the visitor.

**User Story:** As a visitor, I want to understand the method in a few minutes, so that I know why the table can be
trusted.

#### Acceptance criteria

1. THE page SHALL explain the two levels of spec: the builder's specs, which built the lab, and Dr. Kiro's lab
   spec, which it writes from evidence.
2. THE page SHALL say what Dr. Kiro can and cannot touch: its lab folder's spec and experiment files, the four
   bench tools, no shell, no other folder.
3. THE page SHALL show the two applications side by side, from the declaration in each record: knobs and ranges,
   measurements, budget, picture kind and goal. IF records of one application hold different declarations, THEN
   THE page SHALL show each distinct declaration with its session ids.
4. THE page SHALL show, per session, how often the bench refused and why: the count of refusals by action, and each
   refusal's reason as recorded (with "a path outside the lab" where the record has it).
5. THE page's commentary SHALL NOT quote builder spec files, and SHALL name or link no file or folder outside a lab,
   including the repository's root `.kiro/` (Decision 43).

### Requirement 19: Built from the spec

**Concerns:** the visitor. The runs are made by `build-from-spec` with the reader; this spec only shows them.

**User Story:** As a visitor, I want to see whether a Kiro that read only the discovered spec could do what a
request asked, compared with no spec and with the raw record, including the runs that failed.

#### Acceptance criteria

1. WHILE no build-from-spec run is committed, THE section SHALL say that there are no runs yet.
2. WHEN build-from-spec runs exist, THE build SHALL check each run record with its hash chain check before use, and
   SHALL fail as in Requirement 2.2 if a check fails.
3. FOR each run, THE section SHALL show the request in words, the pass condition as committed (its ranges) with the
   commit hash of the request file as recorded in the run record, the spec rows the reader named before running,
   the measured result, and pass or fail as recorded.
4. THE section SHALL group runs by request and show the runs of the three setups (with the spec, with no spec, with
   the raw record only) beside each other. WHERE a request has no run for a setup, THE section SHALL show "no run"
   in that setup's place.
5. Runs that failed or stopped SHALL be shown like the others, in the same list, at the same size.
6. THE build SHALL check pass or fail with the check `build-from-spec` provides, and SHALL fail, naming the run, if
   the recorded result disagrees. THE site SHALL NOT judge a run itself.
7. THE spec rows a reader relied on SHALL link to those rows of the session the spec came from.
8. THE implementation of 19.2-19.7 SHALL come in tasks after the `build-from-spec` spec defines its records; until
   then 19.1 holds.

### Requirement 20: Blind scan of the site

**Concerns:** the builder.

**User Story:** As the builder, I want the site scanned with the same blind scan as the bench output, at the level
of each text's author, so that publishing cannot leak the model.

#### Acceptance criteria

1. BEFORE it writes the site, THE build SHALL scan every text that goes into the site with the bench's blind scan
   (`lab-bench` Requirement 15): the notebook's own text, choice files and the cover file at the builder level
   (terms, paths and file names, credentials); bench-written text from the records at the builder level; and Dr.
   Kiro's text at the Dr. Kiro level (paths and file names, credentials), using the author recorded with it.
2. IF the scan finds anything, THEN THE build SHALL fail, naming the source file and line and the kind of finding,
   and SHALL write nothing.
3. FOR each text file it writes to the site, THE build SHALL write one sidecar file `<file>.authors.json` in the
   format the bench's scan reads (`bench/src/bench/scan/levels.py`), listing the character ranges of the file by
   author, so that the blind scan can scan the written site again at each text's author level (for `publish`)
   without a change in `bench/`. IF a written text has no author, THEN the scan SHALL fail (`lab-bench`
   Requirement 15.7).
4. THE pictures SHALL pass the bench's picture check (Requirement 7.3).
5. A test SHALL show that a term planted in the notebook's own text fails the build, and that the same term in Dr.
   Kiro's text in a fixture record does not.

### Requirement 21: Reproducible build

**Concerns:** the builder.

**User Story:** As the builder, I want the same inputs to give the same site, so that a published notebook can be
rebuilt and compared byte for byte.

#### Acceptance criteria

1. THE same inputs SHALL give the same site, byte for byte. THE build SHALL write no time, date, random value, host
   name or absolute path into the site.
2. THE build SHALL order everything it lists by a rule written in the design, never by file system order.
3. THE build's dependencies SHALL be locked in `notebook/uv.lock`.
4. A test SHALL build the site twice from the same inputs and compare every byte.

### Requirement 22: Done when

**Concerns:** the builder and the user.

**User Story:** As the user, I want a clear point at which the notebook is done, so that the next spec can start.

#### Acceptance criteria

1. THE site SHALL build from the records of both labs in `sessions/`, with the committed choice and cover files.
2. EVERY row of every discovered spec table SHALL show its status word (test over all records).
3. THE replay SHALL match the snapshots at every step (Requirement 16.10 and 16.11). On hold (Decision 48).
4. THE user SHALL accept the first screen. The builder SHALL show the cover on a desktop screen and a 360-pixel-wide
   screen and record the user's answer in `docs/status.md`; any change the user asks for goes first into
   Requirement 6 or the steering file (6.6).
5. THE session page of body-2 SHALL show its 8 `rejected` rows struck through, each with its "replaced by" tab
   (8.3) and each replacing row with its reverse links (8.10), and R13 SHALL carry the refused-end note (10.11); a
   test SHALL check this on the real body-2 record. The test of the strike-through at a middle replay step with the
   fixture of 16.11 is on hold (Decision 48).

---

## Decisions

Items 1-13 were decided by the user in the session before these requirements were written. Items 14-31 were
decided by the builder under the user's delegation (the user's item 14: "any remaining details: the builder decides
and writes the decision into the requirements"). Items 32-44 were decided by the user after the body-2 record was
sealed; each is marked "(user)", and a part decided by the builder under delegation says so. Nothing here makes an
exception to a rule.

1. **What was run, per row** (user). All trials of the experiments the row cites; within them, the trials of the
   predictions the row cites are emphasised. Both come from what the row cites (Requirement 9.1, 9.3).
2. **Prediction chart** (user). It shows all predictions. The condition class is shown in the bench's word,
   labelled "classified at registration"; Dr. Kiro's label beside it in Dr. Kiro's ink; a difference is shown as it
   is (Requirement 17).
3. **Frame layout** (user). The notebook keeps a small table per application (frames, rows, columns), with each
   application's spec named as its source. A sheet whose pixel size does not divide into the layout fails the
   build. `bench/` is not changed (Requirement 7).
4. **Highlight and cover miss chosen by a person** (user). Each session's choice is a committed file, labelled
   "chosen by a person" on the site. The builder proposes candidates; the user approves. A session without its file
   fails the build (Requirements 12, 13).
5. **Verdicts and status words kept apart** (user delegated the rule to the builder). The rule is Requirement 15:
   a verdict is always "verdict on H<n>:" in Dr. Kiro's ink inside an experiment entry or a replay step; a status
   word appears only in a table row or a reference to a row, in the bench's stamp style.
6. **Run and not run** (user). The bench's definition: same parameter-name set; `outside`, `new-combination`,
   `inside`. Display option A: one band per knob, with the declared range, a tick per tried value, the row's cited
   trials emphasised, and the parts outside the tried range hatched as "no trial"; missing combinations shown
   through each cited prediction's class word (Requirement 9.3-9.6).
7. **body-lab parameters** (user). Grouped by the set of parameter names Dr. Kiro declared, never merged by name
   alone; names in Dr. Kiro's ink, linked to the experiment file; no declared range, so "not run" means only
   outside the tried range; small line plots of each channel's input over time against [-1, 1]
   (Requirement 9.2, 9.5, 9.7, 9.8).
8. **Stopped sessions** (user). In the same list as ended ones, same size, not on the cover; the seal's end and
   reason as written, budget used and what the record contains; commentary never names the cause in words that
   would fail the blind scan; trials with equal computed inputs across records shown beside each other, derived
   mechanically (Requirement 14).
9. **Replay steps** (user). One step per after-verdict snapshot, plus the `end` snapshot. Strike-through only where
   a snapshot's table holds a `rejected` row, verified with a fixture that is never shown (Requirement 16).
10. **Cover, option A** (user). One large pinned instant photo playing the missed trial's sheet; prediction in Dr.
    Kiro's ink, measured value in pencil, "miss" in red; the citing row and its replacement beside it; one card per
    lab below with a small moving picture; a session with no miss says so (Requirement 13).
11. **Session page, option B** (user). The table first, as a notebook page, with a sticky note pointing to a missed
    prediction and moving pictures pinned in the margin; body-1 shows "no table" with its missed predictions
    (Requirement 10).
12. **Built from the spec** (user). Its requirements are written now; its implementation comes in later tasks;
    until runs exist the section says there are none yet (Requirement 19).
13. **Only sealed records** (user). The notebook reads `sessions/`, not `discovered/` (Requirement 1.2).
14. **Choice file content, and stopped sessions** (builder). One TOML file per record, with contrast, best and
    missed prediction, each possibly "none" with the user's reason. A session without trials (wt-003) says "none"
    for all three; the file must still exist. A separate cover file names the cover's prediction and each lab
    card's trial, because the cover spans sessions (Requirements 12, 13.5).
15. **Gap in the layout table** (builder). The table also holds the gap between cells, because the wind-tunnel sheet
    has a 4-pixel gap (1208 by 404 = 3 x 400 + 2 x 4 by 2 x 200 + 4); without it the cells cannot be cut. The
    body-lab entry has gap 0 (1600 by 360 = 5 x 320 by 2 x 180) (Requirement 7.1).
16. **The end table is checked again at build time** (builder). The build runs the bench's own table check on the
    `end` snapshot. A disagreement is a corrupt record or a bench defect, and fails the build (Requirement 2.4).
17. **Status words in the middle of a replay** (builder). The bench checks the table only at the end, so the words
    at earlier steps are shown as Dr. Kiro wrote them, labelled "not yet checked by the bench". The notebook does
    not compute a status (Requirement 16.3).
18. **A table the reader does not accept at a middle step** (builder). Shown as written with a labelled sentence, no
    guessed rows (Requirement 16.6). This shows the record as it is and fills in nothing. Confirmed by the user.
    Extended by Decision 45.
19. **Ticks across the session, emphasis from the row** (builder). A run band's ticks are all trials of the
    parameter group in the session, so "no trial" means no trial in the session; the cited and prediction trials
    are drawn stronger (Requirement 9.3). This combines the brief ("conditions that no trial in the session ran")
    with item 1.
20. **Dr. Kiro's text not rendered as Markdown** (builder). Shown as written and escaped, with line breaks; table
    cells come from the bench's reader. Rendering Markdown would change what is shown (Requirement 4.3).
21. **Rounding** (builder). 4 significant digits in lists and charts; the full recorded value when a trial is opened
    (Requirement 5.3).
22. **Equal trials across records** (builder). Compared by the recorded trial key and exact equality of every
    recorded measurement; shown wherever such a pair exists, not only for wt-002 and wt-004 (Requirement 14.5).
23. **Phone and motion** (builder). 360 CSS pixels as the narrow width; reduced motion respected; pictures and
    replay may need JavaScript, all text does not (Requirement 3.4-3.6).
24. **Inks without colour, and contrast** (builder). Each ink differs in typeface or style as well as colour; text
    contrast at least 4.5:1, and Halloween decoration never lowers it (Requirements 4.5, 4.6, 6.5).
25. **Commentary word list** (builder). The motion-wording rule is tested on the notebook's own text against a
    reviewed list in `notebook/` (Requirement 5.5). Dr. Kiro's text is shown as written.
26. **Explicit folders, no overwrite** (builder). Every input and output folder is an argument; an existing,
    non-empty output folder is refused (Requirement 1.3, 1.4).
27. **Series measurements** (builder). body-lab's recorded track is shown as a small path in pencil; it is a
    measurement the bench recorded (Requirement 10.10).
28. **Cover length** (builder). At most 240 words of commentary on the cover (Requirement 13.6; it was 60, see
    Decision 51).
29. **Build-from-spec pass or fail** (builder). The notebook uses the check `build-from-spec` provides and fails the
    build on disagreement; it never judges a run (Requirement 19.6).
30. **Rescanning the written site** (builder). The build writes what the blind scan needs to scan the site again at
    each author's level, for `publish` (Requirement 20.3). How is settled in item 38.
31. **Review pass** (builder). The criteria were sharpened for testability (checks run before writing, the
    fake-trial rule and test fixtures, ink of bench text, unchecked tables in stopped sessions and middle replay
    steps, "none" choices, scales and ordering). No user decision changed.
32. **Replacement display** (user). Rows stay in table order. Beside each struck-through `rejected` row is a tab
    "replaced by <id>" that opens to show the replacing row's rule text in small type; the replacing row shows
    reverse links "replaces <id>, <id>"; no row is drawn in full twice, checked by a property test. This is the
    user's reading of the brief's "the row that replaced it stands beside it", and it supersedes a literal reading
    of it. body-2 needs it: R11 and R13 each replace several rows, and R1 comes before R2, which it replaces
    (Requirement 8.3, 8.4, 8.10-8.12).
33. **Refused ends are shown** (user). A sticky note in the bench's stamp style, "the bench refused to end this
    session N times", is attached to the row whose id equals exactly the text of a quote in the refusal message
    (body-2 R13). Each message is shown as recorded, each part in its recorded author's ink, with the note that the
    sealed row's status is the one in the table and the commentary "the record holds no copy of the table that was
    refused". The notebook never infers what changed between refusals and reads no other meaning from the message.
    In the replay, refusals are events of the step whose entries they precede (body-2: between the E11 verdict step
    and the `end` step). The refusal counts of Requirement 18.4 stay (Requirements 10.11, 10.12, 16.12).
34. **Quotes composed by the bench** (user). The quote "H11.P3: hit/not-comparable" is shown as recorded, in Dr.
    Kiro's ink, because its recorded author is `dr-kiro`. A commentary note explains that quotes in a refusal
    message are recorded with Dr. Kiro as author, and that the bench composes some of them, such as the table
    check's summary of cited outcomes, from Dr. Kiro's ids. The bench is not changed. Whether the design can point
    the note at the composed quotes mechanically, without parsing the message, is left to the design; otherwise
    the note covers every quote part of a refusal message (Requirement 10.13).
35. **Equal trial keys** (user). A compact list of pairs with session and trial ids, parameters as written, and
    whether the measurements are exactly equal; opening an entry shows the two moving pictures side by side
    (Requirement 14.5).
36. **Cover choice** (user). The cover shows body-2 H4.P1 (trial T12): predicted forward, the body went backward
    and turned. The cited row is R4, replaced by R5. Lab cards: body-lab body-2 T31; wind-tunnel wt-004 T1. Because
    the backward drift is faint in the picture, the cover also shows the recorded track in pencil beside the photo;
    this part was decided by the builder under the user's delegation (Requirement 13.7). The cover file itself is
    written in tasks.
37. **Choice files, approved content** (user). The files are written in tasks with this content:
    - body-lab/body-1: contrast T22 and T30; best T39; missed H8.P1.
    - body-lab/body-2: contrast T25 and T30; best T36; missed H8.P6.
    - wind-tunnel/wt-002: contrast T1 and T3; best "none", reason "no trial without shedding"; missed "none",
      reason "no prediction missed".
    - wind-tunnel/wt-003: contrast, best and missed all "none", reason "no trial was run".
    - wind-tunnel/wt-004: contrast T1 and T8; best T12; missed H5.P3.
38. **Rescanning the written site, resolved** (user). The bench now reads a sidecar `<file>.authors.json` that lists
    character ranges by author (`bench/src/bench/scan/levels.py`). The build writes one sidecar per written text
    file, so the site can be rescanned at each author's level without changing `bench/`. This resolves the former
    Open question 2 (one author level per scanned file), which is removed; the former Open question 3 is now Open
    question 2 (Requirement 20.3).
39. **Strike-through tests** (user). body-2's table exists only at the `end` step, so the strike-through at a
    middle replay step stays tested with the fixture (16.11). The end table's strike-through, replacement tabs and
    reverse links, and R13's refused-end note are tested on the real body-2 record (Requirement 22.5).
40. **Order of delivery** (user), for the design and the tasks. First milestone: the cover and the discovered spec
    table, rendered from the real records; then stop and show the screens to the user. Second: the experiment
    list and moving pictures, stopped sessions, "How the lab works", and run bands. Last: the prediction chart, the
    replay, the equal-trial list, and the input time-series lines. The implementation of "Built from the spec"
    (Requirement 19.2-19.7) comes after these.
41. **README limits line** (user). The fact that the bench records its cited-outcome summary as a quote with
    author `dr-kiro` (item 34) is recorded for the README step, as a line in its limits; the orchestrator notes it
    in `docs/status.md`.
42. **Adapters installed for the scan** (user). The bench's blind scan reads each application's allow list by
    importing its declaration (`bench/src/bench/scan/terms.py`, `load_app`), which imports the adapter packages
    (and through them the MuJoCo Python package and `wind-tunnel-model`). The notebook therefore depends on the
    bench and on both adapter packages by path; it installs them but runs no simulator, no solver and no Docker
    (option A of the design's former Open question 1). Not chosen: B, running the scan in each application's own
    environment as a separate process (the build starts no process, and the site would have to be on disk before
    the scan); C, changing the bench so the scan can take the declaration from elsewhere (a `bench/` change, and the
    allow list must come from the application's own declaration, `rules.md` 1) (Requirement 1.5).
43. **No link to the root `.kiro/`** (user). "How the lab works" has no link to the repository's root `.kiro/`; the
    notebook names and links no file or folder outside a lab. The question is decided again when the README is
    written (README step, `docs/brief.md` section 5 item 8). This resolves the former Open question 2, which is
    removed (Requirement 18.5).
44. **Rescanning the written site for `publish`** (user). How `publish` scans the written site again (the bench's
    folder scan reads every file as text, so the site's PNG files would fail it) is decided in the `publish` spec
    when it is written. The notebook still writes one sidecar per text file (Requirement 20.3), and its own scan
    before writing stays (Requirement 20.1, 20.2).

45. **A table the bench reader does not accept** (user, 2026-11-17). `parse_table` raises `TableError` for a table
    with no rows ("the discovered spec table has no rules"), so every snapshot before `end` in the real records is
    one the reader does not accept, and a row-less table cannot be told from other unaccepted tables without
    parsing the message or a second reader (Requirement 2.6). Decided: a table the reader does not accept, with no
    rows or for any other reason, is shown with its `## Discovered spec` section as written in Dr. Kiro's ink, the
    reader's message in pencil, and the commentary "the bench's table reader did not accept this table"; the build
    does not parse the message. "No table" is used only for an ended session without an `end` snapshot (body-1),
    which still lists every missed prediction. wt-002 (stopped, last snapshot without rows) shows its last
    snapshot's section with the message, labelled "not checked by the bench". The edge cases of N12 are unchanged:
    a replaced-by cell naming the row itself gives "names this row itself", no match (including empty) gives
    "names no row of this table", two or more give "names more than one row" (Requirements 10.9, 10.14, 14.6, 16.6;
    design N27; extends Decision 18).

46. **Flat site and wording that avoids scan terms** (user, 2026-11-17). The builder's scan of its own text (task
    8.1) flagged four things: `../` in relative links (read as a path outside the lab), the derived terms `linear`,
    `thickness` and `spacing` in the stylesheet, the `xmlns` URL in the decoration file (which the `http:` check
    of the site rejects), and picture attribute and script names that are scan terms. Decided: every page is at the
    site root, addresses are `index.html`, `how.html`, `built.html`, `legend.html`, `<app>.html`,
    `<app>-<session>.html` and `<app>-<session>-replay-<n>.html`, pictures are `p/<sha256>.png`, assets are
    `a/notebook.css` and `a/notebook.js`, and no link contains `..`; the build checks that application and session
    ids are lower case letters, digits and single hyphens and that no two pages have the same address; the
    stylesheet is reworded without the flagged words, never through the stop list; the Halloween decoration is
    inline SVG without `xmlns`; the picture layout attributes are `data-tile-width` and `data-tile-height`; the
    `http:` check stays strict. A scan finding in builder text is always fixed by rewording (design N28)
    (Requirements 3.2, 6.5, 11.1, 20.1, 20.2).

47. **Dr. Kiro's fixed words** (user, 2026-11-17). Task 12.1 found that the verdict word and Dr. Kiro's label of a
    prediction are recorded in the bench's `verdict` and `register` entries as plain strings with no author (the
    bench's scan treats them as bench strings), while the same values appear with author `dr-kiro` in the `given`
    of a refusal. Requirements 15.1 and 17.4 ask for Dr. Kiro's ink, and 4.2 says ink follows the recorded author.
    Decided: these words keep Dr. Kiro's ink, as an exception written into Requirement 4.2, because Dr. Kiro chose
    them and the bench only checked them against its fixed set; and the build scans each of them at the builder
    level as well as at Dr. Kiro's level, so the exception cannot let a term through. The bench and the records
    are not changed (Requirements 4.2, 15.1, 17.4, 20.1; design N29).

48. **This version stops after the prediction chart; the replay is on hold** (user, 2026-11-17). The replay of a
    sealed record (Requirement 16 and its tests) is on hold until a real sealed record shows a table at each step,
    that is, until the Dr. Kiro template changes so that a new session runs with middle-step tables (the real records
    have an empty table up to the last step, so the replay would show empty tables for most steps). The replay code
    stays in the repository and is not built now. Not in this version: the equal-trial list (Requirement 14.5); the
    input lines of body-lab (Requirement 9.8) and the recorded tracks in experiment entries (Requirement 10.10).
    Tasks 19, 20 and 21 (the rest of milestone 3 after the prediction chart) are stopped. The prediction chart
    (Requirement 17) and Requirement 5.4 stay in this version, and so does the track on the cover (Requirement
    13.7). The requirements, the design sections and Property 9 and the equal-trial property stay in the documents,
    marked "not in this version" or "on hold", and the build does not implement them. This changes the order of
    delivery of Decision 40 (Requirements 9.8, 10.1, 10.10, 14.5, 14.6, 16, 22.3, 22.5; design Delivery order).
49. **Rejected-row tab open by default** (user, 2026-11-17). The "replaced by" tab of a `rejected` row is open when
    the table is shown, so that the replacing rule is readable without a click. Its content and link are as in
    Decision 32 (Requirement 8.13; design N31).
50. **Enlarged picture of the body, body-lab only** (user, 2026-11-17). Beside each body-lab trial's moving picture,
    the site shows an enlarged picture of the moving body, so that the body in its cell is readable. Wind-tunnel
    pictures get none, because the flow moves through the whole sheet and no region of it is the moving body. Its region is the box of the pixels
    that change between frames, plus a 4 px margin, clipped to its cell, scaled by the smallest whole-number factor
    that makes it at least as large as the frame (the whole cell if nothing moves); the track is not used, because
    the records have no mapping from track coordinates to picture pixels. It is derived at build time from the
    record's own picture sheet; the recorded PNG file is not changed. Its alt text says that it is a
    magnified view of the picture beside it, and uses no word of the commentary word list (Requirement 7.9; design
    N32).
51. **Notebook polish pass** (user, 2026-11-19). The cover shows the prediction and the miss in the first screen: a
    top row with the claim card, the sticky note and the magnified picture, then the row with the moving picture and
    the track (Requirement 13.1, 13.12). The sticky note says in one sentence what happened, from recorded numbers
    only (13.8). The row of the outcome is dropped, because the stamp says it (13.9). The details sit inside the
    card of rules (13.10). The cover opens on the tab of the lab of the missed prediction, and the tabs keep the
    order of the cover file (13.4). The cover's limit is 240 words (13.6). On a phone the track box is cropped to
    the drawing (13.7) and the picture controls are 44 px targets (7.8). The discovered spec table is shown as
    cards (8.14). A rejected row or card has a rewrite red (`--rewrite-red` on `--rewrite-bg`), which is not the
    miss red (6.4): the miss red stays for misses. The stylesheet bundles the typefaces Lora, IBM Plex Mono and
    Caveat as files of the site, with their licence; this fetches nothing from another host (3.2). The word
    "spacing", a setting of the wind tunnel like "ahead", is on the stop list, and small headings are letter-spaced.
    The steering file `notebook-visual.md` holds the details.
52. **Night lab** (user, 2026-11-19). The notebook has a dark palette, the night lab: the same paper notebook on a
    dark desk under a lamp, not an inversion. It follows `prefers-color-scheme: dark` in CSS only; there is no switch
    and no script, and without a stated preference the page is the day paper (6.2). Only colours change: every
    custom property of the night lab overrides one of the day, and the layout, the wording and the motion
    (including `prefers-reduced-motion`) are the same. The recorded pictures are never filtered or inverted; the
    photo frame is a dark neutral with a thin edge. The SVG tracks follow the ink in `currentColor`. The miss red,
    the rewrite red and the stamps are lightened and keep their roles (6.4, Decision 51). Every pair of the
    contrast list reaches 4.5:1 with the night values too (4.6). The steering file `notebook-visual.md` holds the
    values (section "Night lab").

## Open questions

None.
