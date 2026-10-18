# score/dashboard/films/

The film script (CONTEXT.md): `__init__.py`'s docstring has the format and the render hook; `script.py` the cut types,
their defaults, the clock and the checks; `media.py` what exists per place (films, hero, 3D copy, layers, step
pictures); `render.py` the render items. The pages are `pages/films.py`, `templates/pages/film*.html` and
`static/pages/film.js` (the editor and the three.js preview), `film.css`.

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
- Tests: `score/dashboard/tests/films_test.py` (the fixture environment, temp homes).
