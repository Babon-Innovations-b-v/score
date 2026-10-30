# score/stages/sim_body/inside/evaluation/

Level 1's runner (#70): `__init__.py` runs levels 2 and 3 on every body of a side (tuning, or the held-out check)
side by side, one `_case.py` process per SOMA body in Newton's Python (at most `MOST`, systemd-run MemoryMax=6G, two
threads, only while `FREE_GB` is available), and reads back each clip's honest measures (`_measure`: joint error,
rotation error on `fit._frozen`, the frozen copy of main's calibration, bones outside SOMA's skin by region through
`fit._skin` and, for level 1's least squares only, their depth outside (`bones outside depth mm`, smooth where the
share is a step; #70, 2026-10-30): the stage's record and level 1's score share that one code), each clip's written twice: `measures.json`
unrounded, the one the solver reads (rounded measures read as flat to its differences), and `m.json`, the copy people
read (`rounded`), and `angles.npz` beside them, mink's angles per frame, the card's seeds (`fit/_card`, plan step 2). A case's body is its name less its motion (`body_of`; `arms_raise` and `sit_stand` hold an underscore, `TWO_WORD_MOTIONS`). Each evaluation's group-end centres go to the
worker in `rest.json` with SOMA's template rig: `_case` moves `landmarks.CENTRES` and the measure's copy by them (the
fit's end targets, the sizing's lengths and the joint measure read them) and reads the calibration table again at rest
from them (`calibration._measure`), never from motion; the run dir holds that rig as `rig.npz`. `tuning.whole` calls it each evaluation; `level1.py <run dir> --python <Newton's Python>` is the thin
command. The check bodies are scored every few iterations and at the end, never used to choose; `accepted` is the
held-out rule (within 10 % of the tuning bodies).

- `_card_case.py <seeds root> ...` is `_case.py` with level 3 on the card (`fit._card._clip`, each frame seeded from the
  seeds root's angles.npz) and the card's measures (`fit._card._measure`); `_case.py` stays the reference and the runner's
  worker until the card's measures equal the CPU's to their rounding on the tuning cases (card build step 5).
- `_card_batch.py` (card build step 5b) is `_card_case.py` for every body of an evaluation in one process: per body
  the state `_case.prepared` lays put back from a copy saved before the first body (`Saved`), never added on top; the
  sizing and the file without constants once per body and calibration table, across sets too (`cached_set_up`:
  links, trusts and weights leave them alone, a centre set reads the table anew), then level 2 and `Fitting` once
  per (set, body) (`sim_body.constants_set_up`; a body's clips share one rig,
  refused otherwise) and every clip's frames in one card batch; `fit.following` not run (nothing here reads it);
  each clip written by `_case.written`, its targets the ones its batch was solved on (`clip_targets`, once per body
  run: `fit.targets` skinning the landmarks was made three times per clip, 2026-10-30; level 2's recordings, the
  body's clips in order, take them too, `recorded_targets`, checked array by array; two heavy sets' 14 cases bit
  for bit, angles too). Gate 2026-10-29 (tall and slim, 14 cases, the per-case card run's constants):
  equal to the per-case card path, skins exact, joints within 5.5e-4 mm; one process 29 s wall, imports included.
  All 70 tuning cases (same constants): equal to the per-case card path on all 70 (skins exact, joints within
  1.1e-3 mm), against the CPU the same 3 cases one to three hand vertex-frames off as the per-case card's (joints
  within 3.3e-3 mm); one process 102 s wall against the per-case card's 237 s and the CPU's 447 s (4 processes each).
- `_card_sets.py <seeds root> <sets root> ...` (card build step 6a) runs every set of one level 1 Jacobian
  (`tuning._differences.nudged`'s, the base point first: <sets root>/<set>/ holds its table, weights and rest) in one card
  process, `_card_batch.body_run` per set and body, each nudged set seeded from the base point's own angles. Level 2
  and the set-up still run per (set, body): G = 137 groups, so 138 sets a Jacobian; not yet batched across sets.
  With `--same-seeds` every set starts from the seeds root: `measured_many(sets, cases, out, python, seeds_root)`
  writes out/s00000.. and runs it once; `level1.py --card <seeds root>` evaluates on the card that way and hands
  `tuning.whole` its `evaluate_many`. The batched columns' gate against the serial CPU columns (2026-10-30, heavy and tall_kimodo, 6 columns: a link, a
  trust, both hips' centres, both globals): with the skin rows as the share outside the columns were 1.4 to 21 % apart
  (noise: the share is a step), with them as the depth outside 0.04 to 0.61 %; the Gauss-Newton steps' cosine 0.99995
  (pass 0.99). The old 1e-4 bar cannot hold: the card's level 3 stops at its float32 floor.
  Never warm-start a nudged set from the base point's answer (tried 2026-10-30, level 2's least_squares x0: the
  columns 1.3 to 9.7 % apart, step cosine -0.91): a solve stops anywhere inside its tolerance, and a 0.4 step's
  difference is that small, so every set starts where the base point started.
  `_card_sets.py ... --warm <tolerance>` (2026-10-30, off by default) is the second try: level 2 per body warm from
  the base point's "solved" (`evaluation.warmed`, a differently laid-out answer refused) and every set, the base point
  too, at that one tight ftol/xtol/gtol. Measured on the 6a gate's 7 sets (heavy and tall kimodo, 2026-10-30, against
  the serial CPU columns; cold: 0.04 to 0.61 %, cosine 0.99998, 28 to 38 evaluations): at 1e-8 (scipy's default)
  the columns 1.5 to 29 % apart, cosine 0.958, 17 to 24 evaluations; at 1e-10 the base point 532 / 584 evaluations
  and every nudged set 176 to 263, about 7 times the cold default's, and still 1.4 to 15 % apart, cosine 0.989
  (the CPU columns are at the default tolerance): warm fails the gate and is dearer than cold.
  Stay cold: warm-starting level 2 is no speed lever.
- Judged on following SOMA, never on landmark distances; `fit._frozen` is never edited to follow the tree's calibration.
- Test: `test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py` (a toy worker, any Python with numpy and scipy).
