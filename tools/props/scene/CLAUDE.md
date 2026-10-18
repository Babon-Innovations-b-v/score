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
  reads a place's style text from `data/definitions/place.json`, and every painting
  (`marble.py --place`), redraw (`redraw.py --place`) and cloud run is worded from it alone; only
  a look-pick take is worded by hand (`marble.py --look --text`). `inventory.py` is the shape of
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
  refuse to run without an approved inventory and its place's style text.
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
- `earth_kit.py` lays the prologue's kit rooms (the flat with its balcony, the stairwell) from EarthSite's own numbers
  (`earth_kit_test.py` reads them in the script), as the route's input; `placed.py` reads their installed layouts.
- `cutsize_test.py` is the gate's check of the cut-out limit.
- The Godot tools run on the card through `bash tools/godot/run.sh shots <scene> -- ...`, one game
  window at a time. Marble's API takes four worlds at once; `call()` waits out a 429.
- **Kit layouts for the route** (`route.py`'s input): `hub_kit.py` for the hub's twelve walls, `room_kit.py <room>` for
  a rounded module room from its inventory's `room.layout` (the shell's own outline, its dome's rings, the floor's
  cross and corner fans, door spots, the rows' spots; the habitat and the airlock, modules batch one), and
  `tube_kit.py` for one bay and one end of a walkway tube, which the game lays along any tube (`TubeKit`).
  `room_kit_test.py` checks them. `greenhouse_kit.py` is room_kit's room with what only the greenhouse has (world 1's
  place job, 2026-10-07): a glass dome on a frame of ribs instead of plates, the floor's rises (SteppedFloor's dais,
  steps and ledges) surfaced, the robot station's pieces on PlotField's spots and the grow-light gantry over the plot;
  `greenhouse_kit_test.py` reads the game's own numbers (SteppedFloor, PlotField, main.tscn) and holds it to them.
- `ship_kit.py <room> <out.json>` lays a ship room's kit (the ship as a world 1 place, 2026-10-14; the bridge first)
  from its plan alone (`w`, `d`, the ceiling in its height words, its doors, its `kit` block: the nose's cut corners,
  the windows' sill, head and pillar) and its inventory's spots: walls in two bands of plain plates round the wedge
  outline, a doorway left clear, the cut corners and the front glazed, the floor and ceiling in grids with a triangle in
  each cut corner. A tapered room (the kit block's `front_wide`, `ceiling_front`, `glazed: roof`, `windows_from`:
  the cockpit) narrows straight to its front under a sloping ceiling, its upper wall plates reaching the ceiling over
  each plate, its floor and roof in rows with tapering slivers at the sides, its windows lights in the sloping roof.
  Shell plates take the sorter's plain names; a room's name is one word (`bridge`), as the route's
  kinds are `<room>_<own>`. `ship_kit_test.py` checks it on a bridge-shaped room.
- `camp_kit.py` lays the expedition camp habitat's kit on Mars (data/kit/camp.json via route.py) from the camp scripts' own numbers; `camp_kit_test.py` reads them back. `camp_shots.tscn` draws the habitat from cameras in its own frame (run with `--mars`, so the game's own check stays on Mars while it shoots).
