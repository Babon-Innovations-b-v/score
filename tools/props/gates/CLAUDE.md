# tools/props/gates/

The robust route's cheap checks, run before anything is paid for (job robust-exp, 2026-10-06): a failing check
stops its step and sends the work back one step, never forward with a flag. Bible: the robust route in
`architecture/components`.

- **Real meshes, never boxes.** `room.py` places every kit piece's own model exactly as `HubKit` does; the hub kit's
  99.6% box coverage sat beside visible holes because it measured laid boxes.
- `greybox.py` (G2): leak rays out through a sector of walls and roof (real openings excluded), straight rays
  through each real opening, pieces poking out of the shell's outer skin, the sector's budget.
  `placement.py` (G6): pieces standing in front of a real opening. `surface.py` (G6): every hung piece flush on its
  host plane, turned to it and inside its face (the hub's trays lay radially across the lattice, which the
  envelope test cannot see). `model.py` (G5): watertight, pieces, proportion spread on the sides the shape class
  can be judged on, thinnest wall.
- `round_room.py` (modules batch one, 2026-10-07): the same leak, envelope and doorway checks for a rounded room
  (the habitat, the airlock) from its inventory's numbers, and solid furniture crowding; `--boxes` runs it on the
  laid boxes before any model is made. `tube.py`: a walkway tube's bay, leaks round its section outside the glass
  bands and pieces out of the hull.
- `doors.py` (the owner, 2026-10-07, on the Mars concepts: a partition with a door and an open gap beside it): every
  door a kit layout lays must stand in a wall or partition that fully parts its two sides. Read as a walk on a 5 cm
  grid at walking height over the wall-like pieces, every door and every listed doorway (`doorways`) shut: no path
  from one side of a door to the other. A screen without a door is not judged. Run on the kit layout before any
  spend; a door with a way round fails the place.
- `density.py` (the owner, 2026-10-08, on the lab: "lost a massive amount of detail"): the inventory's
  `concept_elements` list every element the picked concept shows, crop by crop, each a row (or a part of one) or
  dropped with a reason; the kit layout must lay each row as often as the concept shows it. Run before any spend; the
  built room is then drawn from the concept's own camera beside the concept on the place's page.
- `names.py` (the coordinator, 2026-10-08: the camp's rod lamp baked as `pendant_lamp` overwrote the workshop's
  lamp record and broke main; the stairwell's code `junction_box` nearly routed the lab's generated one to code): an
  own name means one thing in every room. Fails a code-built model named as another thing, an own name made on one route here
  and the other in another installed room (`data/kit/*.json`), and a builder defined twice. `route.py install` runs
  it first and stops on a fault.
- trimesh with embree (`embreex`, `rtree` in the prop environment); a whole room takes about 2 s. Every run goes
  under `systemd-run --user --scope -q -p MemoryMax=16G`.
- Checks: `gates_test.py` (hands itself to the prop environment).
