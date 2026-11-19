# Requirements Document

Spec: `notebook-shelf`.

## Introduction

`notebook-shelf` replaces the pages of `lab-notebook` that show a session (the cover, the lab pages and the session page) with a shelf of notebooks. Each session is one notebook, and its first screen tells one story. The rest of `lab-notebook` stays: the records and their readers, the ink rule, the blind scan, the flat site, the picture sheets and the moving photos, the word list, the ink legend page and the "how the lab works" page.

Which Kiro: every page is built by the **builder** and read by a **visitor**. Dr. Kiro and the reader never see the notebook. Text written by a person (the title, the summary, the words on the photos) is the builder's own text: orange pen, scanned at the builder level.

Replaced from `lab-notebook`: requirements 8 to 14 and 17 as far as they describe the old layout; the replay (16) stays out of the build (Decision 48 of `lab-notebook`).

Rules that apply unchanged: `rules.md` 1 (blind), 2 (fail fast), 4 (honest), 5 (language). Status words are the bench's four words. No number is shown that the record or a choice file does not hold. The site makes no request outside itself.

## Requirements

### Requirement 1: The first page

1. The site opens on `index.html`, the page of the session that `cover.toml` names for its first lab.
2. A page starts with the small heading, a large handwritten title, two or three lines about the open lab, and one line saying what each ink is: green ink is Dr. Kiro's own words, orange pen is our notes, pencil is a measured value.
3. The page is in the night lab by default (a dark, purple-black graph paper) with a moon, a cobweb, a hanging spider and bats at the top right and a pumpkin at the bottom left. A button at the top right switches to the day lab and back. The choice is kept for the next page when the browser allows it. Without the script the page stays in the night lab.
4. Under the heading come one round tab per lab, and under the tabs the open lab's sessions as cover cards side by side. A card shows the notebook's title, one line, in small type the best result and the predictions hit out of all checked, and a coloured band on its left. The open card has a green frame. A tab and a card are links to a session page.

### Requirement 2: The opened notebook

1. A binder's holes are on its left and a cobweb in its top right corner.
2. The notebook starts with a large handwritten line that says what was found, then a summary of three or four lines.
3. The title, its second half and the summary are written by a person in the choice file of the session (`<application>/<session>.toml`). The page only reads them. A choice file that is missing, has an unknown key, or names a trial or measurement the record does not hold fails the build, naming the file and the key.
4. Under the summary come small chips: the model name and the date (both from the choice file), the number of trials or runs, the number of rows of each of the four status words with an icon, and the predictions hit out of all checked. A session whose record holds no table says so instead of the four counts. A stopped session shows the bench's recorded reason.

### Requirement 3: The highlight and progress

1. Two large taped photos stand on the left. Each has a small heading in capitals chosen by a person with the hypothesis id from the record, a handwritten line by a person, and in pencil the trial id and every measured value. The better one has a star. The pictures of the two play together; one play button and one slider under them move both, and under each picture a line says how far the body had come at that moment ("t = 3.0 s forward 38 cm"), from the recorded track. Which two trials is the choice of a person. The photos, the three notes and the chart fit one screen of a wide display.
2. Three sticky notes of different colours, slightly tilted, stand on the right: the best result, the predictions hit out of all checked, and the number of rules rejected (or, when the record holds no table, the hypotheses Dr. Kiro rejected, said so). Every number comes from the record, and numbers on the page are short (`+3.9 cm`, `0.75 m`, `cd 0.993`, never an exponent); the recorded values are in the opened notes.
3. Under them, in a small frame, a line shows the best so far after each trial. Which measurement counts, whether higher or lower is better, and an optional second measurement that must equal a value for a trial to count are chosen by a person in the choice file. Only the largest steps up (at least 10% of the whole climb, at most four) are named, each with its hypothesis and the change ("H10: +9.2 cm"), and no two names overlap. No baseline is drawn: the record holds none.
4. A session without a trial shows a sentence in place of 1 to 3 and has no photo and no chart.

### Requirement 4: The discovered spec, the plan, every experiment

1. The titles are in a cream handwriting and the text of a person is ordinary text with a small orange mark "our notes" beside it.
2. The discovered spec is a set of compact cards, one per table row, each with its id, rule, scope and status stamp, labelled checked or not checked by the bench. A `rejected` row has its rule struck through and the row it was rewritten as beside it, linked. Scope, experiments and predictions are in a closed note of the card.
3. Dr. Kiro's plan is the checklist of its last `tasks.md` in the record: circled numbers joined by arrows, each with Dr. Kiro's own words cut to one line that opens to the whole text. It is shown only when the record holds such a list.
4. "All N experiments and hypotheses" has one card per hypothesis, two cards side by side: a moving photo on the left (the trial that set a new best, else its first trial), on the right a circled hypothesis id, Dr. Kiro's title, what it expected, the outcome of each prediction in pencil, the stamps of the table rows that cite it, and "new best" with a star when one of its trials set a new best (not the first counting trial). Pressing the row opens a note with Dr. Kiro's words as written, the predictions, the verdict, and every trial of the hypothesis. A link to an experiment or prediction opens the note that holds it.

### Requirement 5: The reader

1. When the records hold reader runs of a session, that session's notebook shows the request in words and three results side by side: the reader with the spec only, with the raw record only, and with nothing. Each shows passes out of runs, and every run (a failed run too) with its result.

### Requirement 6: Retaken display pictures

1. The recorded picture of a body-lab trial is small. A display folder given to the build with `--display` can hold larger pictures of chosen trials, taken again outside the sealed record. A manifest names each one and the build checks it as `design.md` says. Without `--display`, every trial shows its recorded picture; there is no other fallback.
2. A retaken picture replaces the magnified picture of its trial everywhere that trial is shown. The sealed records are never changed.
3. `notebook-retake` makes them: it runs each trial of the chosen body-lab sessions again from its recorded inputs, stops at the first difference from the recorded measurements, and only then draws the picture from a camera above that follows the body, one cell of at least 300 px every 0.2 s. It changes neither the adapter nor what the bench returns to Dr. Kiro.
4. Every picture of a notebook is a large picture round the body. The recorded whole picture is shown only when its button is pressed. A wind-tunnel picture shows a crop round the body and its wake, cut from the recorded cell; it is not run again.

### Requirement 7: Unchanged

1. The blind scan covers every page, the stylesheet, the script and every text in a choice file or the cover file. Class names, comments and attribute text are scanned too.
2. Every page, picture and font is a file of the site. There is no `<div>`, no external request and no inline script.
3. A test that no longer fits the new layout may change. No test is weakened to pass.
