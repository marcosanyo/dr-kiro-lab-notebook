# Tasks: body-lab

Each task ends with `sh bench/scripts/check.sh` and the adapter's tests passing.

- [x] 1. Bench: `goal` and `measured_by`
  - Add both fields to `Declaration` and `check_declaration`, to the fake application, and to the tool
    descriptions (`describe.py`); update the dr-kiro `workflow.md` (study every measurement in phases 1-3).
  - _Requirements: lab-bench 2.1, dr-kiro 3.3_

- [x] 2. Simulation and measurer
  - `body-lab/adapter/` uv project; `sim.py`, `measure.py`, `settings.py` (design 2, 3).
  - _Requirements: 1, 2, 5.1_

- [x] 3. Picture and adapter
  - `picture.py`, `adapter.py`, `scan_sources.toml`; the four tests of design 7.
  - _Requirements: 3, 4, 5, 6.1_

- [x] 4. README and lab
  - `body-lab/README.md` (how it measures, view size, running, limits); `bench-make-lab body-lab/lab`, committed.
  - _Requirements: 2.4, 5.2, 5.4_

- [x] 5. One Dr. Kiro session of 40 trials — **Stop and ask**
  - The user runs it on the Mac. Pass: sealed as `ended`; `bench-scan` on the lab and the sealed folder reports
    nothing; also the checks of dr-kiro task 5.
  - Result of the first run (body-1, macOS, 2026-11-13): sealed as `ended` with 0 budget left, without any
    continue line; `bench-verify` verified 117 entries; `bench-scan` on the lab and the sealed folder reported no
    findings, after hooks were changed to run with `python -B` (a `.pyc` in the lab had stopped the scan); Dr.
    Kiro named only `method` and `workflow` as its steering.
  - _Requirements: 6.2_
- [ ] 6. A second Dr. Kiro session of 40 trials (body-2) — **Stop and ask**
  - Why: body-1's record holds no discovered spec table. It was sealed before the bench recorded the three spec
    files at the end of a session (`lab-bench` 10.4), so it has no end snapshot and no copy in `discovered/`
    (`dr-kiro` Decision 12). body-1 stays as it is, sealed and committed.
  - Conditions that differ from body-1, all from the main branch at the start of body-2: the workflow steering
    has the sentence that a refuted rule stays in the table as a `rejected` row (`dr-kiro` Requirement 3.7,
    Decision 8); `end_session` records the end snapshot; the lab's `.kiro/specs/` is tracked in the template state.
    Session id `body-2`, seed 2 (body-1 used seed 1); the same adapter, model, goal and budget.
  - The user runs it on the Mac, with the steps the builder wrote in chat. Pass: as task 5, and
    `bench-export-spec` writes `discovered/body-lab/body-2/` and `bench-check-discovered` passes.
  - Then the builder records the result here and updates `discovered/README.md`.
  - _Requirements: 6.2_
