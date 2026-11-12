# Tasks: dr-kiro

Tasks for Requirements 1-7 (design sections 1-9). Each task ends with `sh bench/scripts/check.sh` passing (tests,
ruff check, ruff format). Verification is kept to the minimum of Requirement 7: no tests beyond the four in design
section 9.

- [ ] 1. Builder files and templates
  - Write `bench/src/bench/drkiro/files/`: `dr-kiro.json` (design 3), `dr-kiro-prompt.md` (design 4), `method.md`
    and `workflow.md` with `inclusion: always` front matter and the fenced examples with placeholders (design 5),
    and the three templates (design 6). English, no path, no part name, no number from a run.
  - Include the files as package data.
  - Tests: each fenced example, with its placeholders replaced by test values that fit the fake declaration, is
    accepted by `parse_hypothesis`, `prepare`/`compute` and `parse_table`; the agent file equals `lab-bench`
    design F10 plus the fields of design 3.
  - _Requirements: 1.1, 1.2, 2, 3, 4, 7.2_

- [ ] 2. `bench-make-lab`
  - `lab.py` and the console script (design 7.1): copy the builder files, run the `bench-lab-hooks` installer,
    create `experiments/`, write the lab's `.gitignore`. Overwrite builder files only; never touch Dr. Kiro's files.
  - Test: a lab made by `bench-make-lab` passes `bench-scan` for the fake application.
  - _Requirements: 1.3, 5.1, 5.4, 7.1_

- [ ] 3. `bench-new-session`
  - `session.py` and the console script (design 7.2), steps 1-7 in order, every argument required, nothing changed
    before step 4 if a check fails.
  - Test: it refuses while a session in the state folder is not sealed; after it runs, the lab holds only builder
    files and templates, the session is open, and the config file has `resume = true`.
  - _Requirements: 5.2, 5.3, 7.3_

- [ ] 4. Running Dr. Kiro
  - Add the section "Running Dr. Kiro" to `bench/README.md` (design 8): the commands, the start line and the
    continue line, interactive and headless, and the steps for the fake session of task 5.
  - _Requirements: 6_

- [ ] 5. One fake session in Kiro CLI — **Stop and ask**
  - Not automated: it needs the user's Kiro CLI. The user runs the fake session from `bench/README.md` with a
    budget of 12 trials, sending only the start line and, if needed, the continue line.
  - Pass: the record ends with an `ended` seal, and `bench-scan` on the sealed folder reports nothing. Also note
    whether any steering other than `method.md` and `workflow.md` appears in Dr. Kiro's context (design 11).
  - Nothing else is judged. A failure is reported, not worked around (`rules.md` 2).
  - _Requirements: 7.4_
