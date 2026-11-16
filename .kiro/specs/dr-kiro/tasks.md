# Tasks: dr-kiro

Tasks for Requirements 1-8 (design sections 1-9). Each task ends with `sh bench/scripts/check.sh` passing (tests,
ruff check, ruff format). Verification is kept to the minimum of Requirement 7: no tests beyond the four in design
section 9.

- [x] 1. Builder files and templates
  - Write `bench/src/bench/drkiro/files/`: `dr-kiro.json` (design 3), `dr-kiro-prompt.md` (design 4), `method.md`
    and `workflow.md` with `inclusion: always` front matter and the fenced examples with placeholders (design 5),
    and the three templates (design 6). English, no path, no part name, no number from a run.
  - Include the files as package data.
  - Tests: each fenced example, with its placeholders replaced by test values that fit the fake declaration, is
    accepted by `parse_hypothesis`, `prepare`/`compute` and `parse_table`; the agent file equals `lab-bench`
    design F10 plus the fields of design 3.
  - _Requirements: 1.1, 1.2, 2, 3, 4, 7.2_

- [x] 2. `bench-make-lab`
  - `lab.py` and the console script (design 7.1): copy the builder files, run the `bench-lab-hooks` installer,
    create `experiments/`, write the lab's `.gitignore`. Overwrite builder files only; never touch Dr. Kiro's files.
  - Test: a lab made by `bench-make-lab` passes `bench-scan` for the fake application.
  - _Requirements: 1.3, 5.1, 5.4, 7.1_

- [x] 3. `bench-new-session`
  - `session.py` and the console script (design 7.2), steps 1-7 in order, every argument required, nothing changed
    before step 4 if a check fails.
  - Test: it refuses while a session in the state folder is not sealed; after it runs, the lab holds only builder
    files and templates, the session is open, and the config file has `resume = true`.
  - _Requirements: 5.2, 5.3, 7.3_

- [x] 4. Running Dr. Kiro
  - Add the section "Running Dr. Kiro" to `bench/README.md` (design 8): the commands, the start line and the
    continue line, interactive and headless, and the steps for the fake session of task 5.
  - _Requirements: 6_

- [x] 5. Check Dr. Kiro in the first `body-lab` session (deferred)
  - Deferred by the user: no separate fake session. The first `body-lab` session in Kiro CLI checks the same
    points, and its `body-lab` task names this one.
  - Pass: the record ends with an `ended` seal; `bench-scan` on the sealed folder reports nothing; no steering
    other than `method.md` and `workflow.md` appears in Dr. Kiro's context (design 11). Note how many continue lines
    were needed.
  - If it fails, the session is stopped with `bench-stop` and a new one started after the fix; nothing else is
    judged here. A failure is reported, not worked around (`rules.md` 2).
  - The steps for a fake session stay in `bench/README.md` for a quick check after builder-file changes.
  - Result of the first run (body-1, macOS, 2026-11-13): sealed as `ended` with 0 budget left, without any
    continue line; `bench-verify` verified 117 entries; `bench-scan` on the lab and the sealed folder reported no
    findings, after hooks were changed to run with `python -B` (a `.pyc` in the lab had stopped the scan); Dr.
    Kiro named only `method` and `workflow` as its steering.
  - _Requirements: 7.4_

- [x] 6. Copies of the final spec
  - `bench/src/bench/record/spec_copy.py` and the console scripts `bench-export-spec` and `bench-check-discovered`
    (design 7.3). `bench-make-lab` writes the lab's `.gitignore` without `.kiro/specs/`; the two labs' `.gitignore`
    files follow it, and the labs track the three templates in `.kiro/specs/lab/`.
  - The blind scan: a folder with `source.json` is a copy, and a template in a lab is builder text (`lab-bench`
    15.10, 15.11, task 35).
  - `discovered/README.md` with its author sidecar, and the copy of `wt-004`, written with `bench-export-spec`.
  - `bench/README.md`, `body-lab/README.md` and `wind-tunnel/README.md`: the two commands after a session ends.
  - Tests: `bench/tests/unit/test_spec_copy.py`, and `tests/test_templates.py` in the `body-lab` and `wind-tunnel`
    adapters.
  - _Requirements: 5.4, 7.5, 8_
- [x] 7. Full check, scans and rehearsal
  - `sh bench/scripts/check.sh`; the `body-lab` adapter tests and the `wind-tunnel` model and adapter tests, with
    ruff; `bench-verify` on every sealed folder; `bench-check-discovered sessions discovered`; `bench-scan` on both
    labs, `sessions/` and `discovered/`; `wind-tunnel/rehearse_session.py` with real Docker, which now also writes,
    checks and scans the copy of its session.
  - _Requirements: 7.5, 8_
