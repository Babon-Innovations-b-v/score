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

