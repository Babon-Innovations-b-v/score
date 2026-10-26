# score/review/relation_solver/

The plan fixes' fallback for crowded plans: `parted(plan, inventory)` parts the floor things the free fixes
(`plan_fixes.nudged`) left in each other, with IsaacLab-Arena's relation solver ported to numpy (`_solver.py`).
Called by `plans_pass.settled_again` after `plan_fixes.settled`; `plans_pass.unsettled` re-fixes a plan it would part,
only where its plan row stands unaccepted (`plans_pass.parting`), a free one before the keep (`parted_first`).

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
- **In no stage's code key.** Only `plans_pass` imports it; never import it from `plan_fixes.py`, `plans.py`,
  `plan_writing.py` or a stage (an edit there re-keys about 74 paid rows: `python -m score.stages.moved origin/main`).
