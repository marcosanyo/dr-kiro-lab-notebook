# Brief: Dr. Kiro Frankenstein

This document is the input for the specs. It says what we want, the rules, and what we already know from an earlier prototype. It does not say how to build it; that is your design. `[DECIDE: …]` marks things that are not settled: ask, do not pick silently.

## 1. What we are building
A lab where a Kiro custom agent ("Dr. Kiro") experiments on a system it has no description of, and writes that system's spec from evidence. Tagline: **Discover the Spec. Don't Just Follow It.**

One skeleton, two applications (hackathon category: Skeleton Crew).

| | body-lab | wind-tunnel |
|---|---|---|
| System | A legged body in MuJoCo with unlabeled control channels | 2D flow around a body in OpenFOAM |
| What Dr. Kiro controls | One function of time per channel, values in [-1, 1] | Four knobs: `aspect` [0.5, 3], `corner` [0, 1], `splitter` [0, 3], `angle` [0, 30]° |
| One trial | 5 s of simulated time | One solver run |
| Budget per session | 40 trials | 24 runs |
| Measurements | Where the body ended up and which way it faces; poses over time | `cd`, `cl_mean`, `cl_amp`, `strouhal`, `shedding` |
| Picture | Overhead frames of the motion | Vorticity animation |

Two Kiros. **You are the builder**: you build the lab from specs in the root `.kiro/`. **Dr. Kiro is the experimenter**: a custom agent that opens only an application's `lab/` folder and uses that folder's own `.kiro/`.

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
/.kiro/            your specs, steering, hooks
/bench/            the skeleton
/body-lab/         application 1 (adapter/, model/, lab/)
/wind-tunnel/      application 2 (same shape)
/notebook/         the lab notebook (static site)
/infra/            AWS CDK
/sessions/         published session records
/docs/brief.md     this file
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
- Dr. Kiro's `design.md` ends with a `## Discovered spec` table: one rule per row, with its scope, the experiments behind it, the predictions that tested it, and a status.
- An application plugs in by providing only: its knobs, how to run one trial, what is measured, one picture, and its budget.
- `[DECIDE after the MCP spike: the bench is an MCP server and Dr. Kiro has no shell; or the bench is one command and Dr. Kiro's shell allows only that.]`

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
- Each trial yields a short animation for the notebook.

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

**The feel (design direction, not a stylesheet).**
- A scientist's paper notebook, not a dashboard. Photos of experiments are pinned like instant photos; verdicts are rubber stamps; side notes are sticky notes.
- Three inks with fixed meanings, used everywhere: one for Dr. Kiro's own words, one for our commentary, pencil for measurements.
- Quiet first screen: little text, moving pictures do the talking, details open on demand.
- Halloween only as a light touch (the dark theme), never at the cost of legibility.
- Propose the visual system yourself and write it as steering, so later parts stay consistent. The user will compare the result with a reference and tell you what to change.

**What a visitor can do.**
- **Cover:** read one real prediction Dr. Kiro registered, then press to reveal what happened; see three lines of the discovered spec; choose a lab.
- **A session:** the highlight (a contrast and the best result, as moving pictures), the progress, the discovered spec, Dr. Kiro's plan, and every experiment with its hypothesis, prediction, measurement, verdict and moving picture.
- **Discovered spec card:** each rule with its stamp, scope and evidence; pressing a rule shows the pair of moving pictures behind it (where it holds, where it does not).
- **Replay:** step or play through the session one experiment at a time; everything on the page shows the state as of that experiment; a rejected rule is struck through and its replacement appears. Labelled as a replay, never as live.
- **Prediction chart:** for each prediction on untried conditions, the registered range and the measured value. Misses are as visible as hits.
- **How the lab works:** the two levels of spec (yours and Dr. Kiro's), what Dr. Kiro can and cannot touch, the two applications side by side, and how often the bench refused and why.
- Link straight to one experiment of one session.

**What must be true.** Static site built only from sealed session records. Works on a phone. No third-party requests. Text written by Dr. Kiro is shown as written and escaped.

**Done when.** Sessions from both labs render; replay matches the snapshots at every step (tested); the user accepts the first screen.

### 4.5 `publish` (AWS)
**Why.** The notebook at a public URL, reproducible from code, with nothing published that breaks the blind.

**What must be true.**
- Private S3 bucket behind CloudFront, HTTPS only, defined in CDK, with a budget alarm.
- Publishing a session scans it first and refuses, naming the file and line, if it finds the model, solver files, part names or anything like a credential. The same scan runs as a hook on your side.
- Deployed from a developer machine with short-lived credentials. No long-lived keys anywhere.
- Access control at the edge that one setting turns on and off (on until submission).
- If AWS MCP servers for documentation or CDK are available to you, use them and note what for.

**Done when.** The README steps deploy to a fresh account; a session with a planted model fragment is refused; the URL serves the notebook.

## 5. Order
1. Steering.
2. `lab-bench` with a fake application.
3. `body-lab`, then one full session.
4. `wind-tunnel`, then one full session.
5. `lab-notebook` against those sessions.
6. `publish`.
7. README: the two levels of spec first; the two applications side by side; how to reproduce; limits; what was brought in from the prototype; what was tried and dropped.

## 6. Prompts
- **Steering:** "Read docs/brief.md sections 1–3. Create steering for product, tech and structure, so that every later spec follows the rules in section 2. Ask me about anything unclear."
- **A spec:** "Read docs/brief.md sections 1–3 and 4.N. Create the requirements for the spec `<name>`. The brief gives the goal and what must be true; work out the full requirements yourself, as user stories with EARS acceptance criteria. Ask me your questions first, including every DECIDE item. Do not start the design until I approve the requirements."
- **Design:** "Write the design. Say which requirements each part covers, which properties you will test, and what would make you stop and ask."
- **Steering toward the reference (user to Kiro, during the build):** describe the difference in behaviour, numbers or appearance, and ask for the requirement to be updated before the code.
