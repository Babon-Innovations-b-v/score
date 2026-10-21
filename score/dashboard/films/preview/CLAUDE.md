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
  from library surfaces in the score_lib cache, rooms from their locked concepts. A missing surface or bed refuses.
- Chromium: `npx -p playwright@1.62.1` (viewer_look.py's pin), its libraries on `LD_LIBRARY_PATH` where the machine
  lacks them. Tests: `../../tests/films_test.py` (the join's clock, the setting's scale; no browser).
