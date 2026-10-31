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
command. The check bodies are scored every `--every` iterations (3 unless given) and at the end, never used to choose; `accepted` is the
held-out rule (within 10 % of the tuning bodies). Each check after the first also goes to steps.jsonl as `tuning._paired.stepped` against the check before (per-case
paired changes, tuning and check bodies apart, verdicts once the run dir has floor.json).

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
  for bit, angles too). Across sets too since 2026-10-30 (`TARGETS`, keyed by `targets_key`: the clip's rig, segments, worlds,
  held groups and the solver landmarks' faces and weights, so a landmark set makes them anew; read-only arrays,
  a write in place raises; profile: targets 4.3 s of 4 heavy sets' 68 s). Gate 2026-10-29 (tall and slim, 14 cases, the per-case card run's constants):
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
  Warm level 2 (a `--warm <tolerance>` option, deleted 2026-10-30) was measured on the 6a gate's 7 sets against the
  serial CPU columns (cold: 0.04 to 0.61 %, cosine 0.99998): at 1e-8 the columns 1.5 to 29 % apart, at 1e-10 still
  1.4 to 15 % apart with about 7 times the cold evaluations. Stay cold: warm-starting level 2 is no speed lever.
- Where a set's time goes (2026-10-31, night/gpu1/phases.txt: 4 of l1d's first Jacobian sets x tall's 7 clips, one
  `_card_sets` process beside l1d and env1): level 2's least_squares 11.3 s and polish 9.1 s, level 3's sampled frames
  7.3 s, measures and writing 4.7 s, the Newton clip builds 3.8 s, set-up 7.0 s, the clips' card batch 2.6 s; 48.9 s
  wall at ~1.3 cores, the card at 5 to 11 % but in the clips' batch. With level 2's residuals and Jacobian on the card
  (`fit/_card/_level2_wide`) and level 3's step a CUDA graph (`fit/_card/_solve`): 37.8 s (least_squares 8.5,
  polish 5.4, sampled frames 3.5); level 1's rows equal to 1e-5 (largest row 5.06; the same set in two card processes
  differs up to 1.5e-5 on tall), the three nudged columns 0.2 to 0.9 % apart, cosine 0.99996 or more. What is left on
  the host: scipy's lsmr inside least_squares and the polish's sparse solve (SuperLU), the person's file written and
  compiled per set (`sim_body.constants_set_up`), the Newton build per set (`_clip.for_fitting`), the measures.
- `_card_sets` writes and compiles a set's person's file once (since 2026-10-31; twice before, the second with the
  constants): `body_run` takes level 2's own `Fitting`, the constants laid on in place, with its group ends laid again
  (`fit.ends_relaid`), and Newton's model is built from the file without constants with the inside joints moved; the
  clips' folders hold no copy of the file. 4 centre sets x tall's 7 clips beside l1d (night/gpu2/prof c, d): set-up B
  4.3 s to 0, rows within 2.7e-5 of the two-file run (largest 5.0), the nudged columns 0.02 to 0.03 % apart.
- `measured_many` runs one `_card_sets` process a body (since 2026-10-31; one process held every body before, ~1.3
  cores, the card mostly idle, a Jacobian 37 min on l1d), at most `SET_PROCESSES` (10, every tuning body) side by side by `run_all`, a
  failed body once more; each writes its own cases into the shared out/pNNN/sNNNNN folders. Measured (night/gpu2/many,
  4 centre sets x tall, mean, slim and mid_tall's 28 cases, env1 beside it): 168.4 s in one process (3.4 cores, card
  19 % mean) against 56.1 s in four (5.3 cores, card 29 %, 5.7 GB on the card at most), every row bit for bit equal.
- `blocked(rows, weights, rest, cases, out, python, seeds_root)` (2026-10-30) runs `tuning/_adjoint/_check_columns.py`
  once per BODY side by side (since 2026-10-31; once per case before), each case's exact block (rows x every unknown)
  to out/<case>.npz: level 2 solved, built and factored once a body from all its clips, as `measured_many` solves it.
  Before, a case's block solved level 2 from that case's clip alone (`_case.prepared` lays the recordings of the
  cases it is given), so the hybrid's exact columns were not the derivative of the function the evaluations measure;
  given one case the per-body script equals the old block (tall_kimodo, 8.7e-5 of 0.106, two old runs 6.7e-5 apart);
  `level1.py --card <seeds root> --exact` hands `tuning.whole` the hybrid (`exact_stacked`: the blocks in sorted case
  order, then the prior's columns; `centre_columns` differenced). About 3 min a case serially; the 70-case timing is
  not measured yet.
- Judged on following SOMA, never on landmark distances; `fit._frozen` is never edited to follow the tree's calibration.
- Test: `test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py` (a toy worker, any Python with numpy and scipy).
