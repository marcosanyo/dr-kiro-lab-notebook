# Design: dr-kiro

Covers Requirements 1-8. Builds on `lab-bench` (core, front end F1-F12). Decisions taken with the user are listed
at the end.

## 1. Lab layout

```
<application>/lab/
  .kiro/
    agents/dr-kiro.json          agent definition (builder)
    agents/dr-kiro-prompt.md     the prompt (builder)
    steering/method.md           how to work with the bench (builder, always included)
    steering/workflow.md         the four phases and the discovered spec (builder, always included)
    hooks/                       confine.py, calllog.py and three hook files (builder, bench-lab-hooks)
    specs/lab/requirements.md    Dr. Kiro's files, written from the templates by bench-new-session; tracked in git
                                 in their template state
    specs/lab/design.md
    specs/lab/tasks.md
  experiments/                   Dr. Kiro's experiment files (git-ignored)
  pictures/                      written by the bench (git-ignored)
```

Session configs live outside the lab, in `bench-run/<application>/<session id>.toml` (git-ignored,
`structure.md`). The final spec of each ended session is copied outside the lab, into
`discovered/<application>/<session id>/` (section 7.3), so that the next session's Dr. Kiro cannot read it.

## 2. Package layout

```
bench/src/bench/drkiro/
  __init__.py
  lab.py            bench-make-lab: write the builder files, install the hooks
  session.py        bench-new-session: check, reset, write templates, start, write the config
  files/            the builder files and templates, as they are copied
    dr-kiro.json
    dr-kiro-prompt.md
    method.md
    workflow.md
    requirements.md
    design.md
    tasks.md
```

The files are package data and are copied byte for byte. They are English (`rules.md` 5) and contain no path,
no part name and no number taken from a run.

## 3. Agent definition (Req 2)

`lab-bench` design F10 with these fields added:

```json
{
  "name": "dr-kiro",
  "description": "Experimenter: discovers the spec of an unknown system from evidence.",
  "prompt": "file://./dr-kiro-prompt.md",
  "resources": ["file://.kiro/steering/**/*.md"]
}
```

- `prompt` with `file://` resolves from the agent file's folder (kiro.dev, custom agent configuration reference).
- `resources` loads the two steering files at start. The steering docs say custom agents do not load steering on
  their own; the configuration reference says they inherit default resources. The explicit glob works in both
  cases. Inherited defaults can only add the user's own global steering, which is not builder text from this
  repository; the manual session checks that no other steering appears (as task 21 of `lab-bench`, C14).
- Steering front matter is `inclusion: always`, so the files behave the same if Kiro loads them as steering.

## 4. Prompt (Req 2.2)

About ten lines. It says: you are Dr. Kiro, an experimenter; you study a system you know nothing about except the
inputs and measurements the bench tools describe; your goal is the system's spec, written from evidence in your
three spec files; you work alone: never ask the user a question and never wait for an answer; keep going until
you have called `end_session` successfully, or the bench reports that the session has ended; follow the method
and workflow steering. No rule of method is repeated in the prompt, so there is one source.

## 5. Steering (Req 3)

### 5.1 `method.md`

Short sections, each a few bullets:

- **The loop.** Write a hypothesis in `requirements.md`, register it, write one experiment file that names it,
  run it, open its pictures, record a verdict, update `design.md` and `tasks.md`. Then the next.
- **Hypotheses.** One EARS sentence and a `prediction` block (format below). Each prediction names a measurement,
  the parameter values, and a range a measurement can fall outside. Label each prediction with the condition class
  you believe it has. After registering, never edit the heading, statement or block; write notes and results below
  the block.
- **Experiments.** The file format (below): first line `# H<n>: <title>`, `PHASE`, `MODE`, `PARAMS`, `TRIALS`,
  and one function per function-of-time input. Plain math only: functions, local variables, `if`, `for` over a list
  or `range`, lists, arithmetic, `math`. Keep parameter names the same across experiments; a renamed parameter
  makes predictions not comparable. For a structurally different compare variant, add a flag parameter and branch
  on it with `if`. Each set of inputs runs once; an exact repeat is refused.
