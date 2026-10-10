# tools/review/

The creator's review page for one place (PRD #1, the review tools the paper describes): every stage's output in the
order the stages ran, before and after where a stage was rerun, and every check's result with what it caught.
`page.py` is the way in (its docstring has the command); `records.py` reads what the stages wrote; `renders.py` draws
what no stage drew, through headless Blender (`../blender/inside/review_models.py` for the models and their parts,
`../blender/inside/usd_views.py` for the scene).

- **Read, never write, the records.** The page is built only from files the stages already wrote; a stage that wrote
  nothing reads as "Not recorded", never as a stand-in. Add a stage by reading its file in `records.py`, not by making
  a stage write something for the page.
- **The scene comes from the OpenUSD stage** (`../usd/export.py`), never from a game engine: in its baked materials,
  on the stage's own ground, lit by a low sun with a weak fill and a little sky light so no side is black. `--plain`
  (one grey, no materials) is a debug view only, never the page's default. The checks include the resting check
  (`../usd/resting.py`) and the placeholder check (`../usd/placeholders.py`) on every stage. Blender only through
  `../blender/session.py batch` (no window, the machine's lock, the memory floor).
- **Same cameras for a rerun.** A model's takes share one camera set from all of them; every stage of a place is drawn
  from cameras set from the newest stage. Keep it so, or before and after stop being comparable.
- The page is generated outside the repo (a folder with `index.html`, `img/`, `models/`, `scene/`); nothing it makes
  is committed. It opens from disk and can be published as it is.
- `review_test.py` builds a page from two runs made in the test (no Blender) and checks the cameras' geometry.
- **A kit room** (route.py's run: its plan.json holds models and pieces) shows its generated models one by one and
  counts its code ones; a room with a roof (draw layer 2) is drawn from inside by its own lamps, with a cutaway from
  above. A room of a place of another name (the prologue's street, place `prologue_street`) reads its place from its
  inventory.
- **Characters** (`characters.py`): a place with a cast (`data/characters/<place>.json`) gets a Characters section,
  why each entry is there, each character close (from the first clear eye round its front), each group and the crowd
  wide, and short moving shots, all drawn from the stage at set moments of its time (a view's `frame`); the scene's
  walk is drawn at consecutive moments too, so its people move.
- **A place with a scene record** (`data/scene/<place>.json`) is drawn from the record's own cameras (the player's
  spots; a room from inside at standing height and a cutaway from above, never from outside a closed room), lit by the
  stage's own lights and sky (no added sun; `"fill"` in views.json adds the weak fill as an option), with no grey plane
  under a room. `--game-shots <folder>` lays each view beside the game's shot it names, with both pictures' mean
  brightness: a scene view under half the game's is caught. The "scene vs game" line says what the record and the cast carry
  and what it lists as game only.
- **The style measure** (`style.py`, `style_test.py`; the paper's style-coherence gap): per place, from the review
  pages' made-model renders only, the coloured pixels' fit to the place's library palette, the spread of the models'
  lightness, how blotchy their surfaces look (surface marks), and DINOv2's likeness within the place against across
  places, with the same pairs as silhouettes subtracted so what an object is does not count as its style. DINOv2
  runs on a rented machine through `../props/cloud/similar.py`, never here. It reports numbers, never a verdict;
  validating it needs the creator's reviews.
- **Luminance per region** (`brightness.py`): the whole picture's mean hides a dark part behind a bright one (the far
  city behind the lit square), so a part is measured on its own: the objects whose prim path holds the `--match` words,
  from the annotate step's ids (`../usd/annotate.py`), and horizontal bands, in linear light against the game's shot
  from the same camera. A knob tuned to the game's brightness (the far city's lit windows) is set from these numbers,
  never by eye. `brightness_test.py` checks it on pictures made in the test.
- **The demo's films** (`demo.py`, PRD #1's world demo): a walk-through film of each place from its stage, rendered on
  the cloud, every frame with the game's ink lines (usd_views.py's `ink`, or its `lines_only` laid over looks rendered
  before: the cheap pass, never a re-render for ink alone) and the night glow where the stage carries it. Every shot
  starts and walks the planner's clearance from walls, objects and people (`../usd/camera_paths.py`); a camera with no
  clear spot near it is left out, never filmed from inside something. The views file keeps every shot's move and the
  planner's commit; `--keep` keeps an earlier take's clear shots as they were. `film_checks.py` is the film's measured
  checks (ffmpeg's size, sound, black, frozen and length; the clearance on every frame from meshes and from people at
  the frame's own moment; the ink pass drawn on every frame, a frame that sees only what lies past the ink's fade
counted, not failed): a film that fails is not shown. `showcase.py` cuts the showcase and the
  figure from the films. `demo_test.py`, `film_checks_test.py` and `showcase_test.py` check them without Blender.
