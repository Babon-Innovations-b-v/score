# tools/props/infinigen/

Infinigen (princeton-vl, BSD-3, vendored at `vendor/infinigen/`, pinned to v1.19.0) as a part of the framework:
our plan steers it, it builds a patch or a creature on a rented machine, and the game gets a light version of what
it built. Bible: `workflow/bootstrap` (the vendored copy, its licences, the runner).

- **Nothing Infinigen runs on this PC.** It was running here beside a gate and a Blender when WSL died
  (2026-10-05). `steer.py` (numpy only) writes the job here; `patch.py`, `ground.py`, `life.py` and
  `game_export.py` import `bpy` and Infinigen and run only on the machine `../cloud/infinigen.py` rents.
- **The plan steers; Infinigen fills in.** `steer.py` turns a dimensioned plan (heights, zones, marked spots,
  camera, sun) into `spec.json`. The ground's shape is the plan's (a height field, or for the Moon the
  crater element in `ground.py` meshed by Infinigen's own mesher); Infinigen's scatters are limited to the
  plan's zones; its assets stand on the plan's spots, a few variants of a kind shared as linked copies.
- **`vendor/infinigen` stays as released.** New behaviour (the crater element, the game export) lives
  here and calls into it; the GPL part (`infinigen_gpl`) is fetched on the machine, never committed.
- **The game gets models, not Infinigen's scene**: a grid ground with the full ground baked onto it, one
  close-up model a distinct mesh, and every copy's transform for a MultiMesh (`placements.json`).
  `view.tscn` draws that folder in the game's look through `run.sh shots` and writes the card's time.
- **Never cut a model to a sliver.** Bake on the full mesh first (Infinigen's `bake_object`), then collapse
  only to the close-up budget in the spec, keeping UVs; distance is lighter levels (`lod_chain`) and picture
  cards, never a 1% model up close (the owner turned those down, 2026-10-06).
- `crater_test.py` is the plain-python check (numpy, the prop environment).
