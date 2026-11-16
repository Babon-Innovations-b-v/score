# score/review/relation_solver/

Crowded plans parted: `parted(plan, inventory)` parts the floor things standing in each other with IsaacLab-Arena's
relation solver ported to numpy (`_solver.py`); score_lib's room_layout algorithm. The plan writer's pass that called
it went with the per-picture chain (#128); no score module calls the package now.

Rules:

- **Credit and licence stay.** `_solver.py` is a modified port of isaac-sim/IsaacLab-Arena (Apache-2.0, commit
  38b200cd): keep its copyright header, its "Modified for SCORE" note (extend it when you change the port) and
  `LICENSE` beside it.
- **numpy, not torch.** Arena's torch (about 200 MB; the conductor has 2 cores and about 15 GB disk free) is not
  pulled in for one loop of Adam: no new dependency. Gradients are the losses' own, a tie split evenly as torch's.
- **Free, CPU, seeded.** Same plan in, same plan out (`SEED`); no call, no machine, no spend.
- **Soft spots, hard checks.** Plan spots are soft targets, so the solver may push a thing far; its answer is kept
  only when `plan_checks.checked` finds fewer overlaps and no more gaps of any other kind. What still overlaps stays a
  gap. Boxes only: a turned (polygon) footprint is solved as its box, so a diagonal crowd may stay unparted (the
  habitat's turned furniture in its kept plan of 2026-10-21: 5 pairs left).
- **In no stage's code key, but `_solver.py`.** Nothing imports the package; never import it from
  `plans.py` or a stage (an edit there re-keys about 74 paid rows: `python -m
  score.stages.moved origin/main`). `assembly/fitting.parted_spots` imports `_solver` alone, by its full module name
  (`from score.review.relation_solver._solver import ...`), so only `_solver.py` (numpy only) is in the assembly's,
  light's and settle's keys (#72): an edit of `_solver.py` re-keys those rows; `__init__.py` re-keys none.
