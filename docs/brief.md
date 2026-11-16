# Brief: Dr. Kiro's Lab Notebook

This document is the input for the specs. It says what we want, the rules, and what we already know from an earlier prototype. It does not say how to build it; that is your design. `[DECIDE: …]` marks things that are not settled: ask, do not pick silently.

## 1. What we are building
A lab where a Kiro custom agent ("Dr. Kiro") experiments on a system it has no description of, and writes that system's spec from evidence. Tagline: **The experiment gets the final edit.**

One skeleton, two applications (hackathon category: Skeleton Crew).

| | body-lab | wind-tunnel |
|---|---|---|
| System | A legged body in MuJoCo with unlabeled control channels | 2D flow around a body in OpenFOAM |
| What Dr. Kiro controls | One function of time per channel, values in [-1, 1] | Four knobs: `aspect` [0.5, 3], `corner` [0, 1], `splitter` [0, 3], `angle` [0, 15]° |
| One trial | 5 s of simulated time | One solver run |
| Budget per session | 40 trials | 24 runs |
| Measurements | Where the body ended up and which way it faces; poses over time | `cd`, `cl_mean`, `cl_amp`, `strouhal`, `shedding` |
| Picture | Overhead frames of the motion, in one PNG image sheet | Vorticity frames, in one PNG image sheet |

Three Kiros. **You are the builder**: you build the lab from specs in the root `.kiro/`. **Dr. Kiro is the experimenter**: a custom agent that opens only an application's `lab/` folder and uses that folder's own `.kiro/`. **The reader** is used in `build-from-spec` (section 4.5): it never sees the experiments and works from Dr. Kiro's spec alone.

## 2. Rules for everything you build (make these steering)
**Blind.** Dr. Kiro must never learn how the system works except by experiment.
- Nothing inside a `lab/` folder may contain the model, part or joint names, what a channel does, solver files, or a path to them.
- The bench returns measurements, pictures and the remaining budget. Nothing else.

**Fail fast, no fallbacks.**
- Never switch to another method, fill in a default for missing data, or swallow an error. Say what failed, where and why, and stop.
- A bench call has three outcomes: ran; refused by a lab rule (Dr. Kiro can fix it; nothing is recorded); bench failure (the session stops).

**Reproducible.** Same input, same output. Seeds are explicit and recorded. Python 3.12 through `uv` only.

**Honest.** No invented numbers anywhere, including examples. No words that suggest human injury or disability for how the body moves.

**English** for code, comments, steering and UI text. **No co-author lines** in commits.

## 3. Repository layout
```
/.kiro/            your specs, steering, hooks; blind-scan/ holds the reviewed stop list
/bench/            the skeleton
/body-lab/         application 1 (adapter/, model/, lab/)
/wind-tunnel/      application 2 (same shape)
/notebook/         the lab notebook (static site)
/build-from-spec/  the reader's requests and the script that starts its runs
/infra/            AWS CDK
/sessions/         published session records
/discovered/       Dr. Kiro's final spec of each ended session, copied from its sealed record
/bench-run/        builder-side files of a running session; git-ignored
/docs/brief.md     this file
/docs/ja/          Japanese reference translations of the specs
/docs/status.md    the current step and open questions, for handing over between sessions
/docs/requests/    the user's requests for specs
/scripts/          repository scripts
/spikes/           scratch area, not part of the product
```
- Each application runs on its own. body-lab needs no Docker.
- `body-lab/model/` is supplied by the user (made in the earlier prototype). Do not edit it.
- The README must point to both kinds of `.kiro`: the root one (how the lab was built) and each `lab/.kiro` (Dr. Kiro itself).

## 4. The specs

### 4.1 `lab-bench` (the skeleton)
**Why.** The rules of method must hold because of the instrument and the agent's permissions, not because a prompt asks.

**Dr. Kiro's loop.** Write a hypothesis as an EARS statement that a measurement can prove wrong, with predicted values, in its lab spec's `requirements.md` → write one experiment file that names it → ask the bench to run it → record a verdict and update `design.md` and its own plan in `tasks.md`.

