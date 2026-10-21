# score/dashboard/films/

The film script (CONTEXT.md): `__init__.py`'s docstring has the format and the render hook; `script.py` the cut types,
their defaults, the clock and the checks; `media.py` what exists per place (films, hero, 3D copy, layers, step
pictures); `render.py` the render items. The pages are `pages/films.py`, `templates/pages/film*.html` and
`static/pages/film.js` (the editor and the three.js preview), `film.css`. `takes.py` is a screen take's steps and
its refusal (CONTEXT.md "screen take"). `preview/` (store's machine only, never imported hosted) renders a script's
free preview end to end (`python -m score.dashboard film-preview <film> [--export DIR]`, `make.py`'s docstring): the
takes recorded in headless Chromium on a hosted-mode cockpit of its own over a state export, signed in as the owner by
the proxy header (`recorder.mjs`), the setting animation and scale zoom drawn by `scene.js` from `scenes.py` (the
setting's physics through `score/review/overhead.py`, the environment plan's sites and blocks, the locked concepts,
colours from library surfaces), the other cuts through the FILM page's own player, joined by ffmpeg on the script's
clock with its library sound bed; out to `$SCORE_DASHBOARD_HOME/films/previews/<film>.mp4|.json`, which the FILM page
plays (`/film-preview/<film>.mp4`, api/routes.py, with ranges) and the export carries (`films/`).

Rules:

- **Plain files, both modes.** Nothing here imports `score.stages`, `score.store` or `tools.*`: the hosted process
  reads it too. The format is plain JSON so showcase.py and the demo-film rows read it without importing this package.
- **The cockpit writes only its home** (`$SCORE_DASHBOARD_HOME/films/<film>.json`); `data/films/<film>.json` is the
  starter, changed by a commit, never by the page. No stage reads either, so no key moves; a stage that reads one
  later declares it on purpose.
- **Free preview, priced renders.** The preview uses only what exists (the web copies, accepted films, step
  pictures). A render item is priced only from measured runs (`render.MEASURED`, film frames per place in
  `render.FILM_FRAME_EUROS`, read from the cloud ledgers; stills as look frames); a kind never rendered on a card reads "not measured
  yet". The basket takes only rows that exist (demo-film@<place>); nothing here plans, launches or calls a cloud.
- **A take never spends.** Every request but a GET is aborted, and a click on a button that posts a form, names a
  price or carries a spend word (`takes.SPEND_WORDS`) refuses the whole preview; the script check refuses one named so
  before anything runs. A page that is not as the owner sees it (a locked place has no Redraw) is said in the
  segment's `why`, never staged.
- **What waits is marked.** A segment showing a stand-in (a blockout for a finished place, a concept for a finished
  room, a waiting inventory) names what it waits on in `waiting`, and says so on screen (a scale zoom leg's `tag`).
- Tests: `score/dashboard/tests/films_test.py` (the fixture environment, temp homes).
