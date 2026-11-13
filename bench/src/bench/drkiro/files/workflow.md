---
inclusion: always
---

# Workflow

## Four phases

Work through the phases in this order. Set `PHASE` in each experiment file to the phase it belongs to.

1. **Map the system** (`map`): find out what each input does to each measurement.
2. **State rules** (`rules`): turn what you saw into rules a measurement could prove wrong.
3. **Test the rules** (`test`): predict conditions never run, then run them. Label these predictions
   `new-combination` or `outside`.
4. **Predict the best point** (`best`): use the rules to predict the inputs that give the best result, then run
   them.

## Budget

Every trial uses one unit of budget. Keep enough budget for the test phase and the best phase.

## After each verdict

- Update `design.md`: what you now believe about the system, and why.
- Update `tasks.md`: tick what is done and add what comes next.

## Ending

Fill the `## Discovered spec` table at the end of `design.md`: one rule per row, with its scope, the experiments
and predictions behind it, and a status.

- `observed`: no cited prediction missed.
- `validated`: every cited prediction hit, and at least one of them was on conditions never run
  (`new-combination` or `outside`).
- `partly`: some cited predictions hit and some missed.
- `rejected`: a cited prediction missed. Name the id of the rule that replaces it in `replaced by`.

```markdown
## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | <rule> | <scope> | E<a>, E<b> | H<a>.P1 | validated | |
| R2 | <rule> | <scope> | E<c> | H<c>.P1 | rejected | R3 |
| R3 | <rule> | <scope> | E<c> | | observed | |
```

Then call `end_session`. If it refuses, fix the table as it says, and call it again.