**What must be true.**
- No experiment runs without a hypothesis registered first. A registered hypothesis cannot be edited or deleted afterwards. Each experiment runs once. The previous verdict comes before the next run. The budget cannot be exceeded.
- The bench, not Dr. Kiro, writes the record of every run and every refusal.
- After every run the bench keeps a snapshot of Dr. Kiro's three spec files, so that a session can be replayed.
- A session ends as a sealed record that the notebook can be built from.
- Dr. Kiro's task in every lab runs in this order: map the system → state rules → test the rules by predicting conditions never run → use the rules to predict the best point.
- Dr. Kiro's `design.md` ends with a `## Discovered spec` table, one rule per row, with the columns id, rule, scope, experiments, predictions, status and replaced by. The status is one of four words, and the bench refuses to end the session unless the word agrees with the record:
  - `validated`: every cited prediction hit, and at least one hit was on conditions never run (the bench's condition class for that prediction is a new combination or outside the tried range).
  - `partly`: the row cites at least one hit and at least one miss.
  - `observed`: the row cites at least one experiment and no missed prediction.
  - `rejected`: the row cites at least one miss, and "replaced by" names the row that replaces it.
- An application plugs in by providing only: its knobs, how to run one trial, what is measured, one picture, and its budget.
- Decided after the MCP spike (`lab-bench` Requirement 17): the bench is an MCP server over stdio and Dr. Kiro has no shell. Dr. Kiro's tools are file read and write, limited to its lab by a pre-tool hook, and the bench tools.

**What we know from the prototype.**
- Gates written only in the prompt drifted; gates in the bench held.
- Dr. Kiro tries to import libraries and read files from experiment code. Experiment code must be plain math, checked before anything is simulated.
- Two modes were enough: compare up to 3 variants, or sweep 1–2 parameters over 6 fixed points.
- The lab needs only two hooks: one that stops reads and writes outside the lab's notebook files, one that logs every action.
- The gates suit property-based testing over random sequences of agent actions.

**Done when.** A full session runs against a fake application; the gates hold under property-based tests; the sealed record is enough to rebuild every screen of the notebook.

### 4.2 `body-lab`
**Why.** The first application: Dr. Kiro learns to move a body it knows nothing about.

**What must be true.**
- Channels are numbers, not names. Dr. Kiro is told how many there are and nothing else.
- Measurements are what a camera above the body could measure, so that hardware could meet the same contract later.
- Renders without a display. Installs with `uv` only.
- Each trial yields one PNG image sheet of overhead frames, which the notebook plays frame by frame.

**Done when.** One full Dr. Kiro session (40 trials) completes; an automated scan shows that nothing in `lab/` or in any bench output reveals the model.

### 4.3 `wind-tunnel`
**Why.** To show the skeleton is general: same bench, same agent, same notebook, a completely different system.

**What must be true.**
- The body is a rounded rectangle of height 1, `aspect` long, with corner rounding, an optional thin plate behind it, at an angle to the flow.
- A solver failure or a run that does not settle is a bench failure with the reason, never a made-up value.
- Solver files stay outside `lab/`. Dr. Kiro is told the knob names and ranges, not the setup.

**What we know from the prototype (settings that worked).**
- OpenFOAM v2412 `pimpleFoam` in Docker image `opencfd/openfoam-default:2412`; mesh from Gmsh; laminar; Reynolds number 150.
- Domain: inlet 6 heights ahead, outlet 18 behind, walls 7 above and below.
- Run to time 150, average the forces from 80, take frames near the end. Time step adapts with a Courant limit of 0.8.
- One run took about 1.5 minutes on 3 processes; 3 runs at once were fine.
- `shedding` was "lift amplitude above 0.01".
- Check: a circle at Reynolds number 100 gave a Strouhal number of 0.167 (literature about 0.165).

**Done when.** The circle check is within 5% of the literature Strouhal number and the README reports the difference; one full session (24 runs) completes; the README reports how long this application took to connect and how much code it is.

### 4.4 `lab-notebook`
**Why.** A judge should understand in 60 seconds what Dr. Kiro discovered, and that every line of it has evidence.

**The centre: the discovered spec table.** The notebook is built around Dr. Kiro's `## Discovered spec` table (section 4.1). It shows the table as the sealed record holds it and never makes up a status, a row or a replacement.
- Every row shows its status as the bench's word, written out: `validated`, `partly`, `observed` or `rejected`. Colour may add to the word, never replace it.
- `rejected`: the row is struck through, and the row named in "replaced by" stands beside it. Shown when the table has such rows.
- `partly`: the cited predictions that missed are shown in red, and named as misses in words.
- `observed`: explained in the words of the bench's check: seen in experiments; no cited prediction missed; Dr. Kiro does not claim `validated`. Opening the row shows the condition class of each cited prediction, from the record.
- The scope is shown as Dr. Kiro wrote it. Beside it, the notebook shows what the record says was run: the range of the trials the row cites, and the conditions that no trial in the session ran. Both come mechanically from the record, never from reading the scope text. `[DECIDE: how the conditions are divided into run and not run; how this is shown for body-lab, whose inputs are functions of time.]`
- Pressing a row opens the experiments and predictions behind it.
- A session whose record holds no table (body-1) shows "no table" as it is. The table is never filled in by hand.

**The feel (design direction, not a stylesheet).**
- A scientist's paper notebook, not a dashboard. Photos of experiments are pinned like instant photos; side notes are sticky notes.
- Three inks with fixed meanings, used everywhere: one for Dr. Kiro's own words, one for our commentary, pencil for measurements.
- Quiet first screen: little text, moving pictures do the talking, details open on demand. A moving picture is a trial's image sheet played frame by frame.
- One theme, with no switch. Halloween only as a light touch, never at the cost of legibility.
- Propose the visual system yourself and write it as steering, so later parts stay consistent. The user will compare the result with a reference and tell you what to change.

**What a visitor can do.**
- **Cover:** see one prediction that missed: the prediction and what happened; when the table has rows, also the row that cites it and the row that replaces it, if there is one. A session with no missed prediction says so. Choose a lab.
- **A session:** the highlight (a contrast and the best result, as moving pictures), the discovered spec table, the progress, Dr. Kiro's plan, and every experiment with its hypothesis, prediction, measurement, verdict and moving picture.
- **Replay:** step or play through the session one experiment at a time; everything on the page shows the state as of that experiment; a rejected rule is struck through and its replacement appears. Labelled as a replay, never as live.
- **Prediction chart:** for each prediction on conditions never run, the registered range and the measured value. Misses are as visible as hits.
- **How the lab works:** the two levels of spec (yours and Dr. Kiro's), what Dr. Kiro can and cannot touch, the two applications side by side, and how often the bench refused and why.
- **Built from the spec:** every `build-from-spec` run (section 4.5): the request, the pass condition committed beforehand, the spec rows the reader relied on, the measured result, and pass or fail, with the runs of the same request in the other two setups beside it. Runs that failed are shown like the others. Until a run is committed, this part says that there are none yet.
- Link straight to one experiment of one session.

The notebook has no chat box and no control that starts an experiment. Checking a rule again happens on the Kiro side (Run all on the lab's `tasks.md`); the notebook shows the result once the next record is committed.

**What must be true.** Static site built only from sealed session records, and for `build-from-spec`, its sealed run records and the committed requests. Works on a phone. No third-party requests. Text written by Dr. Kiro is shown as written and escaped.

**Done when.** Sessions from both labs render; every row of every discovered spec table shows its status word; replay matches the snapshots at every step (tested); the user accepts the first screen.

### 4.5 `build-from-spec`
**Why.** To show that the discovered spec is useful: a Kiro that never saw the experiments reads only the spec and does what a request asks.

**What must be true.**
- The reader gets Dr. Kiro's three spec files (`requirements.md`, `design.md`, `tasks.md`) of one ended session, taken from the final snapshot in its sealed record, never from the lab's working files, and one request in words (for example, walk an arc of a given radius to the right). It does not see the experiment files, pictures, records, the model or the notebook.
- The user writes the request and its pass condition, and commits them before the run. The pass condition is a range of numbers. Each request is one file in `build-from-spec/requests/`, with the ranges in a form a program reads. The commit hash of the request file is recorded with every run.
- Before it runs anything, the reader names the spec rows it relies on.
- The reader works through the same bench. The budget is 12 trials in body-lab; the wind-tunnel budget is decided in the `build-from-spec` spec. Each run is recorded in the same form as a session and sealed, and the notebook shows it (section 4.4).
- Pass or fail is decided mechanically, by comparing the measured values with the committed ranges. No person judges a run.
- Every run is shown, including the ones that failed.
- For comparison, the same request is run in three setups: with the spec, with no spec, and with the raw session record only. Tools, agent configuration and budget are the same in all three.
- One script starts every run. It makes an empty working folder, puts in it only what that setup allows, and records the setup, the request and the session the spec or record came from. The working folder passes the blind scan before every run.
- The blind rules (section 2) apply to the reader as they do to Dr. Kiro.

**Done when.** At least one request has been run in all three setups; the records are sealed and pass verification; pass or fail is decided mechanically; the notebook shows every run, including the ones that failed.

### 4.6 `publish` (AWS)
**Why.** The notebook at a public URL, reproducible from code, with nothing published that breaks the blind.

**What must be true.**
- Private S3 bucket behind CloudFront, HTTPS only, defined in CDK, with a budget alarm.
- Publishing a session or a `build-from-spec` run scans it first and refuses, naming the file and line, if it finds the model, solver files, part names or anything like a credential. The same scan runs as a hook on your side.
- Deployed from a developer machine with short-lived credentials. No long-lived keys anywhere.
- Access control at the edge that one setting turns on and off (on until submission).
- If AWS MCP servers for documentation or CDK are available to you, use them and note what for.

**Done when.** The README steps deploy to a fresh account; a session with a planted model fragment is refused; the URL serves the notebook.

## 5. Order
1. Steering.
2. `lab-bench` with a fake application.
3. `body-lab`, then one full session.
4. `wind-tunnel`, then one full session.
5. `lab-notebook` against those sessions, with the place for `build-from-spec` runs.
6. `build-from-spec`, then its runs.
7. `publish`.
8. README: the two levels of spec first; the two applications side by side; how to reproduce; limits; what was brought in from the prototype; what was tried and dropped.

## 6. Prompts
- **Steering:** "Read docs/brief.md sections 1–3. Create steering for product, tech and structure, so that every later spec follows the rules in section 2. Ask me about anything unclear."
- **A spec:** "Read docs/brief.md sections 1–3 and 4.N. Create the requirements for the spec `<name>`. The brief gives the goal and what must be true; work out the full requirements yourself, as user stories with EARS acceptance criteria. Ask me your questions first, including every DECIDE item. Do not start the design until I approve the requirements."
- **Design:** "Write the design. Say which requirements each part covers, which properties you will test, and what would make you stop and ask."
- **Steering toward the reference (user to Kiro, during the build):** describe the difference in behaviour, numbers or appearance, and ask for the requirement to be updated before the code.
