# score/stages/people/

The people stage (#5, experimental; bible `architecture/experimental`): people made like every prop (owner,
2026-10-11). Environment rows of environment 1's table, `__init__.py`'s docstring has them; each look is a take of
`data/people/surfaces.json` with its `spec` and `outfit`.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Run rows by name only**: `.venv/bin/python -m score run world1 --stage people-look --detach` (it drives the
  line, the LOOKED bodies and their dress). Check `ps` first that no other run is on the same rows.
- **The clothing is the finish route's, unchanged** (`line.py`; the owner, 2026-10-20: people are models like any
  other): the route's makes and judges (views, list, split, parts) and the framework's paint, the inputs handed over
  under the route's and the surface stage's names (`renamed.py`, a module with no imports of this package, so the paid
  rows' code version is the surface stage's modules and that one). Never edit the surface stage for people; its data
  is `data/people/surfaces.json`, its library place `people` in `data/definitions/place.json`. **A named gap until
  the consolidation pass (#26):** the looks are no place's, so the route runs here as environment rows of its own
  (`people-route-*`, `people-parts`, `people-paint`) rather than the places' own rows; the shared shapes-first loop
  takes them over once it can make a model no place owns.
- **A body is the maker's** (`tools/characters/maker/prop_person.py` build, settle, checks; its parts its own priced
  row, `people-look-parts-<look>`, #21), worked in its candidate folder and copied into the row's output
  (`../people_bodies/bodies.py`). The body rows live in a package of their own, `people_bodies` (with clips.py and far.py): this package imports the
  surface stage, so here a surface edit re-keyed every body (2026-10-13). The maker's and people tools' folders are
  declared files: they run by path, so a code change there re-makes the bodies.
- **Gates measure, unknown blocks**: joins, tucks (5 mm), cloth through cloth (the shipped body's count per clip),
  rigid (1.2x), body through cloth (per part, no clip frame deeper than 3 mm more often than the bind: the 3 mm is
  the settle's cloth thickness, `bodycloth.MARGIN_MM`), outline (outline.py) and likeness (the props' gate on the
  body, `score/stages/props/likeness.py`), triangles. Never loosen one to pass; fix the method (the clips' clearance,
  the settle) and measure again.
- **The dress is the paint's library surfaces, nothing else** (`dress.py`): colour, roughness and metalness from the
  library surface; the face print keeps its picture. Tests: `people_test.py`.
- **The concept decides the clothes** (owner, 2026-10-13): a place `data/people/colours.json` names wears its
  concept's colour, the library surface its cast record's words name (within dE 32 of the measured torso; lightness
  never chooses, the concepts are dim and warm-lit), on every fabric surface but a print, through a dress row of its
  own, `people-dress-<look>-in-<place>`, which that place's characters layer reads. A colour with no surface that
  near is reported, never added to the library here (a library edit re-keys every place's paint).
- **Belts are cloth** (owner, 2026-10-13): rigid means helmets, boots, visors and tools; a belt and its buckle ride
  the shell with the clothing and are no rigid part in any gate.
