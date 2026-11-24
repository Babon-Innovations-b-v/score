# tools/props/bench/judge/

The prop benchmark's picture judge (#184, PRD #159): the owner's way of judging (pictures beat numbers; a regression
on the previous round counts) made a check. `__init__.py` is the way in (its docstring has the interface);
`__main__.py` judges pictures named by hand (calibration, a round against pictures no run keeps as a look).

- **Claude asks on the subscription** (score/adapters/models/claude_code, EUR 0) per look, shown alike (on the
  close-up's backdrop, one crop round every object drawn, SHOWN px): the faults ask (NVIDIA's model drawn by the same
  look, bench.nvidia_look_step, and the made look) and, when a previous look is given, the regression ask (COMPARE) twice, the two looks as A and B in both
  orders; regressed only when both choose the previous look. Its answer is kept by the hash of the model and the body (claude_code.CACHE), so the same
  pictures are never asked twice.
- **NVIDIA's model is drawn by the same look** (#159, ORIGINALS["render"]): the same renderer, camera, light and
  backdrop, so the ask holds a part drawn lighter, darker, duller or shaded otherwise as the model's, never the
  light's (beside NVIDIA's own close-up the owner could not tell the drawing from the pipeline, 2026-11-24). A
  pictured case's close-up is still another light (ORIGINALS["closeup"]).
- **Colour strength and value are the part's** (STRENGTH, #198): a whole part drawn more saturated, darker or
  lighter than the original shows it is a `colour` fault even where its hue is right.
- **The kinds of fault are the owner's** (KINDS: edges, specks, holes, lumps, colour, text, shape, parts), each with a
  verdict clean, slight or fault. The bars live in measures.BARS (group `picture`): no kind at fault, no regression,
  a drawn look. A bar or a kind is never loosened to pass a made look; a fault the owner sees and the judge missed is
  fixed in the ask, with a row in the test. Chrome or mirror metal drawn flat dull grey is a `colour` fault, not light
  (`CHROME`, #200).
- **A pictured case's close-up is judged as a cut-out of its own** (#159: tc5r's attitude panel, flight screen and
  pilot console were torn cut-outs and their copied ragged outlines were booked as make faults): the ask (CUTOUT)
  lists the cut-out's faults first (`cutout_faults`, verdict `cutout`), and a made model only following them is not
  at fault for it; PICTURED_BARS holds `picture.cutout` at 0, so a torn close-up fails as the input's fault. The
  render's ask is unchanged by it.
- **Calibration**: NVIDIA's input render against itself and against a re-render (the look's 1080 px, fewer samples)
  must pass; the numbers are on #184.
- **The regression is judged apart and in one light** (#205: in one ask with the faults, "worse in any way you would
  point at, even where better in others" and tc5r's looks drawn under an older light marked 26 of 30 tc6 looks
  regressed where the eye found 4): the previous round's made model is drawn again by today's look
  (bench.redrawn_look), so only the models differ, and held to the made look by which is closer to the original as a
  whole. On tc6's 24 objects with a previous look: 21 regressed by the old ask, 8 by this one, 19 agreeing with the eye
  lines and the other 5 (coffee station, hammer, hand drill, drill b01, heat gun) worse on a look at the redrawn pair;
  a model against its own redraw never regressed (10 of 10), the granite chair and the garbled sign regressed.
  Today's look draws the previous finish too, so a fix in the look's or the bake's own drawing is credited to both.
- **Wired into** `bench.py measure` (run/): branch B's measures carry `picture` when its look is kept; `--previous
  <run>` names the round whose looks it is held to. A pictured case (the 2099 cockpit cases, no NVIDIA model) is held
  to its close-up, the ask naming it so (`pictured`, ORIGINALS); the render's words stay byte for byte, so kept
  answers hold.
- Test: `test_a_look_passes_only_with_no_fault_and_no_regression.py`, a stand-in for Claude, small RGBA pictures.
