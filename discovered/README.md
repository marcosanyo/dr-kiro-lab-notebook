# Discovered specs

Each folder here holds the spec Dr. Kiro wrote in one session: `requirements.md`, `design.md` and `tasks.md`,
as the bench checked them when Dr. Kiro ended the session. `design.md` ends with the discovered spec table.

The files are copies, byte for byte, of the end snapshot in the sealed session record under `sessions/`.
`source.json` names that record entry and the SHA-256 of each file. The sealed record stays the source; the
copies are for reading. They are written with `bench-export-spec`, and `bench-check-discovered` checks that
every copy matches its record.

Only a session that Dr. Kiro ended, and whose record holds an end snapshot, has a copy:

- `body-lab/body-1` has no copy. It was sealed before the bench recorded the spec files at the end of a
  session, so its record does not hold the final table. The second body-lab session, `body-lab/body-2`, was run
  for that reason and has a copy.
- Stopped sessions (`wind-tunnel/wt-002`, `wind-tunnel/wt-003`) have no copy. They did not end with a spec.
