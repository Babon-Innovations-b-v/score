# score/stages/sim_body/inside/evaluation/

Level 1's runner (#70): `__init__.py` runs levels 2 and 3 on every body of a side (tuning, or the held-out check)
side by side, one `_case.py` process per SOMA body in Newton's Python (at most `MOST`, systemd-run MemoryMax=6G, two
threads, only while `FREE_GB` is available), and reads back each clip's honest measures (`_measure`: joint error,
rotation error on `fit._frozen`, the frozen copy of main's calibration, bones outside SOMA's skin by region through
`fit._skin`: the stage's record and level 1's score share that one code). `tuning.whole` calls it each evaluation; `level1.py <run dir> --python <Newton's Python>` is the thin
command. The check bodies are scored every few iterations and at the end, never used to choose; `accepted` is the
held-out rule (within 10 % of the tuning bodies).

- Judged on following SOMA, never on landmark distances; `fit._frozen` is never edited to follow the tree's calibration.
- Test: `test_every_evaluation_runs_every_tuning_body_and_the_check_never_chooses.py` (a toy worker, any Python with numpy and scipy).
