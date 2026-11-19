# Design: notebook-shelf

This design covers requirements 1 to 7 of `notebook-shelf`. It changes the page layer of `lab-notebook` and keeps everything below it.

Which Kiro: the builder makes and runs all of it; a visitor reads it.

## Overview

The build keeps its four phases. Phase 1 reads the records, the choice files (`choices.py`), the cover file and, when `--display` is given, the display manifest (`display.py`). Phase 3 renders three page kinds: the shelf pages (`pages/shelf.py` with `pages/book.py`), the ink legend (`pages/legend.py`) and "how the lab works" (`pages/how.py`). Removed: the cover, lab, session, replay and band pages with `chart.py`, `bands.py`, `plots.py`.

## Pages

- The root holds the front page (`index.html`) and `a/`. Each application is a folder, `<application>/`, with one page per session (`<session>.html`), `index.html` (the same bytes as the page of the session `app.toml` names), `legend.html`, `how.html`, `p/` and `a/`. Every folder has its own copy of the stylesheet, the script and the typefaces, so a folder is a notebook on its own. The write step creates the folders; a path is the application, then `a/`, `p/` or a page.
- Every page of an application holds the two small links at the top (`/` and `/<other application>/`), the masthead, the cards of the application (links; sessions that stopped are small cards in a row of their own), and the opened notebook (`article.book`). A page of an application has a footer link to the front page, `/`.
- The `<html>` element of a page carries `data-app` (the application, or `front`), `data-mode` (the theme the page opens in) and `data-pen`. There is no theme switch and the script stores nothing: an application's theme is fixed by `app.toml`.
- The `/` and `/<application>/` links are the only links that are not relative. The blind scan reads them as it reads every link: they name no folder outside the site.
- Ids on a page: `row-<id>` on a rule card, `H<n>` on a hypothesis row, `E<n>` on an experiment, `E<n>-T<n>` on a trial card, `H<n>.P<n>` on a prediction. A link to an id inside a closed note opens it (`notebook.js`).

## Settings and choice files (requirement 2.3)

`<application>/notebook/app.toml`: `application`, `order`, `case`, `door`, `door_line`, `about`, `open`, `unit`, `theme` (`day` or `night`), `pen` (`blue` or `orange`), `decoration` (`none` or `halloween`) and, when the application has retaken pictures, `display` (a folder name). `<application>/notebook/choices/<session>.toml`: `title`, `subtitle`, `summary`, `line`, `model`, `date` (YYYY-MM-DD), `color` (one of the six band colours), `[progress]` (`measurement`, `better`, optional `require` with `equals`), `[[polaroid]]` twice (`heading`, `trial`, `words`, optional `star`) and `[[note]]` three times (`kind` is `best`, `hits`, `rejected`, `trials` or `miss`; a `miss` names its `prediction`, which must be a missed one with a value; the three differ). A session with one trial needs one photo, with none needs none and no `[progress]` and no note. Every text has a length limit. The `model` and `date` are not in the record; a person writes them. `notebook-build` takes one `--app <application>/notebook` per application; an application of the records without one, or one without records, fails the build.

## The best so far (requirement 3.3)

`progress.series` walks the trials in order. A trial counts when its measurement is a number and, with `require`, the second measurement equals `equals`. The best moves when a counting value is better than the best so far; the first counting trial starts the line and is not a "new best". A step is labelled when its change is at least 4% of the range between the lowest and highest best. The chart is an inline SVG whose texts are pencil segments and handwritten labels; nothing is a number the record does not hold.

## The opened note of a hypothesis

Dr. Kiro's hypothesis text is shown as it reads: its `###` line as a heading and its sentence as a paragraph; the fenced prediction block is left out and each prediction is one line from the record, "cd in [0.5, 1.25] when aspect = 3 → hit". The lines under a moving photo share one place of a fixed height, so the card does not change height as the words change. On a narrow screen the cards are one column.

## What happened here

`_story` builds three sentences from the record. Step 1: the number of predictions registered (all hypotheses), each written before its experiment ran. Step 2: the misses, and the rows with the status `rejected` when a table exists (a stopped session says how many of the checked predictions came true instead). Step 3: the reader's tally of the setups `spec` and `none` when runs of this session exist; else the counts of `validated` and of `partly` plus `observed` in the table with the sentence that no second Kiro has been run; else the sentence for a record with no spec. A record with no prediction gets one sentence.

## The chart line

