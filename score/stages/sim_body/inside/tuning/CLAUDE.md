# score/stages/sim_body/inside/tuning/

Level 1 of the fit (#70; CONTEXT.md "landmark set"; pure numpy, its test runs in the score venv): one tuning round of
the landmark set's links and trusts from fits (levels 2 and 3) on the tuning bodies. `tuned` pools each landmark's
offset (its level-2 move plus its mean leftover, in its body's frame) over the bodies, left and right together
(`paired`, so mirrored pairs stay mirrored); `stepped` moves a link only where the pooled mean clears 2 standard
errors, a joint-defining landmark only across its bone, shrunk by a 10 mm prior and clamped to 20 mm from its
anatomical start; `trusts` gives 1 / (MAD + 5 mm) at the set's old total; `rewritten` writes the tuned rows into
`landmarks/_table.py`.

- A round is judged by the next fit's follow score (joint error, bone-group turns, bones inside SOMA's skin) on the
  tuning bodies and then on the check bodies left out, never by the leftovers it pulls on. A round that does not
  improve the check score, or widens the tuning-check gap by more than 0.05, is not kept.
- The bone's long axis is taken as the body's own y (`LONG_AXIS`, OpenSim's convention for MyoFullBody's long
  bones); not measured per body.
- The harness that runs a round (fits, measures, `round.py`) lives outside the repository with the #70 workflow.
