# tools/characters/accessories/

What a person of the people line wears beside its sewn clothes (#228, under PRD #223): shoes and a belt first,
trinkets and jewellery next. `__init__.py`'s docstring has how each is made; the garments run
(`python -m tools.characters.garments <outfit.json>`) wears them from its outfit file's `accessories`.

- **From the library.** Every finish is a score_lib surface named in the outfit file (`accessories.shoes.upper` and
  `.sole`, `accessories.belt.strap` and `.buckle`). The library holds no shoe or belt model, so the shapes are fitted
  on the body as the garments are; a library shoe or jewellery model, when one is adopted, replaces the fitted shape
  and keeps the checks.
- **Carried by the body's own joints**, never posed by hand: a shoe point carries the skin weights of the foot
  points nearest it, the belt rides the draped waistband and the hips' turn.
- **A fault fails the garments run** after its pictures (`faults`: a sole through or never on the floor, the foot
  out through its shoe, a belt off its waistband). Limits are never loosened to pass.
- Tests: `test_shoes_and_a_belt_stay_on_the_body_that_wears_them.py` (a toy body of ellipsoid feet, leg and hip
  tubes walking forward, a toy flared skirt; no Newton or Blender).
