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
4. **Predict the best point** (`best`): use the rules to predict the inputs that best meet the goal given in the
   bench tools' descriptions, then run them.

In the map, rules and test phases, study every measurement, not only the one the goal names.

## Budget

Every trial uses one unit of budget. Keep enough budget for the test phase and the best phase.

## After each run, before its verdict

- Tick the experiment's task line in `tasks.md`.
- Update `design.md`: what you now believe about the system, and why.

## After each verdict

- Add the next experiment to `tasks.md` when you plan it, not before. Leave the unrun ideas in a short note under
  the last task line when the budget runs out.

## Ending

Fill the `## Discovered spec` table at the end of `design.md`: one rule per row, with its scope, the experiments
and predictions behind it, and a status.

- `observed`: no cited prediction missed.
- `validated`: every cited prediction hit, and at least one of them was on conditions never run
  (`new-combination` or `outside`).
- `partly`: some cited predictions hit and some missed.
- `rejected`: a cited prediction missed. Name the id of the rule that replaces it in `replaced by`.

A rule that was refuted is not removed from the Discovered spec table; it stays as a row with the status `rejected`.

```markdown
## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | <rule> | <scope> | E<a>, E<b> | H<a>.P1 | validated | |
| R2 | <rule> | <scope> | E<c> | H<c>.P1 | rejected | R3 |
| R3 | <rule> | <scope> | E<c> | | observed | |
```

Then tick the last task line and call `end_session`. If it refuses, fix the table as it says, and call it again.
