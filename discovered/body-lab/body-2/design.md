# Design

## Beliefs

The body is a small box with an arm-like appendage (pictures: 10-frame strips seen from above).

- Inputs held constant on c0, c2, c3, c4 give only a ~0.1 s transient (under 0.04 m, under 3 deg), then no motion (E1, E2). c0 also does nothing alone when oscillated (E3).
- c1 held constant drives steady motion along x with a steady turn. For a1 > 0 the body backs up at x ≈ -0.23·a1 over 5 s. For a1 < 0 it moves forward at about half that gain, x ≈ -0.115·a1. Heading ≈ +37·a1 deg over 5 s on both sides (E1, E7, E8).
- A sine on c3 alone only wiggles and turns the body (+30 deg) without travel (E3). Combined with c1 < 0 it propels the body forward by about 0.062 m per c3 cycle at a1 = -1 (0.053 at a1 = -0.5), up to 2 Hz (E8, E9). This interaction is not additive.
- Above about 2.5 Hz the forward travel saturates at about 0.7 to 0.75 m in 5 s (about 0.15 m/s). Square waves do not raise it (E10, E11).
- Heading drift under c1 plus c3 depends on f in no clear pattern: -66 deg at 1 Hz, -29 at 1.5, 0 at 2, +1 at 3, -10 at 4, -20 at 5.
- A wave across all five channels (E4, E5) mostly rotates the body, by up to ±150 deg, with |x| ≤ 0.22 m. Holding c0 constant under that wave removes most of the turn (E6).

Best point: c1 = -1 constant and c3 = sin(2π·5·t), other inputs 0, gave x = 0.753 m (E10 T36). f = 2 to 4 Hz gives 0.62 to 0.71 m with smaller heading drift.

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | With every input at 0, or c0, c2, c3 or c4 held constant alone, the body stays within 0.04 m and 3 deg of the start after a brief transient | constant inputs, one channel at a time, levels 0 or 1 | E1, E2 | H1.P1 | observed | |
| R2 | A constant level on c2, c3 or c4 alone moves or turns the body measurably (\|heading\| > 5 deg) | constant inputs | E2 | H2.P1 | rejected | R1 |
| R3 | A 1 Hz unit sine on c0 alone moves the body forward by more than 0.1 m | single-channel sine | E3 | H3.P1 | rejected | R11 |
| R4 | A travelling sine wave across c0..c4 (phase lag ph per channel) drives forward travel above 0.2 m | f 0.3–8 Hz, ph 0.5–3 | E4, E5 | H4.P1, H5.P1 | rejected | R5 |
| R5 | A travelling wave across all five channels mostly rotates the body (up to ±150 deg) with \|x\| ≤ 0.22 m | f 0.3–8 Hz, ph 0.5–3, amplitude 1 | E4, E5 | | observed | |
| R6 | Holding c0 constant at k under the c1..c4 wave changes x by more than 0.1 m | f 1.5, ph 1, k in {-1, 0, 1} | E6 | H6.P1 | rejected | R7 |
| R7 | The level of c0 has little effect (x 0.07–0.13 m for k = -1, 0, 1), but replacing a c0 sine with a constant removes most of the turn | wave f 1.5, ph 1 | E5, E6 | | observed | |
| R8 | Constant c1 moves the body along x with a gain that is symmetric in sign (x ≈ -0.23·a1) | constant c1, others 0 | E1, E7 | H7.P1 | rejected | R9 |
| R9 | Constant c1 gives x ≈ -0.23·a1 for a1 > 0 and x ≈ -0.115·a1 for a1 < 0, with heading ≈ 37·a1 deg over 5 s, both linear in time | constant c1 in [-1, 1], others 0 | E1, E7, E8 | H7.P2, H7.P3, H8.P1, H8.P2, H8.P3, H8.P4 | validated | |
| R10 | Adding a 1 Hz unit sine on c3 to c1 = -1 cancels the c1 turn and leaves x near 0.11 m | a1 = -1, f = 1 | E8 | H8.P5, H8.P6 | rejected | R11 |
| R11 | With c1 = a1 < 0 and a unit sine on c3, each c3 cycle moves the body forward ≈ 0.062 m (a1 = -1) or ≈ 0.053 m (a1 = -0.5) | f 1–2 Hz | E8, E9 | H9.P1, H9.P2, H9.P3 | validated | |
| R12 | The per-cycle gain of R11 continues at 3–5 Hz, so x ≈ 0.31·f | a1 = -1, f 3–5 Hz | E10 | H10.P1, H10.P2, H10.P3 | rejected | R13 |
| R13 | With c1 = -1 and a unit c3 oscillation at f ≥ 2.5 Hz, forward travel saturates at x ≈ 0.68–0.75 m in 5 s (≈ 0.15 m/s), whatever the waveform | a1 = -1, f 2–5 Hz, sine or square | E10, E11 | H11.P3 | observed | |
| R14 | A square-wave c3 stroke gives more travel than a sine at the same f | a1 = -1, f 2–3 Hz | E11 | H11.P1, H11.P2 | rejected | R13 |
