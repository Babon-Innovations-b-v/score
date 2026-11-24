# tools/props/bench/judge/

The prop benchmark's picture judge (#184, PRD #159): the owner's way of judging (pictures beat numbers; a regression
on the previous round counts) made a check. `__init__.py` is the way in (its docstring has the interface);
`__main__.py` judges pictures named by hand (calibration, a round against pictures no run keeps as a look).

- **One Claude ask on the subscription** (score/adapters/models/claude_code, EUR 0) per look: NVIDIA's render, the
  made look and, when given, the previous round's look, shown alike (on the close-up's backdrop, one crop round every
  object drawn, SHOWN px). Its answer is kept by the hash of the model and the body (claude_code.CACHE), so the same
  pictures are never asked twice.
- **The kinds of fault are the owner's** (KINDS: edges, specks, holes, lumps, colour, text, shape, parts), each with a
  verdict clean, slight or fault. The bars live in measures.BARS (group `picture`): no kind at fault, no regression,
  a drawn look. A bar or a kind is never loosened to pass a made look; a fault the owner sees and the judge missed is
  fixed in the ask, with a row in the test.
- **Calibration**: NVIDIA's input render against itself and against a re-render (the look's 1080 px, fewer samples)
  must pass; the numbers are on #184.
- **Wired into** `bench.py measure` (run/): branch B's measures carry `picture` when its look is kept; `--previous
  <run>` names the round whose looks it is held to.
- Test: `test_a_look_passes_only_with_no_fault_and_no_regression.py`, a stand-in for Claude, small RGBA pictures.