- **Pictures.** Each trial's picture is a file whose path the run returns; open it with the file tool.
- **Paths.** Write only paths relative to your folder in your files, never an absolute path.
- **When the bench says no.** A refusal says what to fix: fix it and continue. A bench failure ends the session:
  stop.

### 5.2 `workflow.md`

- **Four phases**, with their `PHASE` values: map the system (`map`), state rules (`rules`), test the rules by
  predicting conditions never run (`test`), use the rules to predict the best point (`best`). One line on the aim of
  each. A test or best prediction should be labelled `new-combination` or `outside`. In map, rules and test,
  study every measurement, not only the one the goal names; the goal (in the tool descriptions) is used in the
  best phase.
- **Budget.** Every trial uses one unit. Keep enough for the test and best phases. No numbers.
- **After each verdict.** Update `design.md` with what you now believe and why, and tick or add tasks in
  `tasks.md`.
- **Ending.** Fill the `## Discovered spec` table: one rule per row, with its scope, the experiments and
  predictions behind it, and a status. The four statuses and when each applies (`lab-bench` Requirement 12.3), in
  plain words: `observed` if no cited prediction missed; `validated` only if every cited prediction hit and at
  least one was on untried conditions; `partly` if some hit and some missed; `rejected` if one missed, with the id
  of the rule that replaces it. One sentence follows the definitions (Req 3.7, Decision 8): a refuted rule is not
  removed from the table; it stays as a row with the status `rejected`. Then call `end_session`; if it refuses,
  fix the table as it says.

### 5.3 Examples (Req 3.6)

`method.md` and `workflow.md` carry fenced examples in the exact formats of `lab-bench` 5.1, 5.2 and 7.1: a
hypothesis block, a compare experiment with a flag parameter, a sweep experiment, and a discovered spec table.
Every value is a placeholder in angle brackets (`<low>`, `<high>`, `<value>`, `<measurement>`, `<parameter>`).
Placeholders are not valid TOML or Python, so a copied example is refused by the bench until Dr. Kiro fills it in.
The examples use generic input names (`<input>`) so that no application's names appear.

## 6. Templates (Req 4)

```
requirements.md   # Requirements / ## Hypotheses
design.md         # Design / ## Observations / ## Discovered spec  + table header and separator row only
tasks.md          # Tasks / - [ ] Map the system / - [ ] State rules / - [ ] Test the rules / - [ ] Predict the best point
```

The empty table passes every snapshot and is refused only by `end_session` (`lab-bench` 12.5).

The templates are builder text. In a lab they sit where Dr. Kiro's files go (`.kiro/specs/**` is in the lab's
`dr_kiro` globs), so the blind scan reads a lab file that holds exactly a template's bytes at the builder level
(`lab-bench` 15.11). The adapter tests of `body-lab` and `wind-tunnel` scan the templates at the builder level with
their own terms; `bench/tests/unit/test_spec_copy.py` does it for the fake application. The lab keeps the
templates in git, so a checkout shows what Dr. Kiro starts from.

## 7. Commands (Req 5)

### 7.1 `bench-make-lab <lab>`

Copies the agent file and prompt into `.kiro/agents/`, the two steering files into `.kiro/steering/`, and runs
the `bench-lab-hooks` installer. Overwrites those files only. It creates `experiments/` if missing and writes the
lab's `.gitignore` (`experiments/`, `pictures/`). Nothing under `.kiro/` is ignored (Req 5.4).

### 7.2 `bench-new-session`

```
bench-new-session --application <name> --adapter <module:factory> --scan-sources <toml> --stop-list <file>
                  --lab <lab> --state <dir> --sessions <dir> --session-id <id> --seed <n> --config-out <file>
```

All arguments are required (`rules.md` 2). Steps, each failing with a message and changing nothing before step 4:

1. The lab has the builder files (made by `bench-make-lab`); otherwise refuse.
2. Every session folder in the state folder has a seal entry as its last entry; otherwise refuse, naming it.
   Sessions are told apart by folder; the check opens each record with the record verifier.
