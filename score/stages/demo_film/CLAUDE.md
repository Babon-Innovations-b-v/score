# score/stages/demo_film/

The demo-film and demo-film-extra rows (experimental, 2026-10-14): demo K9's walk-through films of a place, from its
final stage once it passes complete or fails it only on its accepted gaps (`gapped`, the overseer 2026-10-15), with its
own sound; paid and cleared by the runner like any paid row.
`__init__.py`'s docstring has the make, the output and the gate.

- **The films are the locked film scripts'** (`films`, `films_of`): each walk-through or hero still segment's `shows`
  names its place and, optionally, its `film` (another film of the place: the ship's hull through the hangar, film
  `hull`), its `camera`, `then`, `start` and `leave_out`. The row's key is the locked scripts that show the place
  (`script <name>`), so a lock moves only those places' films. A segment naming no `film` is the place's own film
  (demo-film@place); one naming a film is demo-film-extra@place, all of that place's other films in one node. The old
  per-place records (`data/definitions/demo_films`) were the old concepts' and are retired (owner, 2026-10-21: all old
  stuff is retired).
- **The camera** is the segment's, else the place's scene record's first (`first_camera`: the plan's first view, as the
  scene record writes them); demo.py plans from the stage's own record (`scene.json`). The path starts there; the first frame is kept as `concept.png`, demo K8's still (no separate
  render); a standing shot starts 5 degrees off the camera's aim and a walk's start may move up to 1.5 m to stand clear,
  which views.json records. A shot whose camera stands no clear spot falls back to the record's next clear camera
  (demo.spare_cameras), and a film whose kept shots show less than the longest walk-through showing it (`walk_seconds`)
  fails before its frames are bought (`refuse_short`).