The step line is a path through its exact corners with short pieces between them offset by a deterministic wobble (a hash of the record name and the piece number, at most 1.2 units), so every build draws the same line. The names of the largest steps are joined to their dots by a short curved stroke. A choice file may name a second measurement and a value (`mark`, `mark_equals`, `mark_words`); the first trial where it takes the value gets a dashed line and the words a person wrote (the wind tunnel: the first run without shedding). The vertical axis spans the line with a quarter of its range on each side.

## Predictions hit

Hits out of all outcomes the bench recorded (hit, miss, not-checkable). A prediction never run has no outcome and is not counted.

## Tables and plans

`progress.table_of` takes the accepted `end` snapshot's table (checked), else the last snapshot's table when it has rows (not checked), else none. The plan lines are the `- [x]`/`- [ ]` lines of that snapshot's `tasks.md`, with the author of the record. Status counts count only the bench's four words.

## Night and day

The default colours are the night lab. `html[data-mode="day"]` replaces the custom properties. The script sets the attribute and stores one value, `notebook-mode`, in `localStorage`; when storage is blocked the choice lasts for the page. Sticky notes, photos and the open notes keep their paper colours in both modes and set their own ink colours.

## Retaken display pictures (requirement 6)

The folder holds `manifest.toml` and the PNG sheets. Each `[[retake]]` has `application`, `session`, `trial`, `file`, `sha256`, `source_picture`, `columns`, `rows`, `interval`, `frame_seconds`, `track`, `track_step` and `measured`. The build refuses the entry unless: the file's SHA-256 is `sha256`; `source_picture` is the trial's recorded picture hash; the sheet divides into `columns` and `rows` with gap 0; `measured` is not empty and every value equals the recorded value of that name at 4 significant digits; and `track` is a recorded series in metres of `track_step * columns * rows + 1` samples. The picture is copied as `p/<sha256>.png` and shown in place of the magnified picture. The recorded whole sheet stays one press away ("whole picture").

### How the pictures are taken (`notebook-retake`, on the Mac)

`uv run notebook-retake --sessions sessions --out notebook/display --session body-1 --session body-2`

1. The sealed records are read, never written. The output folder must be new or empty.
2. For each trial the recorded commands (`trial.inputs`) are run again through the body-lab adapter's own simulator (`sim.run`; the simulation has no random part, and the trial's seed is recorded with it), and the adapter's own measurer computes x, y, heading and the three tracks. They are compared with the record exactly. The first difference stops the command and names the trial and the measurement. On 2026-11-19 all 79 trials of body-1 and body-2 matched.
3. During the same run, 25 pictures are drawn, one every 0.2 s of simulated time, 320 px square, by the renderer's free camera straight above the centre of mass of the body, so the floor shows 50 cm across with the checks moving behind the body. The adapter, its camera and the pictures the bench returns are not changed.
4. The 25 pictures are laid out 5 by 5 with no gap. The low 3 bits of each colour are dropped and each row is stored with the smallest PNG filter, so a sheet is about 0.3 MB (all 79: 20 MB). The sheet is a display picture, not a measurement.
5. The sheet's SHA-256, the recorded picture's hash, the layout and the measured values are written to `manifest.toml`.

The wind tunnel is not run again: a larger picture would need the sampling of the solver changed (`wind-tunnel/model`, a `wind-tunnel` spec change). Its pictures are the recorded ones with a crop (`zoom.py`): the script draws only the window round the body and its wake of every cell (found from the grey of the body in the first cell), and the whole picture is one press away.

## The top of a page

Numbers at the top of a page are short (`numbers.brief`): metres under 10 cm in centimetres (`+3.9 cm`), larger in metres (`0.75 m`), a value with no unit with three decimals (`0.993`), never in exponent form. The recorded values are in the opened notes. The two highlight photos are one group: one play button and one slider move both, and under each photo a line says "t = 3.0 s forward 38 cm" from the recorded track at that cell. The chart is a framed box, names at most four steps (the largest, at least 10% of the climb), and places each name where it does not overlap another. Titles are cream; the text of a person is ordinary text with a small orange mark "our notes". Each discovered spec card shows the id, the stamp, the rule and its rewrite; scope and evidence are in a closed note. Each step of the plan is one line that opens to the whole text. Each hypothesis is a card in a two-column grid that spans both columns when its note is open.

## Decisions

1. The hypothesis stamp on a row is the status of the table rows that cite its experiment (the four bench words). Dr. Kiro's verdict word (supported, partly, rejected) is a different word and is shown in Dr. Kiro's ink inside the open note.
2. The first counting trial is not a "new best" on the best so far or on a hypothesis row, because nothing came before it.
3. The model name is not in the record. It is a required key of the choice file, written by a person.
4. The date is the day a person says the session was sealed. The record holds no time. The first set of dates is the day each record was added to git.
