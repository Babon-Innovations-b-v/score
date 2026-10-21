# tools/props/gates/

The robust route's cheap checks, run before anything is paid for (job robust-exp, 2026-10-06): a failing check
stops its step and sends the work back one step, never forward with a flag. Bible: the robust route in
`architecture/components`.

- **The kit rooms' own gates are retired** (owner, 2026-10-21: "remove all old, all old stuff is retired"): the leak,
  envelope, placement, surface, shell, rounded-room, tube, density, door and name checks (`greybox`, `placement`,
  `surface`, `shell`, `round_room`, `tube`, `density`, `doors`, `names`) judged the old kit layouts (data/kit) and
  route.py's kit room run, which went with the old concepts. A scene's shell is laid from its locked plan
  (`score/stages/earth_seed/design_shell.py`).
- **Real meshes, never boxes.** `room.py` places every kit piece's own model exactly as `HubKit` does (its model
  file, its fit into its laid box, its turn); `model.py` and the visual check (`score/stages/complete/visual`) read it.
- `model.py` (G5): watertight, pieces, proportion spread on the sides the shape class can be judged on, thinnest wall.
- trimesh with embree (`embreex`, `rtree` in the prop environment). Every run goes under
  `systemd-run --user --scope -q -p MemoryMax=16G`.
- Checks: `gates_test.py` (hands itself to the prop environment).
