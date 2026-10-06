# tools/props/gates/

The robust route's cheap checks, run before anything is paid for (job robust-exp, 2026-10-06): a failing check
stops its step and sends the work back one step, never forward with a flag. Bible: the robust route in
`architecture/components`.

- **Real meshes, never boxes.** `room.py` places every kit piece's own model exactly as `HubKit` does; the hub kit's
  99.6% box coverage sat beside visible holes because it measured laid boxes.
- `greybox.py` (G2): leak rays out through a sector of walls and roof (real openings excluded), straight rays
  through each real opening, pieces poking out of the shell's outer skin, the sector's budget.
  `placement.py` (G6): pieces standing in front of a real opening. `model.py` (G5): watertight, pieces,
  proportion spread on the sides the shape class can be judged on, thinnest wall.
- trimesh with embree (`embreex`, `rtree` in the prop environment); a whole room takes about 2 s. Every run goes
  under `systemd-run --user --scope -q -p MemoryMax=16G`.
- Checks: `gates_test.py` (hands itself to the prop environment).
