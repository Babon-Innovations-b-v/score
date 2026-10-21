# score/stages/people_takes/

The people's take rows (#5, experimental): `people-take-<look>`, a new look's close-ups and Pixal3D take, made by the
prop route's closeup and mesh (`tools/characters/maker/prop_person.py`) inside the runner, which clears its rent.
Looks are `data/people/takes.json` entries (spec and outfit).

- **Its own package on purpose**: the people package is hashed into every body row's code version, so a take row
  there would re-key every body. Keep it apart.
- **A take joins the people line by data, after its row is accepted**: its take into `data/surfaces/people.json`
  (and its bake's `models`), its look as a row of the people layer into `data/props/people.json` (its close-up the
  take's `input.png`) and `data/inventory/people.json`, so the shared loop finishes it (#41); its look into
  `data/people/bodies.json`, its cast name into the place's cast record. Still a model made before the loop (the
  loop's Pixal3D batch takes only an approved scene's rows): an accepted gap of #41.
- Gates measure, unknown blocks: `close-ups` (one with the arms apart), `take` (a kept take whose files, its raw
  and finished model and its close-up, are in the output, `take/`, so the store keeps them: #26, the work folder
  was lost on 2026-10-19). Tests: `people_takes_test.py`.