3. The config file does not exist yet; a session id is used once.
4. Remove every file in `experiments/` and `pictures/`, and the three files in `.kiro/specs/lab/`. These are
   Dr. Kiro's files of the previous session; the sealed record holds them (`lab-bench` 13.2), so nothing is lost.
5. Copy the three templates into `.kiro/specs/lab/`.
6. `Session.start` with the given values; a refusal is printed and the command fails.
7. Write the config file (`lab-bench` F7 fields, paths relative to it) with `resume = true`, and close the session.

### 7.3 Copies of the final spec (Req 8)

`bench/src/bench/record/spec_copy.py`:

- `final_spec(record)` verifies the sealed record (`bench-verify`'s check), takes the one snapshot entry with
  `"for": "end"`, and returns the three files' bytes with the application, the session, the snapshot's sequence
  number and hash, and the seal's hash. It fails, saying which, for a record that does not verify, a `stopped`
  seal, or an `ended` seal without an end snapshot (body-1). `build-from-spec` reads the reader's spec through it.
- `bench-export-spec <sealed session folder> <discovered folder>` writes
  `<discovered>/<application>/<session id>/requirements.md`, `design.md`, `tasks.md` and `source.json`
  (`json.dumps` with `indent=2` and sorted keys, then a newline, so the bytes depend only on the record). It refuses
  an existing folder; a copy is written again by deleting it first.
- `bench-check-discovered <sessions folder> <discovered folder>` reads every Dr. Kiro session record in
  `<sessions>/<application>/<session id>/`. It skips `<sessions>/build-from-spec/`, which holds reader run records
  (`lab-bench` Requirement 22). For an ended record with an end snapshot it compares the copy's files
  with what `bench-export-spec` would write; for the others it requires that there is no copy. It reports any
  other file or folder in the discovered folder, except `README.md` and `README.md.authors.json`. It prints one
  line per session and exits 1 with the list of problems.
- After a session is sealed as `ended`, the builder runs both commands and commits the copy with the sealed folder
  (`bench/README.md`, the application READMEs). Before publishing, `bench-check-discovered` runs on the whole
  repository; a test does the same.
- The blind scan reads a folder with `source.json` as a copy (`lab-bench` 15.10): the three files at the Dr. Kiro
  level while their SHA-256 match `source.json`, and `source.json` at the builder level without its hashes.
  `discovered/README.md` has an author sidecar (bench) like any other builder file outside a lab and a record.

## 8. Running a session (Req 6)

`bench/README.md` gets a section "Running Dr. Kiro":

```sh
bench-make-lab body-lab/lab                       # once, and after builder files change
bench-new-session ... --config-out bench-run/body-lab/<id>.toml
export BENCH_SESSION_CONFIG="$PWD/bench-run/body-lab/<id>.toml"
export BENCH_HOOK_LOG="$PWD/bench-run/body-lab/<id>.hook-log.jsonl"
cd body-lab/lab
kiro-cli chat --agent dr-kiro                     # then type the start line
```

- Start line: `Begin the session.` Continue line: `Continue the session.`
- Without interaction, where the builder has a `KIRO_API_KEY`:
  `kiro-cli chat --v3 --no-interactive --require-mcp-startup --agent dr-kiro "Begin the session."`
  `--trust-all-tools` is not used: the agent's permission rules already allow what Dr. Kiro needs, and the hooks
  refuse the rest.
- After the session: `bench-stop` only if it did not end on its own.

## 9. Tests (Req 7)

Example tests, in `bench/tests/drkiro/`:

| Test | Req |
|---|---|
| A lab made by `bench-make-lab` passes `bench-scan` for the fake application. | 1.3, 7.1 |
| Each fenced example, with placeholders replaced by test values that fit the fake declaration, is accepted by `parse_hypothesis`, `prepare`/`compute` and `parse_table`. | 3.6, 7.2 |
| The agent file equals `lab-bench` F10 plus the fields of section 3. | 2.1 |
| `bench-new-session` refuses with an open session; afterwards the lab holds builder files and templates only, and the session is open with `resume = true` in the config. | 5.2, 5.3, 7.3 |
| `bench/tests/unit/test_spec_copy.py`: the final spec of wt-004 is its end snapshot; body-1 and wt-002 are refused; an edited, extra or missing file and a copy without a record are reported; the repository's `discovered/` matches `sessions/`; a copy is scanned by hash; a template in a lab is scanned at the builder level. | 7.5, 8 |

Manual (Req 7.4): one session in Kiro CLI with the fake application's lab in `bench-run/fake/` and a budget of
12 trials. The builder sends only the start line and, if needed, the continue line. Pass: the record ends with an
`ended` seal and `bench-scan` on the sealed folder reports nothing.

## 10. Requirements coverage

| Part | Requirements |
|---|---|
| `files/dr-kiro.json`, `files/dr-kiro-prompt.md` | 2 |
| `files/method.md`, `files/workflow.md` | 1, 3 |
| `files/requirements.md`, `design.md`, `tasks.md` | 4 |
| `lab.py` | 1.1, 5.1, 5.4 |
| `session.py` | 5.2, 5.3 |
| `bench/README.md` | 6 |
| `bench/tests/drkiro/`, manual session | 7 |
| `record/spec_copy.py`, `discovered/README.md`, `test_spec_copy.py` | 5.4, 7.5, 8 |

## 11. What would make me stop and ask

- Kiro CLI does not load the steering through `resources`, or loads steering from outside the lab.
- Dr. Kiro stops before `end_session` in a way the continue line does not fix.
- The blind scan flags a builder file and the only fix would be a stop-list word.

## Decisions

Approved by the user before this spec was written:

1. One command makes a lab; the builder files are the same for every application (Req 1, 5).
2. Two steering files: method and workflow (Req 3.1).
3. Dr. Kiro never asks the user; a fixed start line and continue line (Req 2.2, 6).
4. No budget split in numbers; keep budget for the last two phases (Req 3.4).
5. Examples with visible placeholders, in the `lab-bench` formats (Req 3.6).
6. The wording check of `rules.md` is dropped as excessive; nothing about it goes into Dr. Kiro's files.
7. Minimal verification: a few automated tests and one short fake session (Req 7).
8. A refuted rule stays in the discovered spec table as a `rejected` row (Req 3.7). The notebook is centred on that
   table (`docs/brief.md`, the notebook section), and a deleted refuted rule would leave no trace of it. The
   workflow template gets one sentence after the definition of `rejected`; it says nothing on whether a half-right
   rule is `partly` or `rejected`. This changes Dr. Kiro's conditions from the next session on. The sealed sessions
   `body-1` and `wt-004` were made without the sentence and are not rewritten. Requested by the user
   (`docs/status.md`, the brief revision).
9. Dr. Kiro's final spec is kept in git as plain Markdown, in `discovered/<application>/<session id>/` (Req 5.4, 8).
   Requested by the user: the competition rules forbid listing `.kiro` or its folders in `.gitignore`, and the spec
   Dr. Kiro wrote is the product, to be read in the repository. The copies sit outside the lab, so the next
   session's Dr. Kiro cannot read an earlier conclusion, and outside the record folders, which stay as sealed.
10. The lab's three spec files are tracked in their template state (user's choice of two options). A session
    leaves them changed in the working tree until the next `bench-new-session` writes the templates again; they
    are never committed in that state.
11. A template in a lab is scanned at the builder level, by its bytes (`lab-bench` 15.11). Alternative: scan the
    package templates only. Not chosen: the tracked copies in the lab would then be scanned at the Dr. Kiro level.
12. body-1 gets no copy: its record has no end snapshot, and the table it held at the end is not in the record.
    `bench-export-spec` refuses it and `discovered/README.md` says why. A second body-lab session will be run
    (user's decision). No check before `bench-new-session` that the previous session was copied: a copy can be
    written from the record at any time; the check runs before publishing instead (user's decision).
