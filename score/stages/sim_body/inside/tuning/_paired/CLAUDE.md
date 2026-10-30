# score/stages/sim_body/inside/tuning/_paired/

Level 1's step report and noise floor (#70; numpy only). A step is judged on a FIXED case set: every case named in
the split, tuning and check bodies apart; a case a scoring could not fit is that scoring's failure, counted, never
dropped from the set. `floor` is the same parameter point scored twice in fresh processes (all 147 cases), each
measure's 95th percentile of |paired difference|; `verdict` calls a measure better or worse only past it. `scales`
gives level 1's residual units (SCALES in `../__init__.py`) from that floor once it is measured; until then SCALES
stays the hand-set one. The reported measures stay the honest thresholded ones (frozen harness measure); level 1
tunes their smooth forms.
`flattened` names a case's honest measures from its m.json (each joint's and group's median over frames, each region's
share outside and the share over all, the means over joints and groups), `scored` reads a scoring folder (a case with
no m.json is that scoring's failure), `stepped` is one step's JSON report (per side: cases, paired, failures, per
measure median, p5, p95 of the paired change and its verdict given a floor). `../../evaluation/level1.py` writes one to
steps.jsonl at each check against the check before; its tuning side is the latest evaluation of the tuning bodies.
