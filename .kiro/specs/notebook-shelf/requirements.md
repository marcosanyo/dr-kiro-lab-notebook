# Requirements Document

Spec: `notebook-shelf`.

## Introduction

`notebook-shelf` replaces the pages of `lab-notebook` that show a session (the cover, the lab pages and the session page) with a shelf of notebooks. Each session is one notebook, and its first screen tells one story. The rest of `lab-notebook` stays: the records and their readers, the ink rule, the blind scan, the flat site, the picture sheets and the moving photos, the word list, the ink legend page and the "how the lab works" page.

Which Kiro: every page is built by the **builder** and read by a **visitor**. Dr. Kiro and the reader never see the notebook. Text written by a person (the title, the summary, the words on the photos) is the builder's own text: orange pen, scanned at the builder level.

Replaced from `lab-notebook`: requirements 8 to 14 and 17 as far as they describe the old layout; the replay (16) stays out of the build (Decision 48 of `lab-notebook`).

Rules that apply unchanged: `rules.md` 1 (blind), 2 (fail fast), 4 (honest), 5 (language). Status words are the bench's four words. No number is shown that the record or a choice file does not hold. The site makes no request outside itself.

## Requirements

### Requirement 1: Two applications on one skeleton

1. The site root is a short front page. Under the title it opens with one English line that states the work: "An MCP bench makes a blind Kiro agent register predictions first, keeps its wrong rules struck through, and a second Kiro builds from that spec alone." It then says that two applications stand on one skeleton, the bench and the notebook, and shows two doors side by side: the wind tunnel (CASE 1) opening by day and the stitched body (CASE 2) opening at night. Each door is a link to the application's folder.
1A. The front page has no palette of its own. Its paper and inks are the notebook's: the night candle paper, which is the page's default. Each door takes the palette of its lab: the day paper for the wind tunnel, the night paper for the stitched body. The site is written in English for its readers; the front page carries no Japanese text.
2. Each application is a folder of the site, `/wind-tunnel/` and `/body-lab/`, with its own pages, pictures, stylesheet and script. Its `index.html` is the notebook of the session its settings name. A link from an application to the front page or to another application is `/` or `/<application>/`; every other link is relative and has no `..`.
3. The page maker is one program. What belongs to an application is in its own folder, `<application>/notebook/`: `app.toml` (its place in the order, the text of its tab and door, the description, the session it opens, the word for one budgeted step, the theme it opens in, the pen of our notes and the decoration), the choice files, and the folder of retaken pictures.
4. The wind tunnel opens by day: bright graph paper, a blue pen, a plain research notebook, and no decoration (no spider, bat, cobweb, moon or pumpkin, and no drawing at all in its pages). The stitched body opens at night: near-black paper lit from the middle as by a lamp, a large moon, a cobweb, a hanging spider and bats. Neither has a pumpkin. Each application has one theme and no switch: the wind tunnel is always by day and the stitched body always at night. The night of the stitched body is as close to black as the text allows.
5. A page starts with the small heading, a large handwritten title, two or three lines about the application, and one line saying what each ink is: green ink is Dr. Kiro's own words, the pen of our notes is blue or orange as the application says, pencil is a measured value.
6. There are no tabs to switch applications. At the top of a page are two small links in English: "All labs", which goes to the front page, and "Go to" followed by the title of the other application's door, which goes to that application. Under the heading the application's sessions that ended are cover cards side by side. A card shows the notebook's title, one line, in small type the best result and how many predictions came true, and a coloured band on its left. The open card has a green frame. Sessions that stopped early are not removed: they are small cards in their own row below, with a line saying they stopped early.

### Requirement 2: The opened notebook

1. A binder's holes are on its left and a cobweb in its top right corner.
2. The notebook starts with a large handwritten line that says what was found, then a summary of three or four lines.
3. The title, its second half and the summary are written by a person in the choice file of the session (`<application>/<session>.toml`). The page only reads them. A choice file that is missing, has an unknown key, or names a trial or measurement the record does not hold fails the build, naming the file and the key.
4. Under the summary come small chips: the model name and the date (both from the choice file), the body the session ran on when its record names one (from the record's start entry, which the choice file's `body`, if written, must match), the number of trials or runs, the number of rows of each of the four status words with an icon, and the predictions hit out of all checked. A session whose record holds no table says so instead of the four counts. A stopped session shows the bench's recorded reason.
5. The first page of an application, `index.html`, is the notebook of the session its `app.toml` names in `open`: `wt-004` for the wind tunnel and `body-3` for the stitched body.

### Requirement 2A: What the notebook means

1. Under the summary, three steps joined by arrows say what happened in this session, with every number counted from the record, the table and the reader's runs, and the words plain English: how many predictions Dr. Kiro wrote, each before its experiment ran; how many missed and how many rules were struck out and rewritten; and what a next Kiro gets from the spec.
2. The third step says what the reader did when the records hold the reader's runs of the session ("Another Kiro, given only this spec, did the task in 2 of 2 tries. With nothing, 0 of 2."). Otherwise it says which rows of the spec can be trusted and which are only partly tested or observed, and that no second Kiro has been run on the spec; it never claims a reader that was not run. A record with no final spec says that there is nothing yet for a next Kiro to read.
3. The reader's results come right after the highlight, before the discovered spec, because they are the end of the story.
4. Every section starts with one line saying what it is. Numbers such as H4 and R5 are small labels; the heading of a card is a sentence. Predictions read as "11 of 24 predictions, written before the run, came true".

