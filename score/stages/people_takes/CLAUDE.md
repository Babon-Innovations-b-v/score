# score/stages/people_takes/

The people's take rows (#5, experimental): `people-take-<look>`, a new look's close-ups and Pixal3D take, made by the
prop route's closeup and mesh (`tools/characters/maker/prop_person.py`) inside the runner, which clears its rent.
Looks are `data/people/takes.json` entries (spec and outfit).

- **Its own package on purpose**: the people package is hashed into every body row's code version, so a take row
  there would re-key every body. Keep it apart.
- **A take joins the people line by data, after its row is accepted**: its take into `data/people/surfaces.json`
  (the line paints it), its look into `data/people/bodies.json`, its cast name into the place's cast record.
- Gates measure, unknown blocks: `close-ups` (one with the arms apart), `take` (a kept take on disk). Tests:
  `people_takes_test.py`.
