# tools/props/scene/

A room composed from a target picture, an experiment (2026-10-02, #121's interiors): draw the
room (`target.py`), cut each object out by name with SAM 3 (`cutout.py`), measure the picture in
metres with MoGe-2 (`depth.py`) and the room and its objects' boxes (`boxes.py`), redraw each
cut-out whole (`redraw.py`), build each through `../pixal.py`, read the models' sizes and seen
sides (`models.py`), place them by rules (`layout.py`) and draw the result from the target's own
camera in the game's look (`stage.tscn`). `marble.py` sends a target to World Labs Marble and
brings back its room as a second measure of the same masks (`boxes.py --depth depth-marble.npz`).

Round two goes the other way, from our rooms to Marble: `depth_pano.tscn` renders a 360° depth
cube at eye height in the real starter base, on the kit's own stepped floors (`--pano-kit` takes
each kind's room in the kit yard, `--pano-scene` a scene of its own such as the ready room),
`pano.py` folds it into the depth panorama Marble paints (`marble.py paint`, then
`generate --pano`), and `align.py` lays each world back on its spot on the seat. One world per
room and per tube junction indoors; outside, one viewpoint and one world as the plan, never
walked: even marble-1.1-plus turned the base into houses (2026-10-02). `planview.py` cuts level
views out of a spot's painted (or depth) panorama for `cutout.py --picture` and `redraw.py
--picture`, and `room_shots.tscn` draws the game from those same cameras to lay beside them;
`marble.py --ledger` adds every paid call to a ledger file. The workflow these tools
serve: skill `make-scene`, bible "How a scene is designed".

- `depth_pano.tscn --pano-ship` takes the ship's rooms instead (`ShipCabin.ROOMS`, #70), with the
  rest of the game put away so its windows look out on nothing; `--pano-colour` takes the same six
  ways in the game's look, to lay beside each plan from the plan's own camera.
- Everything a run makes goes under `WORK/scene/<room>/` (`~/.farm-factory-props/work/scene/`);
  target pictures, masks, worlds and layouts never go in the repo.
- Every step that uses the card does so inside `card.claimed()`; Pixal3D only through `pixal.py`.
- SAM 3's weights are gated on Hugging Face; `SAM3_WEIGHTS` names a copy when the account has no
  access. MoGe-2 and its helper library are copies outside the repo put on the path, never
  installed into the prop environment, whose own `utils3d` is TRELLIS's.
- Marble's API key is read at run time from `~/.config/worldlabs/api_key`, never written anywhere.
  A world costs about 1,580 credits; its high-quality mesh export another 3,500. Marble worlds
  are a layout reference only: shipped models stay our own.
- The stage is not the game's habitat scene, which the module kit owns; its shell is a stand-in
  built from the measured section.
- A cut-out under `cutsize.MIN_CUT_SIDE` source pixels on its box's short side never feeds the
  redraw (the owner, 2026-10-02: "the low-res ones look shit"). `redraw.py` draws such an object
  afresh as a close-up when the target was drawn here, else leaves it off the build list;
  `redraw/report.json` lists every object with its cut-out size and the way it took.
- `layout_test.py` is the gate's check of the placing rules, plain python; `cutsize_test.py` of
  the cut-out limit; `pano_test.py` checks
  the folding and the placing of worlds, `planview_test.py` the plan views' cameras (hands itself to the prop environment for numpy).
- The Godot tools run on the card through `bash tools/godot/run.sh shots <scene> -- ...`, one game
  window at a time. Marble's API takes four worlds at once; `call()` waits out a 429.