- **The film is the place's own**: the neighbours output where the place shows others, else its assembly, never a seed;
  two shots of 4 s each (SHOTS, the finish plan of 2026-10-18: a place on screen about 7 s unbroken), 1280x720 at 24
  frames a second (192 frames), the look only (no ink): a 9 s film with its title card, which the length gate holds
  to (planned_seconds for the shots its views hold). The second shot is the record's `then` (a record camera's name
  or a spot of its own), else the record camera standing furthest from the first. A spot of its own is `eye` and
  `aim`, or `across` the record's floor as shares of it (the ship's rooms: the spot keeps its place when a room is
  built at another size), with `fov` and `stand` (a small room's shot stands and turns rather than walking into a
  wall). The planner keeps clear of people and moving things (camera_paths), glides at one speed between eased ends and
  rounds its corners (demo.py); every frame carries the camera's motion blur towards the next (`motion_blurred`, drawn by
  `blender/film_frames.py`, its overlay: a 180 degree shutter, shorter where the picture moves fast, none standing still; no
  mesh deformation blurred). About EUR 3.2 a place likely and 3.5 high (twice a measured 96-frame film's 1.6 and 1.75).
- **A film is one batch** (#21, owner 2026-10-20, replacing #20's paid preview): everything before the yes is free,
  the local preview (`tools/review/film_preview.py`) and the forecast (`python -m score.stages.demo_film forecast
  <place>`: frames, cards, card minutes and euros likely and high, from a scan of the accepted stage for fog,
  volumes and glass, priced high at `FOG_FRAME_MINUTES` a frame). His lock of a script on the Film step is the yes
  (`final`): a place no locked script shows has no node. A film whose forecast's high passes the euros its run was
  cleared at is Blocked: a dearer film is a new ask at the forecast's price.
  The runner clears the row at its films' forecast high (`own_forecast`, `extra_forecast` as graph.Stage.forecast, from
  the node's inputs), the one figure the make holds each film to (fault 2026-10-25: cleared at the row's EUR 3.50, or
  at measured runs of 96-frame films, a fogged or a 192-frame film Blocked itself). Never lock for him.
  The final is rendered once at 1280x720 over the cards `capacity.machines_for` sizes (no fixed card count), each
  job's deadline its frames at the forecast's high; a job that dies or passes it is a gap, never run again inside
  the batch, and filming it again is a new batch and a new yes. The gate holds each film to the size its views.json
  planned.
- **The gate measures**: film_checks' video checks (size, sound, black, frozen, length) and the clearance on every
  frame (meshes, people and moving things at the frame's own moment), and the owner's faults of 2026-10-18 (#28, `shots.py`):
  every shot at least `SECONDS`, a frame showing a person where the stage holds people (and a stage that holds
  none where the place's design stands people fails, #26: `cast_people` over `data/people/rows.json`), and nothing seen moving in a
  shot without a sound under it. Whether a film reads well is the creator's call. One card class (`CLASSES`
  gpu-24gb): a dearer class taken when it is out of stock would be a fallback chain inside the batch.
- **The environment's own film** (`final.py`, the environment-film row, #28): one environment node, free (a local
  ffmpeg cut), reading every film script the creator locked on the cockpit's Film step
  (`$SCORE_DASHBOARD_HOME/films/locked/<film>.json`, the environment's `dashboard` root; a new lock moves its key)
  and, beside it, the place films they show (demo-film, demo-film-extra), so the runner plans and prices it with
  them. Blocked while none is locked (the lock is his yes; the starters in `data/films/` are read by nothing here
  but needs.py's film gaps); every segment names its `seconds` and is a cut it makes (title, text, walk-through, hero still),
  a screen take, physics animation or scale zoom cut from the free preview's take of that very segment
  (`<film>-takes/` beside the preview; one recorded from another script is Blocked until the preview is rendered
  again), else the node is Blocked naming each segment (exploded, isolate, layer cuts, step cards, before and after
  need frames no row makes yet). Cards and lower thirds are in the cockpit's type (`lettering.py`), the films are
  matched in exposure, the whole graded as the preview is (`GRADE`), cards and takes over the script's bed. The whole film's sound is moved by one gain to `TARGET_LUFS`; its gate holds the pace
  (`PLACE_SECONDS` a place, `SHOT_SECONDS` a walk-through) and the loudness. Its needs (`needs.py`) are the gaps
  check's film gaps: a film a script shows that no locked script shows waits on his lock.
  A locked script that peels no place whose design shows people (design_layers.has_layer, every kept design an input)
  is Blocked naming each (`plan_faults`, owner 2026-10-27), so it cannot drift from the designs.
- **A layer peel** (`peel.py`, the script's `body-peel` cut, CONTEXT.md "layer peel"; owner 2026-10-27) is drawn free on
  this machine's card by `blender/body_peel.py` in Blender `-b` (no display needed): every person of the cast clothed
  (its dressed body posed by the sim body's clip, its rest fitted to the clip rig's bind), as its bare SOMA mesh and as
  its sim body (whatever geometry the sim body layer holds under the person's SimBody, bones, boxes or muscles with
  their own colours, imported by Blender with its time samples and shown at the record's frames, placed as the sim runs;
  `--build` its person's own build; each foot's recorded push an arrow up from the ground under it, `METRES_PER_NEWTON`
  long), over the scene's ground (`--ground`), joined by a wipe at each third. `--close` follows one walker alone,
  `close_walker`'s rule (the most relief in scene-clips' record). A shot never outlasts the sim body record. No row
  makes peel frames yet, so the environment film names the cut as one it cannot cut; making it a row (inside the
  assembled scene, on its own camera) is a change of its own.
- **Stills come from the films.** K5, K6 and K8 take frames of the places' films (a film starts at its
  segment's `start`, else the stage's start); the demo-stills row, which rendered a view no film showed, was retired
  on 2026-10-22 (it had no definitions and so no node).
- Run: `python -m score run world1 --place <place> --stage demo-film --detach` (a film the creator said yes to starts by
  itself once its place passes complete, or fails it only on its accepted gaps, in any environment run). Test: `test_a_film_shows_its_locked_script_within_its_forecast.py` (no Blender, no spend; one small local ffmpeg cut).
