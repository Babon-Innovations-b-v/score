# score/dashboard/films/preview/

A film script's free preview, rendered end to end on the store's machine (`make.py`'s docstring has the steps; the
film script's rules are `../CLAUDE.md`'s).

- **Store's machine only.** It starts Chromium, ffmpeg and a hosted-mode cockpit of its own; the hosted process never
  imports it (it reads numpy through `score/review/overhead.py`).
- **Its own clock.** Every frame is drawn at its time on the segment's clock (`recorder.mjs`, `scene.js`
  `draw(seconds)`), transitions and animations switched off on the recorded pages, so a take comes out the same each
  time; nothing reads the wall clock.
- **Moves like a camera, shows only what is there** (owner, 2026-10-21: no generative video, "make the animations very
  profesional looking"): a scale zoom's legs move on through their dissolves (`scene.js` `travel`, resting only where
  the shot ends), a screen take's page closes in slowly (`recorder.mjs` `DRIFT`), cards rise in on their clock
  (`film.js` `drawWords`), one grade on every segment (`make.py` `GRADE`) and the bed started on its beats
  (`beat_offset`; a hum has none). Nothing is added that the page or the scene does not hold.
- **The takes are kept** (`<film>-takes/<NNN>.mp4` beside the preview, not exported): the environment-film row cuts
  its recorded segments from them, while the record says they were made from the locked segment.
- **No spend, ever.** The recorder aborts every request that is not a GET and refuses a take that clicks a button that
  spends (`../takes.py`); the cockpit it records is a loopback one over a state export, never the hosted site.
- **What a scene shows comes from data**: the setting's bodies through `overhead.orbit_position` (sizes and moons'
  orbits enlarged as `pages/setting_picture.py` draws them), sites, blocks and skies from the environment plan, colours
  of the bodies and grounds from each body's face as its `body-face-<body>` row made it (the state's `body_faces`, never a library name; a plain colour of its own while the row has not run, the leg's tag saying `WAITING`), rooms from their locked concepts. The bed is the sound stage's (the state's `sound_beds`: the first place the film
  shows with an accepted `sound@<place>` bed, else the first with one), never a library name; while none is made the
  film joins with silence and its record says `waiting on the sound bed`.
  A scale zoom arrives at each place in daylight (#51, `scenes.arrival`): the first hour from its site's scene time
  when its sun stands `LIT_DEGREES` up, its sky worked out again there through `overhead.seen`; a segment's `time`
  (ISO) overrides it for its own place.
- Node.js 20 or newer (the pin's `engines`; older stops with "Please update your version of Node.js"): the
  conductor's `tools/cloud/conductor/boot.sh` installs `NODE_VERSION`, a PC brings its own.
- Chromium: `npx -p playwright@1.62.1` (viewer_look.py's pin), its libraries on `LD_LIBRARY_PATH` where the machine
  lacks them. Tests: `../test_a_film_is_timed_checked_and_priced_from_its_script.py` (the join's clock, the setting's scale; no browser).
