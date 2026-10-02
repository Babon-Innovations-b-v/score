# tools/props/scene/

A room composed from a target picture, an experiment (2026-10-02, #121's interiors): draw the
room (`target.py`), cut each object out by name with SAM 3 (`cutout.py`), measure the picture in
metres with MoGe-2 (`depth.py`) and the room and its objects' boxes (`boxes.py`), redraw each
cut-out whole (`redraw.py`), build each through `../pixal.py`, read the models' sizes and seen
sides (`models.py`), place them by rules (`layout.py`) and draw the result from the target's own
camera in the game's look (`stage.tscn`). `marble.py` sends a target to World Labs Marble and
brings back its room as a second measure of the same masks (`boxes.py --depth depth-marble.npz`).

- Everything a run makes goes under `WORK/scene/<room>/` (`~/.farm-factory-props/work/scene/`);
  target pictures, masks, worlds and layouts never go in the repo.
- Every step that uses the card does so inside `card.claimed()`; Pixal3D only through `pixal.py`.
- SAM 3's weights are gated on Hugging Face; `SAM3_WEIGHTS` names a copy when the account has no
  access. MoGe-2 and its helper library are copies outside the repo put on the path, never
  installed into the prop environment, whose own `utils3d` is TRELLIS's.
- Marble's API key is read at run time from `~/.config/worldlabs/api_key`, never written anywhere.
  A world costs about 1,580 credits; its high-quality mesh export another 3,500. Marble worlds
  are a layout reference only: shipped models stay our own.
- The stage is not the game's habitat scene, which the module kit owns; its shell is a stand-in
  built from the measured section.
- `layout_test.py` is the gate's check of the placing rules, plain python.
