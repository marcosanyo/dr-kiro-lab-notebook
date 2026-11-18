---
inclusion: always
---

# Reader

## What you have

- `request.md` holds the request. It is also the goal the bench tools give you, word for word.
- `given/` holds material about the system. It may be empty. Read all of it before your first hypothesis.

## Hypotheses

- Register H1 before your first experiment.
- The first line inside H1's `prediction` block is the relied-on line: `# relies on: <ids>`. Put in `<ids>` the ids,
  as they appear in `given/`, of what you rely on, separated by commas. Ids are rule rows such as `R<n>`,
  hypotheses such as `H<n>`, or experiments such as `E<n>`. If you rely on nothing, write `# relies on: none`.
  `none` stands alone. An id that is not in `given/` makes your result not counted.
- The relied-on line is frozen with H1. Name only what you actually used.
- A hypothesis is one EARS sentence and a `prediction` block, as the method describes.

Example of H1. Placeholders in angle brackets stand for your own values:

````markdown
### H1: <short title>

WHEN <condition>, THE system SHALL <response>.

```prediction
# relies on: <ids>
[[prediction]]
id = "P1"
measurement = "<measurement>"
range = [<low>, <high>]
label = "<condition class>"
[prediction.when]
<parameter> = <value>
```
````

## Experiments

- Every experiment sets `PHASE = "best"`.
- Write each experiment file and its verdict as the method describes.

## Your answer

Your last trial is your answer. Its measurements are judged against the request.

## Ending

Call `end_session` when your last trial is done and every experiment has a verdict. The `end_session` tool
description says what ending needs. This file does not repeat it.
