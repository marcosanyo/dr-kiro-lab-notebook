---
inclusion: fileMatch
fileMatchPattern: "notebook/**"
---

# Notebook visual system

Source: `lab-notebook` design, "Visual system" (Requirement 6.1). Every page of the notebook follows this file. When
the user describes a difference from the reference, this file (or `lab-notebook` Requirement 6) is changed first and
the pages after (Requirement 6.6). The stylesheet `notebook/src/notebook/assets/notebook.css` holds every colour
below as a CSS custom property on `:root`; pages use the properties and the classes, never a colour literal.

Which Kiro: the builder writes the pages; visitors read them. Dr. Kiro and the reader never see the notebook.

The site looks like a scientist's paper notebook, not a dashboard. It has one theme and no theme switch
(Requirement 6.2). The stylesheet bundles three typefaces as files of the site and names them first in each font
stack: Lora (400 and 600, the serif), IBM Plex Mono (400 and 600, the monospace) and Caveat (700, the script of
the title, the tagline and the tab titles). They are `woff2` files in `notebook/src/notebook/assets/fonts/`, served
from `a/` with their licence (`a/fonts-license.txt`), and the stylesheet names them without a folder. The system
stacks stay as fallbacks. Nothing is fetched from another host (Requirement 3.2): no CDN, no remote font.

## Wording of the stylesheet

The stylesheet, the script and the markup are builder text and pass the blind scan at the builder level. They avoid
the terms the scan derives from the model files (design N28): a finding is fixed by rewording, never through the
stop list. So where this file names a property or a keyword that is such a term (for example line thickness or
linear timing), the stylesheet gets the same look another way or the look is dropped, and the stylesheet's own
wording is what counts. The one exception is a word the user approved for the stop list: `ahead` and `spacing`
(2026-11-19; both are settings of the wind tunnel, `constants.toml`, and say nothing about the body). So the
property `letter-spacing` and the word "spacing" in "Type and spacing" are allowed. Links never contain `..` (the
site is flat, design N28).

## Paper

- Background `--paper` `#fbf7ec`.
- Graph paper: faint lines `--rule-line` `#dfe6ef`, one along the bottom and one along the right edge of each 1.5rem
  tile, drawn with CSS gradients on the body. Text sits on the lines, so every text colour must also reach 4.5:1 on
  `--rule-line`.
- From 1000px the page also has a red margin line (`--margin-line` `#e2a9a2`, 2px, at 88px from the left edge) and
  binder holes (`--hole` `#e4dcc6`, edge `--hole-edge` `#cdc3a8`) in the left gutter, both behind the text.
- Content column at most 72rem wide, centred.
- Cards are `--card` `#fffdf8` with a 1px edge `--card-edge` `#e3d9bf` (the claim card, the rules card, the reader,
  the tab panels). `--accent` `#b4540a` is a line colour (the checked tab, the highlighter stripe's tint
  `--accent-tint` `#fde6c8` under the title); it is never a text colour. `--observed-bg` `#ecebe6` with the edge
  `--observed-edge` `#7b8088` is the background of an `observed` card.

## The three inks (Requirements 4.1, 4.5)

Each ink differs in typeface as well as colour, so it can be told apart without colour.

| Ink | Class | Colour | Typeface | Notes |
|---|---|---|---|---|
| Dr. Kiro's ink | `.ink-k` | `--ink-drkiro` `#1f3a8a` | serif: `"Lora", ui-serif, Georgia, "Times New Roman", serif`, upright | `white-space: pre-wrap`. Blocks (`.block-k`) have a 2px solid left rule in the same colour and the label "written by Dr. Kiro". Dr. Kiro's code blocks (`.code-k`) use the monospace of the pencil with the same left rule. |
| Pencil | `.ink-p` | `--ink-pencil` `#3d3d3d` | monospace: `"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | No rule. Measurements, outcomes, condition classes, reasons, counts, numbers the build computes. |
| Commentary ink | `.ink-c` | `--ink-commentary` `#2b2118` | sans: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`, 0.95em | The builder's text. |

The builder's text also appears in two other faces, each set by the element it stands in, with the commentary
colour: the title, the tagline, the photo captions of the cover and the tab titles are in the script (`"Caveat",
"Segoe Print", cursive`); every small heading is in the monospace (next section).

## Small headings

