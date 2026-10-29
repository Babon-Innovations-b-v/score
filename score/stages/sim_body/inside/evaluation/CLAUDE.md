# score/stages/sim_body/inside/evaluation/

Level 1's runner (#70): `__init__.py` runs levels 2 and 3 on every body of a side (tuning, or the held-out check)
side by side, one `_case.py` process per SOMA body in Newton's Python (at most `MOST`, systemd-run MemoryMax=6G, two
threads, only while `FREE_GB` is available), and reads back each clip's honest measures (`_measure`: joint error,
rotation error on `fit._frozen`, the frozen copy of main's calibration, bones outside SOMA's skin by region through
`fit._skin`: the stage's record and level 1's score share that one code), each clip's written twice: `measures.json`
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
- Judged on following SOMA, never on landmark distances; `fit._frozen` is never edited to follow the tree's calibration.
- Test: `test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py` (a toy worker, any Python with numpy and scipy).
