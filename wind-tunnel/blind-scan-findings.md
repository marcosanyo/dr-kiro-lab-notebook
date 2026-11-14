# Blind scan findings of wind-tunnel (tasks 12.3, 12.4, 13.4)
Status: **none.** The told set and the three fixed public reasons of `failures.py` have no finding.
History: task 12.3 found 19 distinct derived terms in the told set (`body`, `flow`, `height`, `depth`, `speed`,
`density`, `gap`, `picture`, `settings`, `time`, `end`, `number`, `Arc`, `Line`, `Point`, `move`, `_turn`, `value`,
`forces`). In task 12.4 (2026-11-14) the user approved all 19 for `.kiro/blind-scan/stop-list.txt`, treating
`forces` as a general word. They are stored in the scan's token form (lowercase, no underscore: `arc`, `line`,
`point`, `turn`, `number`). No told text was changed.
How this was checked: `bench-scan` terms of `adapter/scan_sources.toml` (the solver files and geometry scripts of
`wind-tunnel/model/`), minus the declared names and the stop list, matched against the told set
(`declaration_text` of `scan_adapter()`; `wind-tunnel-told-set --out <file>` writes it) and against the three fixed
public reasons of `failures.py`. The test `adapter/tests/test_told_set_terms.py` fails when any hit appears. The lab
folder does not exist yet (task 13.1), so no lab file is scanned yet.