- `h2`, `h3`, the kicker and the block labels are in the monospace, 0.72rem to 0.78rem, weight 600, upper case and
  letter-spaced (`letter-spacing: 0.08em`). The captions of the measure list, of the spec cards and of the tabs
  follow the same rule.

Markup (`.ink-m`) carries no text of its own. The ink legend (`legend.html`) is linked from every page footer.

## Miss red (Requirement 6.4)

- `--miss-red` `#b3261e`.
- Used only on missed predictions and their measured values, through the classes `.miss`, `.miss-value`,
  `.miss-mark` (chart marks) and `.miss-stamp` (the cover's stamp). No other class uses it.
- Always shown with the word "miss" beside it. On the cover the word is the stamp "missed" (`.miss-stamp`, framed in
  the miss red and tilted, across the corner of the list of the prediction and the measured value); the cover has no
  separate outcome row. Never used for status stamps (a `rejected` stamp is not red).

## Rewrite red (Decision 51)

- `--rewrite-red` `#a3302a` on `--rewrite-bg` `#fbe8e4`: the state of a rejected row, which Dr. Kiro rewrote. It is
  not the miss red and is never used for a miss.
- Used for: the band and the left edge of a rejected card (`.rule-card.st-rejected`), the strike through the rule
  of a rejected card on the cover, the dotted line above "replaced by", the swatch of the cover's ink line and the
  count of rejected rows in a session's line on the cover. A stamp is still not red: the `rejected` stamp stays
  `--stamp-rejected`.

## Bench stamp (Requirements 8.2, 15.2)

- Class `.stamp` plus one of `.stamp-validated`, `.stamp-partly`, `.stamp-observed`, `.stamp-rejected`.
- Uppercase monospace, weight 600, 2px border in the stamp colour, rounded corners, rotated -2deg. The stamp itself
  is not letter-spaced; the small headings are.
- Colours: validated `--stamp-validated` `#1d5e3a`, partly `--stamp-partly` `#7a4b00`, observed `--stamp-observed`
  `#3a4a5c`, rejected `--stamp-rejected` `#5b2a6e`. A status cell that is not one of the four words uses the
  pencil colour (`.stamp` alone). The word is always written out; colour only adds to it.
- The label ("checked by the bench", "not checked by the bench", "not yet checked by the bench") sits below the
  stamp in small commentary type (`.stamp-label`).

## Instant photo (Requirement 6.3)

- Class `.photo`: white frame `--photo-frame` `#ffffff`, 8px on the sides and top, 28px at the bottom, a soft shadow.
- Rotated within +-1.5deg by a fixed rule from the trial number n: class `.tilt-<n mod 5>`, with `.tilt-0` -1.5deg,
  `.tilt-1` -0.75deg, `.tilt-2` 0deg, `.tilt-3` 0.75deg, `.tilt-4` 1.5deg.
- A brass pin `--pin-brass` `#b08d3c` at the top centre (`.photo::before`). The pin holds no text. On the cover the
  photos are held by a strip of tape (`--tape`, a translucent gold) in its place.
- Caption below the picture (`figcaption`), in commentary ink or pencil.
- The cover's large photo adds `.photo-large`; lab cards use `.photo-small`.
- The picture buttons (play, pause, step, whole sheet) are at least 44px by 44px on a screen narrower than 560px and
  on any touch screen (`pointer: coarse`); with a mouse they stay small.

## Magnified picture (Requirement 7.9, design N32)

- Beside each moving picture, except the lab cards, one magnified picture of the body, in one row with it (class
  `.photo-pair`, a wrapping flex row). On a narrow screen the magnified picture moves below the moving picture. On
  the cover it is not beside the moving picture: it stands in the top row of the miss (next section).
- The magnified picture is framed like an instant photo (class `.photo .photo-magnified`) with no tilt class, no
  caption and no controls. It is the whole magnified sheet, a still picture; its pixels are drawn without smoothing
  (`image-rendering: pixelated`).
- Its alt text is "Magnified view of the picture beside it".

## Cover layout (Requirements 13.1, 13.4, 13.7, 13.9-13.12; Decision 51)

Order of the page: the head (`.cover-head`: the kicker, the title, the tagline, one line naming the three inks with
the link to the legend); the miss (`.cover-miss`); the reader (`.cover-reader`, only when the build has reader runs);
the lab tabs (`.cover-labs`); the footer.

- The miss holds, in order: its heading, the top row (`.cover-top`), the row of evidence (`.cover-evidence`) and the
  card of rules (`.cover-rules`).
- The top row holds the claim card (`.claim-card`: the prediction in Dr. Kiro's ink, then the list of predicted and
  measured values, each with a small heading, with the stamp "missed" across its corner), the sticky note
  (`.sticky`) and the magnified picture (`.photo-magnified`, a body-lab trial only). The claim card and the sticky
  note share one block (`.cover-claim`).
- From 1000px the top row has two columns: the magnified picture at the left, as wide as 38% of the row but at most
  30rem and at least 16rem, and the claim card at its right with the sticky note beside it (the note wraps below
  the card when there is no room). The placement in columns is scoped to `.cover-top.with-sheet`; a top row without
  a magnified picture (a wind-tunnel miss) keeps its one column, with the claim card and the sticky note side by
  side in it. The prediction, the measured value and the stamp are in the first screen, with the picture. The row
  of evidence follows below: the moving picture (`.photo-large`) and the recorded track (`.track`), side by side
  from 1000px.
- On a narrow screen the cover is one column in this order: the claim card, the sticky note, the magnified picture,
  the moving picture, the track, the card of rules. The track box is cropped to the drawing (the svg's viewBox is the
  drawing plus an 8 unit margin), so no empty band stands above or below it, and the row adds no gap of its own.
- The cover has no outcome row. The stamp "missed" says it.
- The card of rules (`.cover-rules`) is one card: the heading "rules that cite it", one card per cited row
  (`.rule-card`, class `st-<status>` for the left edge; a rejected card is in the rewrite red, its rule struck, with
  one dotted line "replaced by <id> <rule>" and a drawn arrow), and at the bottom the `<details>` ("details"),
  inside the card, below the rule cards. Each cited row's stamp keeps its label below it, as in the table
  (Requirement 8.2).
- The lab tabs (`.tabs`) are index tabs side by side at every width, switched by radio buttons and the stylesheet
  alone, with no script (at most four). Their order is the order of the cover file. The tab of the lab of the missed
  prediction is the checked one when the page loads (the first tab when the cover file says "none"; a missed
  prediction whose lab has no tab fails the build). A tab holds the lab's kicker, its title in the script, and
  its engine and the budget of its session with the unit; its panel holds the chosen trial's photo ("chosen by a person") and the lab's ended sessions.
- The cover's visible commentary is at most 240 words (Requirement 13.6).

## Sticky note (Requirement 6.3)

- Class `.sticky`: background `--sticky` `#fff1a8`, commentary ink, rotated 1deg (the cover's note -1.5deg), a shadow.
- The cover's sticky note has three lines, all from the record: the measurement's name and the measured value with
  its unit in large pencil (`.sticky-number`); one sentence of what happened (`.sticky-happened`); and the
  conditions of the prediction ("when a = 1, f = 1, ..."). The sentence is "expected <measurement> between <low> and
  <high> <unit>, measured <value> <unit>: below the range" (or "above the range"), with ", on the other side of
  zero" when the range lies on one side of zero and the value on the other, for example "expected x between 0.2 and
  3 m, measured -0.2047 m: below the range, on the other side of zero". It names no direction of travel, because the
  record declares none. The sentence holds the range, so the note does not repeat it on a line of its own.
- The sticky note to a missed prediction on a session page names the measurement in its own element, set apart from
  the ids and the range (user, checkpoint 11): "<id> registered range [<low>, <high>], measured <name>: <value>
  miss", with the name in `.measure-name` (pencil, bold). The same wording is used in the list of missed predictions
  of a session without a table.
- The refused-end note is `.sticky.sticky-stamp`: a sticky note with the stamp border (2px, rounded, pencil colour),
  its heading in stamp type. Refusal message parts inside it keep their own inks.

## Strike-through of a rejected row (Requirement 8.3)

- Class `.row-rejected` on the row: `text-decoration: line-through` 2px. In the table the line is in `--graphite`
  `#3d3d3d`; on a card of the cover it is in `--rewrite-red`. The text keeps its full colour and contrast.
- The line covers the row's own text only (user, checkpoint 11). The stamp's label (`.stamp-label`, "checked by the
  bench" and the others) is never struck through: in the table the status cell (`td.status`) is left out of the
  rule, and on the cover only the rule text (`.cover-rule`) is struck.
- The "replaced by" tab (`.tab`) is a `<details>` whose content is the replacing row's rule text and a link to that
  row. It is open when the table is shown (`open="open"`, Requirement 8.13, Decision 49); a visitor may close it. In
  a card (next section) it is the dotted last line of the card, with a drawn arrow in front of its words, not a
  paper tab; the background `--tab` `#f1e9d2` is used by the opened evidence of a row and by the tabs of the cover.
- Reverse links ("replaces <id>, <id>") use `.replaces`.

## Spec table cards (Requirements 8.14, 10.1; Decision 51)

- The discovered spec table on a session page stays a `<table>` in the HTML (the bench reader's rows, the column
  names for a screen reader); each row is drawn as a card in the look of the cover's rule cards. One row is one
  `tbody.spec-row.rule-card.st-<status>`, which holds the row (`tr#row-<id>`), its refused-end note
  (`tr.row-note`) and its opened evidence (`tr.row-evidence`), so the evidence and the tab are inside the card.
- The table parts are `display: block`, so the HTML carries the explicit ARIA roles `table`, `rowgroup`, `row`,
  `columnheader` and `cell` on them; some engines drop the table semantics otherwise.
- The header row is clipped out of sight (not `display: none`). Each cell shows the name of its column from the bench
  (`data-label`) as a small letter-spaced caption; the id, the rule, the stamp and the "replaced by" tab have no
  caption of their own, and an empty cell is hidden.
- The head of the card has the id at the left and the stamp with its label at the right, then the rule, then scope,
  experiments and predictions, then the line "replaced by". A `rejected` card has the rewrite red (`--rewrite-bg`,
  `--rewrite-red`); an `observed` card has `--observed-bg`; the left edge of a card has the colour of its
  status.
- Below 480px the experiments and the predictions stand one under the other. From 1000px the cards stand in columns
  at least 21rem wide, two side by side where the column beside the margin has room.
- The arrow in front of "replaced by" is drawn with a CSS shape (`clip-path`), because none of the bundled typefaces
  has the arrow character.

## Type and spacing

- Base 17px, line height 1.5.
- Spacing scale 4, 8, 16, 24, 40px (`--space-1` to `--space-5`).

## Narrow screen (Requirement 3.5)

- At 360 CSS pixels the page is one column and the page's scroll width does not exceed the viewport.
- Margin photos (`.margin`) move below the table.
- The spec table is cards, so it has no sideways scroll. Its box (`.table-box`) is still `overflow-x: auto`, in case
  a cell holds an unbreakable text.
- The two-column layout (table with margin) starts at 1000px, and so does the cover's top row.
- The row evidence is a `<details class="evidence">` in its own table row below the row (`tr.row-evidence`, one
  cell across all columns, inside the row's card), never struck through. Its opened body (`.evidence-body`,
  background `--tab`, a 2px pencil rule on its left) is full width of the card below 1000px and at most 40rem wide,
  at the right of the card, from 1000px.
- The picture buttons are 44px targets (see Instant photo).

## Halloween (Requirement 6.5)

- One small ink-drawn bat and a cobweb corner, as inline SVG in the page markup (no file, no `xmlns` attribute).
  The drawing holds no text (no `<text>`, no `<title>`, no `<desc>`).
- Shown only at viewports of 1000px and wider, in the page gutter: at that width the body reserves a 96px left
  gutter and the decoration (`.deco`) is fixed inside it, so it never overlaps any text, table, chart or experiment
  entry. Hidden below 1000px.
- Used as `<svg class="deco" aria-hidden="true">…</svg>`; `pointer-events: none`.
- It sits behind nothing and never changes the colour of any text.

## Motion (Requirements 3.6, 7.6)

- A moving picture shows one cell every 500 ms (`--cell-interval: 500ms`), in reading order, looping.
- With `prefers-reduced-motion: reduce`, a moving picture starts paused on its first cell, and CSS transitions and
  animations are off.

## Contrast pairs (Requirement 4.6)

Every text colour is used on every background below, and every pair reaches at least 4.5:1 by the WCAG formula. A
test reads these two lists and the values from `notebook.css` and checks every pair. A new text colour or background
is added here first.

```
foreground: --ink-drkiro --ink-pencil --ink-commentary --miss-red --stamp-validated --stamp-partly --stamp-observed --stamp-rejected --rewrite-red
background: --paper --rule-line --sticky --photo-frame --tab --card --observed-bg --rewrite-bg --accent-tint
```
