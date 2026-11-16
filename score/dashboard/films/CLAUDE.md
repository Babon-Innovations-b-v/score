# score/dashboard/films/

The film script (CONTEXT.md): `__init__.py`'s docstring has the format and the render hook; `script.py` the cut types,
their defaults, the clock, the checks and the lock; `default.py` an environment's default film; `media.py` what exists
per place; `render.py` the render items; `takes.py` a screen take's steps and its refusal (CONTEXT.md "screen take");
`preview/scenes.py` a setting animation's and scale zoom's scene. The FILM pages, their editor and the free preview's
recorder went with the cockpit (owner, 2026-11-16); his Lock is a chat decision (`decide-yes lock-film`,
`pages/films.film_locked`).

Rules:

- **Plain files.** Nothing here imports `score.stages`, `score.store` or `tools.*`. The format is plain JSON so showcase.py and the demo-film rows read it without importing this package.
- **Only the dashboard's home is written** (`$SCORE_DASHBOARD_HOME/films/<film>.json`); `data/films/<film>.json` is the
  starter, changed by a commit. No stage reads either, so no key moves.
- **The lock is the one input a stage reads** (owner, 2026-10-21: the film is a design step, after the scenes and
  before Buy). His Lock (his chat `lock-film`, request kind `film-lock`, applied by `pages/films.film_locked`) saves
  the script as his yes named it and keeps a copy in `$SCORE_DASHBOARD_HOME/films/locked/<film>.json` (`script.lock`); the
  environment-film row reads only those (`score/stages/demo_film/final.py`, the environment's `dashboard` root), so a
  lock, a changed lock or an unlock moves its key. Locked, nothing saves over it; Unlock is refused once a checkout
  since the lock bought a film row (`script.FILM_STAGES`). Buy waits for it as for a
  scene's design: while the environment has no locked script (`screens.film_waits`, "film script not locked"), `screens.now_items` leaves out every item holding a film row and the checkout refuses one.
- **Every environment opens on its default film** (owner, 2026-10-21: "just do my script as the default setup u can
  then change"): the environment's film is (`script.default_name`: its starter marked `"default": true`,
  environment 1's `env1_demo`, even where a saved copy lost the mark; else a saved script so marked; else
  `<world>-film`), built until he saves it by `default.py` from his script's
  structure filled in from the environment's own setting and scenes (the site holding the most scenes, its first
  three rooms, each body's library surface as earlier scripts drew it), then the whole environment (owner,
  2026-10-21: "its needs to show all of env 1"): every other top scene, the rest of its body's first, then body by
  body in the environment plan's order, one scale zoom each going on from where the last ended (over the ground from
  the site before, `from_place`; else out from its world, across the setting, `from_body`, the one leg that may go
  back up, and down again), the plan's metres and the true distance its sky gives in the captions, the concept in the
  corner, round it from outside and into its first three rooms; never tied to one environment by name. Every zoom
  is followed by a walk through its scene (not a shell, no place of its own) and every scene it holds, parent before
  child (owner, 2026-10-24: "scale zoom after scale zoom and no walkthroughs in between"), so two zooms follow each
  other only where a site has nothing to walk; the env1_demo starter the same. Last, the sim bodies part
  (`default.sim_bodies`, owner 2026-10-27): a layer peel of every shown scene whose design has people
  (`data/people/rows.json`) and whose cast gives sim bodies (a cast of a crowd alone has none, the sim body row's
  rule: such a scene, the Square, gets a place peel instead), and a close-up peel after it where one walks, Earth's first (the clips' motion is true
  there), every other carrying `LOW_GRAVITY_NOTE` (env1_demo's from the kept designs' people rows,
  `design_layers`; the environment film refuses a lock missing one), then a place peel of every other scene it walks
  through (`default.place_peel`, owner 2026-11-05: "every scene needs the peel"; asked whether that meant adding
  people or peeling the place itself: "2"): the same view finished, its bare models and its physics bodies, so every
  walked scene has one peel; env1_demo's made by the same `sim_bodies`, and the environment film refuses a lock
  missing one. Its words and shots follow the design, never
  the tree (audit, 2026-11-04): a walk is said Inside or Outside by its scene record's `inside` (`WorldState.
  scene_inside`), the rooms leg the same; a shell with a plan of its own (the Base) is walked like any top scene; a
  scene whose plan names its eye ("balcony eye 10.6 m", `default.designed_eye`) is a still from there, never walked;
  site metres from the environment plan as it stands. `script.design_faults` (from `default.design_of` of the facts
  now) checks a script for each of these, and his Lock of an environment's script is refused while one stands, so a
  script that froze data since moved is locked again only once it says what the design says. A default is complete: every segment names a real scene, each long enough
  to read (the physics animation 12 s, `script.CUTS` defaults the same), its target its own length.
- **Priced renders.** A render item is priced only from measured runs (`render.MEASURED`, film frames per place in
  `render.FILM_FRAME_EUROS`, read from the cloud ledgers; stills as look frames); a kind never rendered reads "not measured
  yet". The basket takes only rows that exist (demo-film@<place>); nothing here plans, launches or calls a cloud.
- **A take never spends.** Every request but a GET is aborted, and a click on a button that posts a form, names a
  price or carries a spend word (`takes.SPEND_WORDS`) is refused; the script check refuses one named so before
  anything runs.
- **What waits is marked.** A segment showing a stand-in (a plan's masses for a finished place, a concept for a finished
  room, a waiting inventory) names what it waits on in `waiting`, (a scale zoom leg's `tag`).
- Tests: `films/test_a_film_is_timed_checked_and_priced_from_its_script.py` (the fixture environment, temp homes).
