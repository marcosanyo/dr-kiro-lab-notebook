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
(Requirement 6.2). Only system font stacks are used; no font file is fetched or shipped (Requirement 3.2).

## Wording of the stylesheet

The stylesheet, the script and the markup are builder text and pass the blind scan at the builder level. They avoid
the terms the scan derives from the model files (design N28): a finding is fixed by rewording, never through the
stop list. So where this file names a property or a keyword that is such a term (for example letter spacing of the
stamp, line thickness, linear timing, the word "spacing" in "Type and spacing"), the stylesheet gets the same look
another way or the look is dropped, and the stylesheet's own wording is what counts. Links never contain `..` (the
site is flat, design N28).

## Paper

- Background `--paper` `#fbf7ec`.
- Faint horizontal rule lines `--rule-line` `#dfe6ef`, one per line height, drawn with a CSS gradient. Text sits on
  the lines, so every text colour must also reach 4.5:1 on `--rule-line`.
- Content column at most 72rem wide, centred.

## The three inks (Requirements 4.1, 4.5)

Each ink differs in typeface as well as colour, so it can be told apart without colour.

| Ink | Class | Colour | Typeface | Notes |
|---|---|---|---|---|
| Dr. Kiro's ink | `.ink-k` | `--ink-drkiro` `#1f3a8a` | serif: `ui-serif, Georgia, "Times New Roman", serif`, upright | `white-space: pre-wrap`. Blocks (`.block-k`) have a 2px solid left rule in the same colour and the label "written by Dr. Kiro". Dr. Kiro's code blocks (`.code-k`) use `ui-monospace` with the same left rule. |
| Pencil | `.ink-p` | `--ink-pencil` `#3d3d3d` | monospace: `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | No rule. Measurements, outcomes, condition classes, reasons, counts, numbers the build computes. |
| Commentary ink | `.ink-c` | `--ink-commentary` `#2b2118` | sans: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`, 0.95em | The builder's text. |

Markup (`.ink-m`) carries no text of its own. The ink legend (`legend.html`) is linked from every page footer.

## Miss red (Requirement 6.4)

- `--miss-red` `#b3261e`.
- Used only on missed predictions and their measured values, through the classes `.miss`, `.miss-value` and
  `.miss-mark` (chart marks). No other class uses it.
- Always shown with the word "miss" beside it. Never used for status stamps (a `rejected` stamp is not red).

## Bench stamp (Requirements 8.2, 15.2)

- Class `.stamp` plus one of `.stamp-validated`, `.stamp-partly`, `.stamp-observed`, `.stamp-rejected`.
- Uppercase sans, bold, letter-spaced, 2px border in the stamp colour, rounded corners, rotated -2deg.
- Colours: validated `--stamp-validated` `#1d5e3a`, partly `--stamp-partly` `#7a4b00`, observed `--stamp-observed`
  `#3a4a5c`, rejected `--stamp-rejected` `#5b2a6e`. A status cell that is not one of the four words uses the
  pencil colour (`.stamp` alone). The word is always written out; colour only adds to it.
- The label ("checked by the bench", "not checked by the bench", "not yet checked by the bench") sits below the
  stamp in small commentary type (`.stamp-label`).

## Instant photo (Requirement 6.3)

- Class `.photo`: white frame `--photo-frame` `#ffffff`, 8px on the sides and top, 28px at the bottom, a soft shadow.
- Rotated within +-1.5deg by a fixed rule from the trial number n: class `.tilt-<n mod 5>`, with `.tilt-0` -1.5deg,
  `.tilt-1` -0.75deg, `.tilt-2` 0deg, `.tilt-3` 0.75deg, `.tilt-4` 1.5deg.
- A brass pin `--pin-brass` `#b08d3c` at the top centre (`.photo::before`). The pin holds no text.
- Caption below the picture (`figcaption`), in commentary ink or pencil.
- The cover's large photo adds `.photo-large`; lab cards use `.photo-small`.

## Sticky note (Requirement 6.3)

- Class `.sticky`: background `--sticky` `#fff1a8`, commentary ink, rotated 1deg, a shadow.
- The refused-end note is `.sticky.sticky-stamp`: a sticky note with the stamp border (2px, rounded, pencil colour),
  its heading in stamp type. Refusal message parts inside it keep their own inks.

## Strike-through of a rejected row (Requirement 8.3)

- Class `.row-rejected` on the row: `text-decoration: line-through` 2px in `--graphite` `#3d3d3d`. The text keeps
  its full colour and contrast.
- The "replaced by" tab (`.tab`) sits at the row's right edge as a paper tab, background `--tab` `#f1e9d2`; it is a
  `<details>` whose content is the replacing row's rule text in small type and a link to that row.
- Reverse links ("replaces <id>, <id>") use `.replaces`.

## Type and spacing

- Base 17px, line height 1.5.
- Spacing scale 4, 8, 16, 24, 40px (`--space-1` to `--space-5`).

## Narrow screen (Requirement 3.5)

- At 360 CSS pixels the page is one column and the page's scroll width does not exceed the viewport.
- Margin photos (`.margin`) move below the table.
- Wide tables scroll inside their own box (`.table-box`, `overflow-x: auto`).
- The two-column layout (table with margin, row evidence in a side panel) starts at 1000px.

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
foreground: --ink-drkiro --ink-pencil --ink-commentary --miss-red --stamp-validated --stamp-partly --stamp-observed --stamp-rejected
background: --paper --rule-line --sticky --photo-frame --tab
```
