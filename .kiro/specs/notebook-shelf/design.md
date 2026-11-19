# Design: notebook-shelf

This design covers requirements 1 to 7 of `notebook-shelf`. It changes the page layer of `lab-notebook` and keeps everything below it.

Which Kiro: the builder makes and runs all of it; a visitor reads it.

## Overview

The build keeps its four phases. Phase 1 reads the records, the choice files (`choices.py`), the cover file and, when `--display` is given, the display manifest (`display.py`). Phase 3 renders three page kinds: the shelf pages (`pages/shelf.py` with `pages/book.py`), the ink legend (`pages/legend.py`) and "how the lab works" (`pages/how.py`). Removed: the cover, lab, session, replay and band pages with `chart.py`, `bands.py`, `plots.py`.

## Pages

- One page per session, `<application>-<session>.html`, and `index.html`, which is the page of the session `cover.toml` names for its first lab. The two are the same bytes.
- Every page holds the masthead, the lab tabs (links to the session each lab opens), the cards of the open lab (links), and the opened notebook (`article.book`).
- Ids on a page: `row-<id>` on a rule card, `H<n>` on a hypothesis row, `E<n>` on an experiment, `E<n>-T<n>` on a trial card, `H<n>.P<n>` on a prediction. A link to an id inside a closed note opens it (`notebook.js`).

## Choice files (requirement 2.3)

`choices/<application>/<session>.toml`: `title`, `subtitle`, `summary`, `line`, `model`, `date` (YYYY-MM-DD), `color` (one of the six band colours), `[progress]` (`measurement`, `better`, optional `require` with `equals`), and `[[polaroid]]` twice (`heading`, `trial`, `words`, optional `star`). A session with one trial needs one photo, with none needs none and no `[progress]`. `choices/cover.toml`: one `[[lab]]` per application with `application`, `case`, `about`, `open`, `unit`. Every text has a length limit. The `model` and `date` are not in the record; a person writes them. A `<fill in>` model is shown as written.

## The best so far (requirement 3.3)

`progress.series` walks the trials in order. A trial counts when its measurement is a number and, with `require`, the second measurement equals `equals`. The best moves when a counting value is better than the best so far; the first counting trial starts the line and is not a "new best". A step is labelled when its change is at least 4% of the range between the lowest and highest best. The chart is an inline SVG whose texts are pencil segments and handwritten labels; nothing is a number the record does not hold.

## Predictions hit

Hits out of all outcomes the bench recorded (hit, miss, not-checkable). A prediction never run has no outcome and is not counted.

## Tables and plans

`progress.table_of` takes the accepted `end` snapshot's table (checked), else the last snapshot's table when it has rows (not checked), else none. The plan lines are the `- [x]`/`- [ ]` lines of that snapshot's `tasks.md`, with the author of the record. Status counts count only the bench's four words.

## Night and day

The default colours are the night lab. `html[data-mode="day"]` replaces the custom properties. The script sets the attribute and stores one value, `notebook-mode`, in `localStorage`; when storage is blocked the choice lasts for the page. Sticky notes, photos and the open notes keep their paper colours in both modes and set their own ink colours.

## Retaken display pictures (requirement 6)

The folder holds `manifest.toml` and the PNG sheets. Each `[[retake]]` has `application`, `session`, `trial`, `file`, `sha256`, `source_picture` and `measured`. The build refuses the entry unless: the file's SHA-256 is `sha256`; `source_picture` is the trial's recorded picture hash; the sheet divides into the lab's columns and rows with gap 0; `measured` is not empty and every value equals the recorded value of that name at 4 significant digits. The picture is copied as `p/<sha256>.png` and shown in place of the magnified picture.

### Proposal: how to take the pictures again (on the Mac, outside this change)

1. A builder script `body-lab/retake.py` (not in the notebook, and not blind-scanned because it is never in a lab) reads one sealed session read-only.
2. For each chosen trial it takes the experiment file's source blob from the record, the trial's parameters and seed, and the sampled input series (`trial.inputs`), and runs that one trial again through the body-lab adapter. The same seed and inputs give the same run (`rules.md` 3).
3. The measured values of the rerun are compared with the recorded ones: x, y and heading at 4 significant digits. If any differs the script stops and says which (`rules.md` 2). Nothing is retried or adjusted.
4. The rerun draws the same ten frames, but from a camera that follows a box around the body (the box is the body's recorded track from start to end, plus a margin), at a larger size, and writes one sheet in the lab's layout with gap 0.
5. The script writes the sheet to `notebook/display/<session>-<trial>.png`, computes its SHA-256, and appends the manifest entry with the recorded picture's hash and the measured values.
6. `notebook-build ... --display notebook/display` shows the new pictures. The folder is committed; the sealed records are untouched. Which trials to retake: the two photos of each choice file first, then every trial of the hypothesis rows if wanted.

Open: whether the adapter lets a caller set the camera and size. If it does not, a small change to the adapter is a spec change of `body-lab` and needs the user.

## Decisions

1. The hypothesis stamp on a row is the status of the table rows that cite its experiment (the four bench words). Dr. Kiro's verdict word (supported, partly, rejected) is a different word and is shown in Dr. Kiro's ink inside the open note.
2. The first counting trial is not a "new best" on the best so far or on a hypothesis row, because nothing came before it.
3. The model name is not in the record. It is a required key of the choice file, written by a person.
4. The date is the day a person says the session was sealed. The record holds no time. The first set of dates is the day each record was added to git.
