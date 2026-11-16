# score/dashboard/films/preview/

`scenes.py`: a setting animation's and a scale zoom's scene worked out from what exists (the setting's bodies on their
orbits through `score/review/overhead.py`, the environment plan's sites, blocks and skies, each body's face colour);
`score/stages/light/sky.py` reads its `kelvin_colour`. The free preview's recorder (`make.py`, `recorder.mjs`,
`scene.js`) that played these scenes in the cockpit went with the cockpit (owner, 2026-11-16).

- **What a scene shows comes from data**: colours of the bodies and grounds from each body's face as its
  `body-face-<body>` row made it (never a library name; a plain colour of its own while the row has not run, the
  leg's tag saying `WAITING`). A scale zoom arrives at each place in daylight (#51, `scenes.arrival`): the first hour
  from its site's scene time when its sun stands `LIT_DEGREES` up; a segment's `time` (ISO) overrides it.
- Test: `../test_a_film_is_timed_checked_and_priced_from_its_script.py` (the setting's scale, the arrival, the face).
