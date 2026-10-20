# score/stages/demo_film/

The demo-film and demo-film-extra rows (experimental, 2026-10-14): demo K9's walk-through films of a place, from its
final stage once it passes complete or fails it only on its accepted gaps (`gapped`, the overseer 2026-10-15), with its
own sound; paid and cleared by the runner like any paid row.
`__init__.py`'s docstring has the make, the output and the gate.

- **One record a film**, `data/definitions/demo_films/<film>.json` (`place`, `camera`, `why`), so adding a film moves no
  other film's key. `<place>.json` is the place's own film (demo-film@place); any other name is another film of its
  `place` (demo-film-extra@place, all of that place's other films in one node): the ship's hull through the hangar
  goes in as `hull.json` (place hangar, camera ship) only once the hull has landed, or it films the gap.
- **The camera** is the scene record's camera nearest the place's concept (picked by laying the concept beside every
  camera's game shot). A planned place's stage carries its own record (`scene.json` with cameras: spot-N,
  from-...-door), which demo.py plans from, so its film names that record's camera nearest the seed pick (by eye and
  aim; each record's `why` says how near). The path starts there; the first frame is kept as `concept.png`, demo K8's still (no separate
  render); a standing shot starts 5 degrees off the camera's aim and a walk's start may move up to 1.5 m to stand clear,
  which views.json records.
- **The film is the place's own**: the neighbours output where the place shows others, else its assembly, never a seed;
  two shots of 4 s each (SHOTS, the finish plan of 2026-10-18: a place on screen about 7 s unbroken), 1280x720 at 24
  frames a second (192 frames), the look only (no ink): a 9 s film with its title card, which the length gate holds
  to (planned_seconds for the shots its views hold). The second shot is the record's `then` (a record camera's name
  or a spot of its own), else the record camera standing furthest from the first. A spot of its own is `eye` and
  `aim`, or `across` the record's floor as shares of it (the ship's rooms: the spot keeps its place when a room is
  built at another size), with `fov` and `stand` (a small room's shot stands and turns rather than walking into a
  wall). The planner keeps clear of people and moving things (camera_paths), glides at one speed between eased ends and
  rounds its corners (demo.py). About EUR 3.2 a place likely and 3.5 high (twice a measured 96-frame film's 1.6 and 1.75).
- **A film is one batch** (#21, owner 2026-10-20, replacing #20's paid preview): everything before the yes is free,
  the local preview (`tools/review/film_preview.py`) and the forecast (`python -m score.stages.demo_film forecast
  <place>`: frames, cards, card minutes and euros likely and high, from a scan of the accepted stage for fog,
  volumes and glass, priced high at `FOG_FRAME_MINUTES` a frame). A film whose record lacks `"final": true` keeps
  its node (the films page can put it in the basket), but the row is Blocked before anything is bought; the creator
  writes `final` once he has seen both. A film whose forecast's high passes the euros its run was cleared at is
  Blocked too: a dearer film is a new ask at the forecast's price. Never write it for him.
  The final is rendered once at 1280x720 over the cards `capacity.machines_for` sizes (no fixed card count), each
  job's deadline its frames at the forecast's high; a job that dies or passes it is a gap, never run again inside
  the batch, and filming it again is a new batch and a new yes. The gate holds each film to the size its views.json
  planned.
- **The gate measures**: film_checks' video checks (size, sound, black, frozen, length) and the clearance on every
  frame (meshes, people and moving things at the frame's own moment), and the owner's faults of 2026-10-18 (#28, `shots.py`):
  every shot at least `SECONDS`, a frame showing a person where the stage holds people (and a stage that holds
  none where the place's cast record stands people fails, #26), and nothing seen moving in a
  shot without a sound under it. Whether a film reads well is the creator's call. One card class (`CLASSES`
  gpu-24gb): a dearer class taken when it is out of stock would be a fallback chain inside the batch.
- **The environment's own film** (`final.py`, the environment-film row, #28): one environment node, free (a local
  ffmpeg cut), reading every film script in `data/films/` and, beside it, the place films they show
  (demo-film, demo-film-extra), so the runner plans and prices it with them. Blocked until the script says
  `"final": true`; every segment names its `seconds` and is a cut it makes (title, text, walk-through, hero still),
  else the node is Blocked naming each segment (exploded, isolate, layer cuts, step cards, before and after need
  frames no row makes yet). The whole film's sound is moved by one gain to `TARGET_LUFS`; its gate holds the pace
  (`PLACE_SECONDS` a place, `SHOT_SECONDS` a walk-through) and the loudness. Its needs (`needs.py`) are the gaps
  check's film gaps: a film a script shows with no record, no yes, or one shot only.
- **Stills come from the films first.** K5, K6 and K8 take frames of the places' films (a film starts a second before the
  first one-off moment of its place's motion record, `motion_start`: the launch's from 5 s, so its lift-off at 6 s
  lands 1 s into the shot; places whose motions loop start at 0); `stills.py` (the demo-stills row,
  `data/definitions/demo_stills/<place>.json`) renders a still only for a view no film shows (K3's tool board).
- Run: `python -m score run world1 --place <place> --stage demo-film --detach` (a film the creator said yes to starts by
  itself once its place passes complete, or fails it only on its accepted gaps, in any environment run). Test: `demo_film_test.py`, `shots_test.py` and `final_test.py` (no Blender, no spend; one small local ffmpeg cut).
