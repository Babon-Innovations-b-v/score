# score/dashboard/films/

The film script (CONTEXT.md): `__init__.py`'s docstring has the format and the render hook; `script.py` the cut types,
their defaults, the clock, the checks and the lock; `default.py` an environment's default film; `media.py` what exists per place (films, hero, 3D copy, layers, step
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
  starter, changed by a commit, never by the page. No stage reads either, so no key moves.
- **The lock is the one input a stage reads** (owner, 2026-10-21: the film is a design step, after the scenes and
  before Buy, the top bar's Film). His Lock (`/film/<film>/lock/`, SyncRequest `film-lock`, applied on the store's
  machine by `pages/films.film_locked`, hosted through the sync and on the hosted home at once) saves the script as
  the editor shows it and keeps a copy in `$SCORE_DASHBOARD_HOME/films/locked/<film>.json` (`script.lock`); the
  environment-film row reads only those (`score/stages/demo_film/final.py`, the environment's `dashboard` root), so a
  lock, a changed lock or an unlock moves its key. Locked, nothing saves over it; Unlock is refused once a checkout
  since the lock bought a film row (`script.FILM_STAGES`; hosted, any checkout sent since). Buy waits for it as for a
  scene's design: while the environment has no locked script (`screens.film_waits`) the Buy screen says "film script
  not locked", `screens.now_items` leaves out every item holding a film row and the checkout refuses one.
- **Every environment opens on its default film** (owner, 2026-10-21: "just do my script as the default setup u can
  then change"): `/film/` goes to the environment's film (`script.default_name`: its script marked `"default": true`,
  environment 1's `env1_demo` starter, else `<world>-film`), built until he saves it by `default.py` from his script's
  structure filled in from the environment's own setting and scenes (the site holding the most scenes, its first
  three rooms, each body's library surface as earlier scripts drew it); never tied to one environment by name. A
  default is complete: every segment names a real scene (the zoom's rooms walked through after it), each long enough
  to read (the physics animation 12 s, `script.CUTS` defaults the same), its target its own length. The list of every
  film is `/film/all/`.
- **The page is a cockpit** (owner, 2026-10-21: "this is not at all easy to use"; the design page's panels, enlarge
  buttons and rail, `design.js`): the player (live, or the rendered free preview), under it the storyboard (a card a
  segment, its thumbnail a frame of its take in the rendered preview, else its scene's hero; drag to reorder, click to
  edit, Add segment's cut types in plain words grouped by `script.GROUPS`), the rail the lock, one cost line ("render
  EUR x, n to render, m free", its items, prices' basis and basket rows folded) and the chosen segment's fields, only
  those its cut needs. Every change saves itself (autosave, owner only, not while locked); no defaults table, no
  ledger ids or frame maths on the page.
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
