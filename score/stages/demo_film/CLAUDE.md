# score/stages/demo_film/

The demo-film and demo-film-extra rows (experimental, 2026-10-14): demo K9's walk-through films of a place, from its
final stage once it passes complete or fails it only on its named gaps (`gapped`, the overseer 2026-10-15), with its
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
  one camera path of 4 s, 1280x720 at 24 frames a second (96 frames), the look only (no ink): a 5.5 s film with its
  title card, which the length gate holds to. People need no handling: the characters layer lays nobody today.
  About EUR 0.7 a place (EUR 1.0 for the 8 s path of 192 frames; the overseer's plan, 2026-10-15).
- **The gate measures**: film_checks' video checks (size, sound, black, frozen, length) and the clearance on every
  frame. Whether a film reads well is the creator's call.
- **Stills come from the films first.** K5, K6 and K8 take frames of the places' films (a film starts a second before the
  first one-off moment of its place's motion record, `motion_start`: the launch's from 3 s, so its lift-off at 4 s
  lands 1 s into the shot; places whose motions loop start at 0); `stills.py` (the demo-stills row,
  `data/definitions/demo_stills/<place>.json`) renders a still only for a view no film shows (K3's tool board).
- Run: `python -m score run world1 --place <place> --stage demo-film --detach` (a film starts by itself once its place
  passes complete, or fails it only on its named gaps, in any environment run). Test: `demo_film_test.py` (no Blender, no spend).
