# Design

## Beliefs

- System: 5 inputs c0..c4 (functions of time, [-1,1]), 5 s trials, measures x, y, heading and tracks (51 points, every 0.1 s). A small body with two appendages seen from above. Goal: maximise x.
- Constant inputs do not translate the body (|x| < 0.03 m). Constant c2, c3, c4 give a small heading offset (+1.7, -3.9, -1.7 deg) that settles within ~0.1 s (E1).
- c0 and c1 are inert in every setting tried: constant, 1 Hz sine, and combined with c2 (E1, E2, E3, E4).
- A 1 Hz sine on c2 alone turns the body left by ~23 deg. c3 and c4 alone mostly wobble it (E2). Pairs of c2, c3, c4 in phase turn it by 57 to 74 deg, all three by 126 deg (E4). The turn is not the sum of single-channel turns.
- Phase lag of c3 behind c2 (1 Hz, E5) sets the heading: +83 deg at 45, +56 at 90, +23 at 135, -8 at 180, -24 at 225, -4 at 270. x is 0.04 to 0.07 m at 45, 90, 225, 270, near 0 at 135.
- Frequency at lag 270 deg (E6, E7): x = 0.055 (0.5 Hz), 0.042 (1), 0.048 (1.5), 0.144 (2), 0.085 (2.5), 0.036 (3), 0.117 (4), 0.079 (6), 0.012 (8). Peak near 2 Hz, not monotonic.
- Lag 225 deg beats 270 deg at 2 Hz (0.241 vs 0.144 m). At 2.1 Hz and 225 deg x = 0.266 m, the best found (E8).
- Final x includes a wobble of a few cm from the tracked point, so a single x value is uncertain by about 0.02 m.
- Not explored: c4 together with c2 and c3 at 2 Hz, lags between 180 and 225 deg at 2 Hz, amplitudes below 1, non-sine waveforms.

## Best point

c2 = sin(2 pi 2.1 t), c3 = sin(2 pi 2.1 t - 225 deg), c0 = c1 = c4 = 0: x = 0.266 m, y = 0.079 m, heading -7.7 deg.

## Discovered spec

| id | rule | scope | experiments | predictions | status | replaced by |
|---|---|---|---|---|---|---|
| R1 | A constant level on any single channel (and all channels at 0) does not translate the body: \|x\| < 0.03 m after 5 s. | c0..c4 held at +1 one at a time, others 0 | E1 | H1.P1, H1.P2 | observed | |
| R2 | c0 and c1 have no effect on x, y or heading: alone as a constant or as a 1 Hz sine, they match the all-zero baseline, and adding them to c2 changes nothing. | c0, c1 at constant +1 or 1 Hz sine amplitude 1 | E1, E3, E4 | H1.P2, H3.P2, H4.P2 | observed | |
| R3 | c1 alone at 1 Hz moves the body forward, and a constant on c0 amplifies the turn from a sine on c2. | c0, c1 | E2, E3 | H2.P1, H3.P1 | rejected | R2 |
| R4 | A 1 Hz sine on c2, c3 and c4 together, in phase, turns the body left by more than 60 deg; c2 alone turns it about 23 deg and in-phase pairs turn it 57 to 74 deg. | c2, c3, c4 in phase, 1 Hz, amplitude 1 | E2, E4 | H4.P1 | observed | |
| R5 | With c2 and c3 at 1 Hz, the phase lag of c3 behind c2 sets the turn: large left turn for lags 45 to 90 deg, about 0 at 180 deg, small right turn at 225 deg. x is small (< 0.07 m) at every lag. | c2, c3 at 1 Hz, lag 45 to 270 deg | E5 | H5.P1, H5.P2 | observed | |
| R6 | x grows with drive frequency. | c2, c3 at lag 270 deg, 1 to 8 Hz | E6 | H6.P2 | rejected | R7 |
| R7 | At lag 270 deg, x peaks near 2 Hz (0.144 m) and is lower at 1.5 Hz, 2.5 Hz and 3 Hz; it is not monotonic in frequency. | c2, c3 sines, lag 270 deg, 0.5 to 8 Hz | E6, E7 | H6.P1, H7.P1, H7.P2 | observed | |
| R8 | At about 2 Hz, a lag of 225 deg gives more forward travel than 270 deg: 0.241 and 0.266 m against 0.144 m. Best found: 2.1 Hz, lag 225 deg, x = 0.266 m. | c2, c3 sines at 2 to 2.1 Hz, lag 225 or 270 deg, c0, c1, c4 = 0 | E6, E7, E8 | H7.P3, H8.P1 | validated | |
| R9 | The final x reading carries a wobble of a few cm (about 0.02 m) from the tracked point, so one x value is uncertain at that level. | all drives with sines | E2, E5, E6, E7, E8 | | observed | |
