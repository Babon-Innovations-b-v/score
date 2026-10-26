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
- **Run rows by name only**: `.venv/bin/python -m score run world1 --place people --stage people-look-<look> --object <look>-s1 --detach` (one look: the loop narrowed to its take, then its body, dress and page; name every look's page and leave out `--object` for all, and add `--stage people-clips`; it drives the
  line, every full body the designs name and their dress). Check `ps` first that no other run is on the same rows.
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
  proportions (the rig sizes the body). **The line holds the looks the locked designs map** (`data/people/rows.json`,
  `../people_rows.py`, #26): each look's size and bake entry the metres of the person row that maps it, written by
  `python -m score.stages.people_rows`; one body a look (owner, 2026-10-22): rows are grouped into looks by what
  they are and wear (`people_rows.look_of`: `astronaut-made`, `worker_jumpsuit-made`, a crowd's `crowd-made`; pose
  and colour vary a look through its clip and dress, a named person or the player is `<place>_<row>-made`), the
  outfit `made` the route's made body and face (`route_head.FACE`; `drawn` is the owner's open choice there, never
  what a row asks for), each look with its maker spec written from its largest standing row (`data/people/specs/`, generated, never
  edited by hand: who by its words, the build by its metres, face, hair and clothes as drawn in its concept) and its
  take on the line, so every design's person can be made with no hand-written character file. **Each line row is drawn from the person that maps it** (`people_rows.drawn_from`, #26): its view the
  mapping place's kept concept, its box SAM 3's in that concept's reading (`grounded`), the line's inventory
  approved by those locks (recorded as "the creator's pick", which the Pixal3D batch takes), and no close-up named, so
  `closeup@people` draws it (Pro, `stage.PERSON`) and `pixal@people` makes its take (`<look>-s1`): the whole line,
  bodies included, is one `score run`, with no take row first. **Accepted gaps today:** a hair finish fails the
  paint's colour gate by name (the old people-paint left hair out, `hair.py`, deleted with it).
- **A body is the maker's** (`tools/characters/maker/prop_person.py` build, route, checks; its parts its own priced
  row, `people-look-parts-<look>`, #21), worked in its candidate folder and copied into the row's output
  (`../people_bodies/bodies.py`). The body rows live in a package of their own, `people_bodies` (with clips.py and far.py): this package imports the
  surface stage, so here a surface edit re-keyed every body (2026-10-13). The maker's and people tools' folders are
  declared files: they run by path, so a code change there re-makes the bodies.
- **Gates measure, unknown blocks**: joins, tucks (5 mm), cloth through cloth (the shipped body's count per clip),
  rigid (1.2x), body through cloth (per part, no clip frame deeper than 3 mm more often than the bind: the 3 mm is
  the cloth's thickness, `bodycloth.MARGIN_MM`), outline (outline.py) and likeness (the props' gate on the
  body, `score/stages/props/likeness.py`), triangles (the route's body as drawn). Never loosen one to pass; fix the
  method (the clips' clearance, the route) and measure again.
- **The dress is the loop's library surfaces, baked, nothing else** (`dress.py`, paid; owner 2026-10-23: "this didnt
  use our prop pipeline and materials"): each part takes the library surface the loop's bake painted on the take's
  outer surface (never a face Pixal3D grew inside it), a garment split where its paint changes, a hard part, the skin,
  the hair and each far-body part one surface; no picture's finish, the close-up's face print included. An island of
  one surface under the props' `patchy.STRAY_ISLAND` of the outfit joins the surface round it (`without_strays`: the
  take's unseen paint left the astronaut's collar, wrists and lower back in jagged dark blotches, 2026-10-23), and the
  `strays` gate holds the dressed body's stray area within `patchy.STRAY_LIMIT`. Then
  `baked_body.py` bakes those surfaces onto the body itself with the library's own bake (`inside/bake_body.py`,
  `Atlas.bake_self`, on the bake's L4 through `blender_cloud.py`, the people palette's wear and dirt) and checks it
  with `bake_check.py`'s measures; `dressed` fails a material in flat factors with no baked maps, `baked` the
  check's faults. A person's variant (`-v<n>`, `varied`) wears other surfaces of the same families from the people
  line's scene library (surface-library@people, `library_surfaces`), never the repo's method library, which holds none. skel_usd carries the three maps and `score:surface` into the asset. Tests:
  `test_looks_dressed_from_the_library_and_judged_by_measure.py`.
- **The concept decides the clothes** (owner, 2026-10-13), per person row and from the design alone
  (`../people_clothes.py`, each row's `dress` in `data/people/rows.json`, written by the people rows' refresh): of the
  people place's library fabrics, those whose name shares a word with the row's name as read, the nearest by dE to
  the row's torso measured on the locked concept, used only within dE 32 (lightness never chooses on its own, the
  concepts are dim and warm-lit). A person of that row wears it on every fabric surface but a print through the dress
  row `people-dress-<look>-in-<surface>`; a row naming no fabric, or none that near, wears its look's own paint (the
  plain row, its look already drawn from that person). No hand-kept list of places or colours. A colour with no
  surface that near is reported in the row's `why`, never added to the library here (a library edit re-keys every
  place's paint).
- **Belts are cloth** (owner, 2026-10-13): rigid means helmets, boots, visors and tools; a belt and its buckle ride
  the shell with the clothing and are no rigid part in any gate.
