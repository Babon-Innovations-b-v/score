# tools/props/bench/judge/

The prop benchmark's picture judge (#184, PRD #159): the owner's way of judging (pictures beat numbers; a regression
on the previous round counts) made a check. `__init__.py` is the way in (its docstring has the interface);
`__main__.py` judges pictures named by hand (calibration, a round against pictures no run keeps as a look).

- **One Claude ask on the subscription** (score/adapters/models/claude_code, EUR 0) per look: NVIDIA's render, the
  made look and, when given, the previous round's look, shown alike (on the close-up's backdrop, one crop round every
  object drawn, SHOWN px). Its answer is kept by the hash of the model and the body (claude_code.CACHE), so the same
  pictures are never asked twice.
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
- **Wired into** `bench.py measure` (run/): branch B's measures carry `picture` when its look is kept; `--previous
  <run>` names the round whose looks it is held to. A pictured case (the 2099 cockpit cases, no NVIDIA model) is held
  to its close-up, the ask naming it so (`pictured`, ORIGINALS); the render's words stay byte for byte, so kept
  answers hold.
- Test: `test_a_look_passes_only_with_no_fault_and_no_regression.py`, a stand-in for Claude, small RGBA pictures.
