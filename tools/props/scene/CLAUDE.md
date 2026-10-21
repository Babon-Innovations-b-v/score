# tools/props/scene/

A room composed from a target picture, an experiment (2026-10-02, #121's interiors): draw the
room (`target.py`), cut each object out by name with SAM 3 (`cutout.py`), measure the picture in
metres with MoGe-2 (`depth.py`), redraw each cut-out whole (`redraw.py`) and build each through the
cloud batch (`../cloud/batch.py`). `marble.py` sends a target to World Labs Marble and brings back
its room (`depth-marble.npz`, in `depth.py`'s form).
Its paid calls (`generate`, `paint`) refuse outside a cleared run (`score.adapters.compute.require_cleared`).

Outside, one viewpoint and one Marble world is the plan, never walked: even marble-1.1-plus turned
the base into houses (2026-10-02). `cutout.py --picture` and `redraw.py --picture` take a level view
in place of the target; `marble.py --ledger` adds every paid call to a ledger file. `closeups.py` plans close-ups of every
inventory item out of a world's own 3D (its splats and collider, free from `marble.py`): a front, two
three-quarter and an above camera per item from its 3D position and size, checked against the
collider, each carrying the item's and its neighbours' prompt points; `closeups_gpu.py` renders them
from the splats and cuts each item out, resolved against its neighbours, on a card through
`../cloud/closeups_cloud.py` (the object maker's input, page A's close-ups). The workflow these tools
serve: skill `make-scene`, bible "How a scene is designed".

- **The scene workflow of 2026-10-04 (#121): look pick, then pages A, B and C.** `place.py`
  gives a scene's style from its design alone (owner, 2026-10-21: no per-place prose decides a picture): the
  environment concept's style line and the look of the scene's locked concept, keyed by the scene id the design store
  holds, read once per lock by one Gemini 3.1 Pro call on that picture inside the cleared run that draws (priced at the
  measured ask, kept under `{home}/design/looks/`); every painting (`marble.py --place`), redraw (`redraw.py --style`,
  worked out here by `cloud/scene.py`) and klein close-up (`cloud/pictures.py`) is worded from it alone; only a
  look-pick take is worded by hand (`marble.py --look --text`). `data/definitions/place.json`'s `style.text` is read
  by none of these (the concept draws still read it, `score/review/concepts.py`). `inventory.py` is the shape of
  a scene inventory and the shell hash; `placed.py` reads what every layer places in a scene
  today (layout, the room's scene, main.tscn's game nodes, the machines, the kit's wall fill, the
  opening's constants, an outdoor place's made layout `data/kit/<place>.json`: the old station, the wreck; a walkway
  tube's kit layout, `kit_layout`); `match.py` holds migrated scenes to their inventory and prints the rest
  as a to-do list (`python3 tools/props/scene/match.py`). `box_check.py` holds every inventory's boxes to its
  concept: inside the picture, not the whole picture for a single thing, spread over it rather than in one corner,
  **No box is typed** (2026-10-09: the camp's typed boxes made close-ups of the wrong things): `partition.py` cuts
  the concept into tiles, SAM 2.1 proposes a mask per element (`../cloud/segment.py`), and the agent only maps each
  proposal to a row, drops it with a reason or names a new element; a row's box is its proposals' box (`box_from`).
  `box_check.gate()` runs before any close-up (`../closeup/stage.py`) and in the completion gate (`../../usd/complete.py`
  "boxes"); unknown blocks like a fail. Also
  with `--masks`, each box measured against SAM 3's masks of its row's words (`box_masks.py` on a card through
  `../cloud/box_masks_cloud.py`; `--tighten` sets a loose box to the thing inside it), and, with `--judge`, the boxes
  SAM 3 cannot measure shown to the open judge beside its row's words (majority of three); a row the
  concept does not show has `"box": null` and says why in `"unseen"`. `duplicates.py` fails when two places'
  made rows name one real-world object and are made from different takes, or one is about to be made again, unless a row
  says why in `own_model` or names the row it reuses in `reuse` (the owner, 2026-10-09: no duplicates; reuse first). `cloud/scene.py` and `cloud/batch.py`
  refuse to run without an approved inventory; `cloud/scene.py` also without the scene's concept locked.
- Everything a run makes goes under `WORK/scene/<room>/` (`~/.farm-factory-props/work/scene/`);
  target pictures, masks, worlds and layouts never go in the repo.
- **No model runs on this PC** (owner, 2026-10-03: "My GPU is only for game tests; do all model
  stuff in batches in the cloud"). `target.py`, `cutout.py`, `depth.py` and `redraw.py` refuse
  here (`../local_models.py`) and run on one rented card through `../cloud/scene.py <plan.json>`,
  which brings the room's folder back and sends the kept objects to `../cloud/batch.py` as one
  batch. `closeups_gpu.py` refuses here too and runs through `../cloud/closeups_cloud.py`.
  `marble.py`, `closeups.py`
  and the Godot shots stay here: no model in them. `FARM_LOCAL_MODELS=1` is an emergency switch
  for the owner to throw, never a session.
- Every step that uses the card does so inside `card.claimed()`; Pixal3D only through `pixal.py`.
- SAM 3's weights are gated on Hugging Face; `SAM3_WEIGHTS` names a copy when the account has no
  access. MoGe-2 and its helper library are copies outside the repo put on the path, never
  installed into the prop environment, whose own older `utils3d` is left from the retired TRELLIS
  mesher.
- Marble's API key is read at run time as the secret `worldlabs-api-key` (`secret_store.secret()`: an
  environment variable, else the cloud backend's secret store), never printed or written anywhere.
  A world costs about 1,580 credits; its high-quality mesh export another 3,500. Marble worlds
  are a layout reference only: shipped models stay our own.
- A cut-out under `cutsize.MIN_CUT_SIDE` source pixels on its box's short side never feeds the
  redraw (the owner, 2026-10-02: "the low-res ones look shit"). `redraw.py` draws such an object
  afresh as a close-up when the target was drawn here, else leaves it off the build list;
  `redraw/report.json` lists every object with its cut-out size and the way it took.
- `inventory_test.py` checks the inventory's shape, the refusals and the place file;
  `match_test.py` runs the match over the real tree on every change to game/, sim/ or data/.
- `cutsize_test.py` is the gate's check of the cut-out limit.
- The Godot tools run on the card through `bash tools/godot/run.sh shots <scene> -- ...`, one game
  window at a time. Marble's API takes four worlds at once; `call()` waits out a 429.
- **The per-place kit scripts are retired** (owner, 2026-10-21: "remove all old, all old stuff is retired"): the
  hub's, the rounded rooms', the bay's, the camp's, the ship rooms' and the walkway tube's kit layouts (`*_kit.py`)
  went with data/kit; every scene's shell is laid from its locked plan by its earth seed
  (`score/stages/earth_seed/design_shell.py`), and every reader of an old kit reads the design's kit there.
- **A kit's lamps come from the design** (owner, 2026-10-21: no per-scene list decides what a scene gets): `lamps.py`
  gives a lamp its light (the scene record's kit shell reads it, `score/stages/scene_record/kit_shell.py`): a row whose row kind glows (its reading `noun`,
  `score/stages/row_kinds.py`) lit by the library's lamp for its mount (`data/library/lamps.json`: ceiling, wall or
  stands; reach from its laid pieces' height, the starting strength the light sweep then measures, shadows by mount).
  A reading's row anchored `on:<row>` is mounted as that row is (the library's `mount_words` in its noun, else its
  own anchor, else what it rests on in turn), so a caller passes the inventory's rows to `light_of`. No row carries typed `light` numbers and no builder keeps a lamp list.
- `ship_floor.py <out>` is the ship's floor plan inside its 46 m hull (the owner's loop, 2026-10-19: the outside's
  plan split into the inside's rooms): data/definitions/ship_floor.json names each room's span, side, floors and doors
  and carries its own hull (`hull`: plan v7's stations at 46 m, their section, the nose spike and the side ring,
  written in when data/definitions/ship.json was retired, 2026-10-21); every size and section is measured from that
  hull, people keep their size
  (0.9 x 2.0 m doors, a 2.6 m ceiling), and its faults (overlaps, a floor under the keel, a door to nowhere, a room
  naming no place of data/definitions/place.json) exit 1.
  It draws the plan (`ship-floor.png`) and, with `--views`, each room's concept request in concept_views.json's form.
  `ship_floor_test.py` checks it.
