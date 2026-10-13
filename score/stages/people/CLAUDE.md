# score/stages/people/

The people stage (#5, experimental; bible `architecture/experimental`): people made like every prop (owner,
2026-10-11). World rows of world 1's table, `__init__.py`'s docstring has them; each look is a take of
`data/people/surfaces.json` with its `spec` and `outfit`.

- **Run rows by name only**: `.venv/bin/python -m score run world1 --stage people-look --detach` (it drives the
  line, the LOOKED bodies and their dress). Check `ps` first that no other run is on the same rows.
- **The clothing is the surface stage's, unchanged** (`line.py`): its makes and judges, the inputs handed over under
  the surface stage's names (`renamed.py`, a module with no imports of this package, so the paid rows' code version
  is the surface stage's modules and that one). Never edit the surface stage for people; its data is
  `data/people/surfaces.json`, its library place `people` in `data/definitions/place.json`.
- **A body is the maker's** (`tools/characters/maker/prop_person.py` build, settle, checks; parts first when a take
  has none), worked in its candidate folder and copied into the row's output (`../people_bodies/bodies.py`). The
  body rows live in a package of their own, `people_bodies` (with clips.py and far.py): this package imports the
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
