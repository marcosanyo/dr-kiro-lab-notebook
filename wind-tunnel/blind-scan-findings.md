# Blind scan findings of wind-tunnel (tasks 12.3, 13.4)

Status: **open, 19 distinct derived terms; the user decides (task 12.4).** Nothing was added to
`.kiro/blind-scan/stop-list.txt` and no told text was changed.

How this list was made: `bench-scan` terms of `adapter/scan_sources.toml` (the solver files and geometry scripts of
`wind-tunnel/model/`), minus the declared names and the stop list, matched against the told set
(`declaration_text` of `scan_adapter()`; `wind-tunnel-told-set --out <file>` writes it) and against the three fixed
public reasons of `failures.py`. The public reasons have no hit. The lab folder does not exist yet (task 13.1), so
no lab file is scanned.

Every hit below is in the told set, so a change of the text needs the user's approval (Requirement 1.7). Each row is
one matched word of the told set with its derived term, where the term comes from, and the line of the told set. The
test `adapter/tests/test_told_set_terms.py` fails when this table and the real hits differ in any way, so a new
collision or a fixed one shows up at once. The table must hold exactly the hits and nothing else.

Order followed (Requirement 13.4): rename the identifier the builder chose, else reword, else ask. Nothing was
renamed: the section and key names of `settings.toml` (`flow`, `body`, `time`, `speed`, `height`, `depth`, `density`,
`end`, `picture`, `gap`), the template placeholders (`SPEED`, `DENSITY`, `END`) and the names in `geometry.py`,
`mesh.py` and `solver_output.py` are fixed by the design's Data Models table and used in about every module and
test of `model/` and `adapter/`. Renaming them is a wide change of finished tasks, and the told words (body, flow,
height, depth, density, speed, point, line, end ...) would need a new unrelated name for each. The builder asks
instead. OpenFOAM keywords (`value`, `forces`, and the `end`, `time` words of `endTime`) cannot be renamed.

| Matched word | Derived term | Source (file:line) | Text |
|---|---|---|---|
| `body` | `body` | wind-tunnel/model/settings.toml:11 | told set:2 |
| `height` | `height` | wind-tunnel/model/settings.toml:7 | told set:2 |
| `heights` | `height` | wind-tunnel/model/settings.toml:7 | told set:2 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:2 |
| `arc` | `Arc` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:1; wind-tunnel/model/src/wind_tunnel_model/geometry.py:33 | told set:3 |
| `body` | `body` | wind-tunnel/model/settings.toml:11 | told set:3 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:3 |
| `body` | `body` | wind-tunnel/model/settings.toml:11 | told set:4 |
| `end` | `END` | wind-tunnel/model/case/system/controlDict.in:14; wind-tunnel/model/settings.toml:21; wind-tunnel/model/src/wind_tunnel_model/casegen.py:37 | told set:4 |
| `flow` | `flow` | wind-tunnel/model/settings.toml:4 | told set:4 |
| `gap` | `gap` | wind-tunnel/model/settings.toml:61 | told set:4 |
| `heights` | `height` | wind-tunnel/model/settings.toml:7 | told set:4 |
| `line` | `Line` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:1; wind-tunnel/model/src/wind_tunnel_model/geometry.py:73 | told set:4 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:4 |
| `point` | `Point` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:18; wind-tunnel/model/src/wind_tunnel_model/mesh.py:94 | told set:4 |
| `body` | `body` | wind-tunnel/model/settings.toml:11 | told set:5 |
| `end` | `END` | wind-tunnel/model/case/system/controlDict.in:14; wind-tunnel/model/settings.toml:21; wind-tunnel/model/src/wind_tunnel_model/casegen.py:37 | told set:5 |
| `flow` | `flow` | wind-tunnel/model/settings.toml:4 | told set:5 |
| `height` | `height` | wind-tunnel/model/settings.toml:7 | told set:5 |
| `moves` | `move` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:133 | told set:5 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:5 |
| `turns` | `_turn` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:115 | told set:5 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:7 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:8 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:9 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:10 |
| `number` | `_number` | wind-tunnel/model/src/wind_tunnel_model/solver_output.py:62 | told set:11 |
| `picture` | `picture` | wind-tunnel/model/settings.toml:53 | told set:12 |
| `body` | `body` | wind-tunnel/model/settings.toml:11 | told set:13 |
| `density` | `DENSITY` | wind-tunnel/model/case/system/functions.in:7; wind-tunnel/model/settings.toml:9; wind-tunnel/model/src/wind_tunnel_model/casegen.py:36 | told set:13 |
| `depth` | `depth` | wind-tunnel/model/settings.toml:8 | told set:13 |
| `flow` | `flow` | wind-tunnel/model/settings.toml:4 | told set:13 |
| `forces` | `forces` | wind-tunnel/model/case/system/functions.in:1 | told set:13 |
| `height` | `height` | wind-tunnel/model/settings.toml:7 | told set:13 |
| `speed` | `SPEED` | wind-tunnel/model/case/0/U.in:11; wind-tunnel/model/settings.toml:6; wind-tunnel/model/src/wind_tunnel_model/casegen.py:35 | told set:13 |
| `speeds` | `SPEED` | wind-tunnel/model/case/0/U.in:11; wind-tunnel/model/settings.toml:6; wind-tunnel/model/src/wind_tunnel_model/casegen.py:35 | told set:13 |
| `times` | `time` | wind-tunnel/model/settings.toml:20 | told set:13 |
| `value` | `value` | wind-tunnel/model/case/0/U.in:18; wind-tunnel/model/case/0/p.in:22 | told set:13 |
| `point` | `Point` | wind-tunnel/model/src/wind_tunnel_model/geometry.py:18; wind-tunnel/model/src/wind_tunnel_model/mesh.py:94 | told set:14 |
| `settings` | `settings` | wind-tunnel/model/settings.toml (file name) | told set:14 |