### Requirement 3: The highlight and progress

1. Two large taped photos stand on the left. Each has a small heading in capitals chosen by a person with the hypothesis id from the record, a handwritten line by a person, and in pencil the trial id and every measured value. The better one has a star. The pictures of the two play together; one play button and one slider under them move both, and under each picture a line says how far the body had come at that moment ("t = 3.0 s forward 38 cm"), from the recorded track. Which two trials is the choice of a person. The photos, the three notes and the chart fit one screen of a wide display.
2. Three sticky notes of different colours, slightly tilted, stand on the right. A person chooses them in the choice file, three different ones of: the best result, the predictions hit out of all checked, the number of rules rejected (or, when the record holds no table, the hypotheses Dr. Kiro rejected, said so), the trials or runs used, and one missed prediction (its measured value and the range that was expected). Every number comes from the record, and numbers on the page are short (`+3.9 cm`, `0.75 m`, `cd 0.993`, never an exponent); the recorded values are in the opened notes.
3. Under them, in a small frame, one line, drawn so that it wavers a little like pencil on paper, with each named step joined to its name by a short stroke, shows the best so far after each trial; the vertical axis fits the line, so the line does not lie on the bottom of the frame, and the single trials are not drawn as dots. Which measurement counts, whether higher or lower is better, and an optional second measurement that must equal a value for a trial to count are chosen by a person in the choice file. Only the largest steps up (at least 10% of the whole climb, at most four) are named, each with its hypothesis and the change ("H10: +9.2 cm"), and no two names overlap. No baseline is drawn: the record holds none.
4. A session without a trial shows a sentence in place of 1 to 3 and has no photo and no chart.

### Requirement 4: The discovered spec, the plan, every experiment

1. The titles are in a cream handwriting and the text of a person is ordinary text with a small orange mark "our notes" beside it.
2. The discovered spec is a set of compact cards, one per table row, each with its id, rule, scope and status stamp, labelled checked or not checked by the bench. A `rejected` row has its rule struck through and the row it was rewritten as beside it, linked. Scope, experiments and predictions are in a closed note of the card.
3. Dr. Kiro's plan is the checklist of its last `tasks.md` in the record: circled numbers joined by arrows, each with Dr. Kiro's own words cut to one line that opens to the whole text. It is shown only when the record holds such a list.
4. "All N experiments and hypotheses" has one card per hypothesis, two cards side by side: a moving photo on the left (the trial that set a new best, else its first trial), on the right a circled hypothesis id, Dr. Kiro's title, what it expected, the outcome of each prediction in pencil, the stamps of the table rows that cite it, and "new best" with a star when one of its trials set a new best (not the first counting trial). Pressing the row opens a note with Dr. Kiro's words as written, the predictions, the verdict, and every trial of the hypothesis. A link to an experiment or prediction opens the note that holds it.
5. A rejected row's card has its left edge in the rejected stamp colour, its rule struck through, and the row it was rewritten as beside it. A stamp is never red. The miss red is used only for a missed prediction and its measured value, always with the word "missed".

### Requirement 5: The reader

1. When the records hold reader runs of a session, that session's notebook shows the request in words and three results side by side: the reader with the spec only, with the raw record only, and with nothing. Each shows passes out of runs, and every run (a failed run too) with its result.
2. Under the request in words, one line gives the budget of each run and the pass ranges that decide it, in this form: "each run: up to 12 trials · pass: x 0.3 to 0.5 m, heading -20 to 20 deg, y -0.2 to 0.2 m". The budget and the units come from each run's sealed start entry, the ranges from the request file. The line is not written when the numbers are missing: a run with another budget than the others of its request, a pass measurement its runs do not declare, or a missing budget fails the build and names the file. Nothing is filled in.
3. When the session's record names a body, the reader's runs given the spec of an earlier session on the same body are shown first, as a tile "Spec of an earlier session: <session>" with its passes out of runs, the runs, and the rules that run relied on as that session's table states them. Runs made on another body are not shown in this session's section.

### Requirement 6: Retaken display pictures

1. The recorded picture of a body-lab trial is small. A display folder given to the build with `--display` can hold larger pictures of chosen trials, taken again outside the sealed record. A manifest names each one and the build checks it as `design.md` says. Without `--display`, every trial shows its recorded picture; there is no other fallback.
2. A retaken picture replaces the magnified picture of its trial everywhere that trial is shown. The sealed records are never changed.
3. `notebook-retake` makes them: it runs each trial of the chosen body-lab sessions again from its recorded inputs, stops at the first difference from the recorded measurements, and only then draws the picture from a camera above that follows the body, one cell of at least 300 px every 0.2 s. It changes neither the adapter nor what the bench returns to Dr. Kiro.
4. Every picture of a notebook is a large picture round the body. The recorded whole picture is shown only when its button is pressed. A wind-tunnel picture shows a crop round the body and its wake, cut from the recorded cell; it is not run again.

### Requirement 7: Unchanged

1. The blind scan covers every page, the stylesheet, the script and every text in a choice file or the cover file. Class names, comments and attribute text are scanned too.
2. Every page, picture and font is a file of the site. There is no `<div>`, no external request and no inline script.
3. A test that no longer fits the new layout may change. No test is weakened to pass.
