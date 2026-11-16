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

An automated check that fails, naming the file and line, when it finds a forbidden item. It looks for three kinds:

- **Terms**: names from `body-lab/model/` (the values of `name`, `class`, `joint`, `material`, `texture` and
  `model` attributes, and the actuator names in the wiring) and identifiers from the wind-tunnel solver setup.
- **Paths and file names**: a path pointing outside the lab into `model/`, `adapter/`, solver directories or the
  repository root, and the file names of the model and solver files.
- **Credentials**: anything that looks like one.

How the term list is built, at scan time, never copied by hand into the scanner:
1. Derive the terms from the model and solver files.
2. Remove the **allow list**: everything Dr. Kiro is told on purpose. That is each application's declared
   interface (knob names and ranges, number of channels, measurement names, picture, budget), taken from the
   application's own declaration, not from a second copy.
3. Remove the **stop list**: names that say nothing about the body's structure, such as material and texture
   names. The stop list is a reviewed file, `.kiro/blind-scan/stop-list.txt`. Adding or removing a word needs the
   user's approval.

Every part, joint and actuator name stays forbidden at the builder level, even when it is an ordinary English word.
The builder words its own text in `lab/`, bench output and the notebook to avoid them; it does not add them to the
stop list to make a check pass. There is no proximity rule: a forbidden term fails the scan wherever it appears.

Two levels, by who wrote the text:

| Written by | What | Scanned for |
|---|---|---|
| The builder or the bench | Everything the builder puts in `lab/` (agent, steering, hooks, templates); all bench output; the notebook's own text | Terms, paths and file names, credentials |
| Dr. Kiro | Its lab spec (`requirements.md`, `design.md`, `tasks.md`) and its experiment files | Paths and file names, credentials |

A guess written by Dr. Kiro, such as "this channel acts like a leg", is a hypothesis, not a leak. Text keeps the
level of its author wherever it is copied: snapshots in `sessions/`, the notebook build output, anything published.

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
- **A refused command is a stop.** When a tool call or command is refused, blocked or denied (by the user, a hook, a permission setting or a sandbox), do not do the same thing by another route: no other command, interpreter, script or tool that has the same effect (for example `rm -rf` refused, then the same deletion from `python`). Stop, say which command was refused and what it was meant to do, and ask the user. This holds for every file, folder, process and network operation, and for sub-agents. A refusal is also reported when the task is finished: the report lists every refused command, even if the user later allowed it.

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

## 5. Language and commits

- English for code, comments, steering, specs, docs and UI text. (The current `README.md` is replaced in the README
  step; do not edit it before then.)
- Exception: `docs/ja/` holds Japanese reference translations of the specs for the user. This is the user's policy;
  see `japanese-translations.md`. The English specs stay the source of truth.
- Exception: `docs/status.md` and `docs/requests/` are written in Japanese for the user (`handoff.md`).
- Reports and questions to the user are in Japanese. Code, commits, specs and steering stay in English.
- No co-author lines in commit messages.
- Commit only the files you created or changed for the task, each added by name. Never `git add -A` or `git add .`.

## 6. Open decisions

`[DECIDE: …]` in the brief marks something not settled. Ask the user; never pick silently. Record the answer in the
spec that needed it.
