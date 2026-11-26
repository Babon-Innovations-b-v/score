# tools/characters/accessories/

What a person of the people line wears beside its sewn clothes (#228, under PRD #223): shoes and a belt first,
trinkets and jewellery next. `__init__.py`'s docstring has how each is made; the garments run
(`python -m tools.characters.garments <outfit.json>`) wears them from its outfit file's `accessories`.

- **From the library.** Every finish is a score_lib surface named in the outfit file (`accessories.shoes.finish`, or
  `.upper` and `.sole` for a made shoe; `accessories.belt.strap` and `.buckle`). Shoes are a library model where the
  outfit names one (`accessories.shoes.model`: the adopted knit runner `model/sneaker_knit_runner@1`, Shopify's
  Materials Variants Shoe under CC BY 4.0, with three colourway surfaces), fitted to each foot by `shoe_model.py`
  and held to the same checks; the library holds no belt model, so the belt is fitted on the body as the garments
  are.
- **Carried by the body's own joints**, never posed by hand: a shoe point carries the skin weights of the foot
  points nearest it, the belt rides the draped waistband and the hips' turn.
- **The foot is tucked into a library shoe** (`shoe_model.tucked`, #223 photoreal round 1: the Achilles stood out
  through the runner's leaning heel counter in a torn V): the skin under the shoe's own top (its heel counter read
  leaning, `leaning`) moved in from its walls and into its cavity, carried by its skinning; the check reads that skin
  out through the walls (`top_out`) beside the cavity's (`out_of`). `shoe_model.shell` is the shoe the drape meets.
- **A fault fails the garments run** after its pictures (`faults`: a sole through or never on the floor, the foot
  out through its shoe, a belt off its waistband). Limits are never loosened to pass.
- Tests: `test_shoes_and_a_belt_stay_on_the_body_that_wears_them.py` (a toy body of ellipsoid feet, leg and hip
  tubes walking forward, a toy flared skirt, a toy shoe model (an open ellipsoid cup); no Newton or Blender).
