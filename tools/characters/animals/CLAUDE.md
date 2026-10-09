# tools/characters/animals/

The character maker's animal route (job characters-full, 2026-10-09): one animal from its spec
(`data/characters/makes/<name>.json`, `"kind": "animal"`) to a rigged, skinned, animated glTF, its
UsdSkel asset, its lighter copies and its review frames. Entry: `route.make(spec, folder, who,
dry_run)`, called by `../maker/make.py`; its docstring lists the steps.

- **Nothing runs here but plain Python.** The mesh (Pixal3D, `../../props/cloud/batch.py
  --characters`), the rig (UniRig, `../../props/cloud/unirig.py`) and every Blender script
  (`blender_rig.py`, `blender_review.py`) run on rented machines; the Blender pair share one held
  machine (`blender_cloud.Machine`). The batch's finish of the raw model still runs on this PC as
  every batch's does (`pixal.py --finish-only`, about a minute a model): moving it up needs the
  byte match `../../props/cloud/CLAUDE.md` asks for.
- **The body decides the rig.** A fish gets a spine made in code (`spine.py`, `rig_fish.py`): a
  chain of bones along its level long axis, each vertex split between two bones by where it lies
  along it, so its fins follow the spine. A four-legged animal gets UniRig's skeleton and skin, and
  its parts are found from the skeleton's shape (`legs.py`): the legs are the four chains that end
  lowest, the head's and the tail's the chains that end furthest forward and back.
- **Clips are made, not captured.** Swim, turn and hover for a fish; idle, walk and sit for a
  four-legged animal, the legs on inverse kinematics baked into plain bone keys. Every clip is a loop
  at 30 frames a second with the travel taken off: the game moves the node (`rig.json` gives the
  walk's speed).
- **The file faces glTF's +z**, as the people do, a fish centred on its node and a land animal
  standing on it, at the spec's `length_m` from snout to tail.
- **Look at the frames before claiming a clip works.** The review frames are rendered from the
  exported file read back, on a floor with a grid that shows a sliding foot.
- `animals_test.py` checks the plain-Python pieces (spine weights, leg chains, the foot's path).
  Everything a make writes lives in `~/.farm-factory-motion/made/<name>/`; nothing generated is
  committed.
