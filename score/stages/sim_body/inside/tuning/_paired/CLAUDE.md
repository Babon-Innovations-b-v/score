# score/stages/sim_body/inside/tuning/_paired/

Level 1's step report and noise floor (#70; numpy only). A step is judged on a FIXED case set: every case named in
the split, tuning and check bodies apart; a case a scoring could not fit is that scoring's failure, counted, never
dropped from the set. `floor` is the same parameter point scored twice in fresh processes (all 147 cases), each
measure's 95th percentile of |paired difference|; `verdict` calls a measure better or worse only past it. `scales`
gives level 1's residual units (SCALES in `../__init__.py`) from that floor once it is measured; until then SCALES
stays the hand-set one. The reported measures stay the honest thresholded ones (frozen harness measure); level 1
tunes their smooth forms.
