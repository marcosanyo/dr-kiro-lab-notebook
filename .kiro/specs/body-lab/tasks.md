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

- [ ] 4. README and lab
  - `body-lab/README.md` (how it measures, view size, running, limits); `bench-make-lab body-lab/lab`, committed.
  - _Requirements: 2.4, 5.2, 5.4_

- [ ] 5. One Dr. Kiro session of 40 trials — **Stop and ask**
  - The user runs it on the Mac. Pass: sealed as `ended`; `bench-scan` on the lab and the sealed folder reports
    nothing; also the checks of dr-kiro task 5.
  - _Requirements: 6.2_
