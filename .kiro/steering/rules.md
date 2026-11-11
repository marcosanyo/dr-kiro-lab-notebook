---
inclusion: always
---

# Rules for everything we build

Source: `docs/brief.md` section 2. Every spec (requirements, design, tasks) and every piece of code, data, prose and
infrastructure in this repository follows these rules. A spec that needs an exception must name the rule and ask
the user; it may not make the exception itself.

## 1. Blind

Dr. Kiro must never learn how the system works except by experiment.

- Nothing inside a `lab/` folder may contain the model, part or joint names, what a channel does, solver files, or
  a path to any of them. This includes `lab/.kiro/` (Dr. Kiro's agent, steering and hooks), templates, examples and
  generated files.
- The bench returns measurements, pictures and the remaining budget. Nothing else: no stack traces, file paths,
  model or solver identifiers, log excerpts or library versions in anything Dr. Kiro can see.
- Bench error messages shown to Dr. Kiro say what Dr. Kiro did wrong in Dr. Kiro's own terms (channels, knobs,
  experiment file, budget). Full failure detail goes to the builder side only.
- The root `.kiro/` (this steering and the builder specs) is never visible to Dr. Kiro.

### Blind scan

An automated check that fails, naming the file and line, when it finds any of:
- content or identifiers from `body-lab/model/` (part, joint, actuator, body and site names; file names);
- wind-tunnel solver files, case setup, or identifiers from them;
- a path pointing outside the lab into `model/`, `adapter/`, solver directories or the repository root;
- anything that looks like a credential.

The forbidden terms are derived from the model and solver files at scan time, not copied by hand into the scanner.

Scope: every `lab/` folder, all bench output, `sessions/`, the notebook build output, and anything published.
Publishing refuses if the scan fails.

## 2. Fail fast, no fallbacks

- Never switch to another method, fill in a default for missing data, or swallow an error. Say what failed, where
  and why, and stop.
- No `try`/`except` that hides a failure, no "best effort" values, no retries that change the method, no silent
  defaults for missing configuration.
- A bench call has exactly three outcomes:
  1. **Ran**: the trial ran and its record was written.
  2. **Refused by a lab rule**: Dr. Kiro can fix it; nothing is recorded as a run and no budget is used. The bench
     still logs the refusal.
  3. **Bench failure**: the session stops, with the reason.
- This applies to the builder (Kiro) too: when a tool fails, a command errors, or a requirement is unclear, stop
  and ask the user. Do not work around it.

## 3. Reproducible

- Same input, same output.
- Every source of randomness takes an explicit seed, and the seed is recorded with the result it produced.
- Python 3.12 through `uv` only (see `tech.md`). Dependencies are locked.

## 4. Honest

- No invented numbers anywhere, including examples, placeholders in docs, test fixtures that are presented as
  results, and UI mock-ups. Every number shown as a result comes from a recorded run. Where an example needs a
  value that does not exist yet, write a visible placeholder such as `<measured>`, not a plausible-looking number.
- No words that suggest human injury or disability for how the body moves. Describe the motion itself: direction,
  distance, heading, speed, symmetry, which channels were active.

### Wording check

A separate check from the blind scan. It runs on prose only: README files, `docs/`, UI text of the notebook, and
Dr. Kiro's lab steering and agent prompts. It does not run on code identifiers, and it does not flag words that
are normal in code.

Initial word list (pending user review). Match whole words, case-insensitive, including the listed forms:

| Flagged | Forms |
|---|---|
| limp | limps, limping, limped |
| lame | lameness |
| cripple | crippled, crippling |
| hobble | hobbles, hobbling, hobbled |
| injured | injury, injuries |
| wounded | wound (as a verb or noun about the body) |
| maimed | maim |
| hurt | hurts |
| paralysed | paralyzed, paralysis |
| handicap | handicapped |
| spastic | spasm, spasms |
| amputee | amputated, amputation |
| deformed | deformity |
| invalid (as a person) | (manual review only: `invalid` is normal in code and in "invalid input") |

Not flagged: `disabled`, `invalid input`, `broken` (as in a broken build), `fault`, `failure`.

## 5. Language and commits

- English for code, comments, steering, specs, docs and UI text. (The current `README.md` is replaced in the README
  step; do not edit it before then.)
- No co-author lines in commit messages.
- Commit only the files you created or changed for the task, each added by name. Never `git add -A` or `git add .`.

## 6. Open decisions

`[DECIDE: …]` in the brief marks something not settled. Ask the user; never pick silently. Record the answer in the
spec that needed it.
