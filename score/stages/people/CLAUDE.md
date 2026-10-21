# score/stages/people/

The people stage (#5, experimental; bible `architecture/experimental`): people made like every prop (owner,
2026-10-11). Environment rows of environment 1's table after the shared loop, `__init__.py`'s docstring has them;
each look is a take of `data/surfaces/people.json` with its `spec` and `outfit`.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Run rows by name only**: `.venv/bin/python -m score run world1 --stage people-look --detach` (it drives the
  line, the LOOKED bodies and their dress). Check `ps` first that no other run is on the same rows.
- **People are made by the shared loop** (`../shapes_first`, #41; the owner, 2026-10-20: people are models like any
  other): every look is a row of the people layer in the hand-in record `data/props/people.json` (its rows
  `data/inventory/people.json`, its surface data `data/surfaces/people.json`, its library place `people` in
  `data/definitions/place.json`), run on the line `people`, which no place owns (`align.NO_PLACE`: held to no plan,
  and assembly, complete and the library hand-over do not apply there). The loop's close-up, Pixal3D, finish route,
  bake and likeness make it; no side route of the people's own. Run it by name: `python -m score run world1 --place
  people --detach` (it is no place of the environment's, so a whole run leaves it out). The people layer's after-step,
  `people-made@people` (`loop.py`), hands each look on (its take, its finishes, its labelled take, and its Pixal3D
  files as pixal@people's takes.json names them, `takes/<take>/`) or names its gap; each look's parts, body and
  dress rows read it (beside, on the line) and are Blocked on the look's gap before anything is bought. The body
  rows build from the take the store keeps (`bodies.laid_take`), never the work folder alone (#26). Never edit the surface stage for people. **A person's close-up is the people layer's own**
  (`tools/props/closeup/stage.PERSON`, chosen for every row whose `layer` is `people`, on this line and in a designed
  place's hand-in alike): one person, or one member of a crowd row, front on in the rig's A-pose, never the concept's
  pose; its gate is `check.person_faults` (framed, arms clear of the body: Pixal3D fused Nev's), not a box's
  proportions (the rig sizes the body). **The line holds the looks the picked designs map** (`data/people/rows.json`,
  `../people_rows.py`, #26): each look's size and bake entry the metres of the person row that maps it, written by
  `python -m score.stages.people_rows`; a person no line look fits is a named new look there until it has a spec and
  a take row. **Accepted gaps today:** a hair finish fails the paint's colour
  gate by name (the old people-paint left hair out, `hair.py`, deleted with it); `people-take-<look>` still makes
  each look's close-up and its Pixal3D take before the loop (its pose and limbs-apart retries).
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
- **The dress is the loop's library surfaces, nothing else** (`dress.py`): colour, roughness and metalness from the
  library surface the loop's bake painted; the face print keeps its picture. Tests: `people_test.py`.
- **The concept decides the clothes** (owner, 2026-10-13): a place `data/people/colours.json` names wears its
  concept's colour, the library surface its cast record's words name (within dE 32 of the measured torso; lightness
  never chooses, the concepts are dim and warm-lit), on every fabric surface but a print, through a dress row of its
  own, `people-dress-<look>-in-<place>`, which that place's characters layer reads. A colour with no surface that
  near is reported, never added to the library here (a library edit re-keys every place's paint).
- **Belts are cloth** (owner, 2026-10-13): rigid means helmets, boots, visors and tools; a belt and its buckle ride
  the shell with the clothing and are no rigid part in any gate.
