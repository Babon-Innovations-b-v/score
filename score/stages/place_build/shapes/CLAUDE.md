# score/stages/place_build/shapes/

A place_build scene's made shapes that read wrong, each told for a remake (#149; the 2099 session's play-runs,
2026-11-20: "lumpy seats, sausage pipes"; the owner's rule of 2026-10-18 keeps a picture-made model's geometry, so a
shape that does not read as its thing is remade, never kept or repainted). `__init__.py`'s docstring has the rules
and the measures they were set on; ready/ reports them in ready.json's `shapes`, and the place is ready only with
none.

- **Judged from the model file**, in its own frame, never from a mark the agent sets; only a made shape (a picture's
  take, Pixal3D, TRELLIS.2, or code built from a concept crop). A library kit or a scan is what it is.
- **What a thing is comes from its entry's id** (PIPE_WORDS, HARD_WORDS). A seat is not held to the flat faces of a
  hard thing: upholstery is curved.
- **A measure is set on kept places, never loosened to pass one**: a threshold moves only with the library's own
  pieces and a made one that reads right measured both sides of it, written in the docstring.
- Test: `test_a_made_shape_that_reads_wrong_is_told_for_a_remake.py` (a temp library, no Blender).
