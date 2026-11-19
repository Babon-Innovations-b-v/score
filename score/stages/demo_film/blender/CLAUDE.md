# score/stages/demo_film/blender/

`film_frames.py` runs inside Blender on the rented card that draws a demo film's frames (blender_cloud.py ships this
folder and `tools/blender/inside` with the job): `tools/blender/inside/usd_views.py` as it is, its camera keyed to the
next frame's for motion blur, its denoiser on the card and the scene kept between frames (its docstring: measured the
same pictures, quicker). The shutter and the next camera are worked out free, before the job, by
`../__init__.py` (`motion_blurred`).

- **usd_views.py stays untouched for this.** Many paid rows declare it (light passes, library clips,
  stills, crops); a change there moves all their keys. The films' own look goes here, which only the demo-film rows
  and the environment film declare (`TOOLS`).
- Blur only what moves: the camera and the stage's moving transforms, never a mesh's deformation (it doubles a skinned
  body's evaluation, which no ledger has priced).
- `film_frames.py`: never run here: it needs `bpy`. Checked with the `bpy` module of the cloud's Blender version, never
  a local render.
- `body_peel.py`: a layer or place peel's three passes, the frames its job's `frames` names (a slice of the shot,
  `../peel.py` sliced). Run on rented cards by the body-peel and place-peel rows (`../peel_rows.py`, which declare it),
  or free on this machine by `../peel.py`'s command line (`blender -b`); no demo-film row declares it.
- `walker_peel.py`: a walker peel's passes in its place (`../peel.py` walker_job, `--scene`), on this PC's card through
  the card queue: it patches usd_views.py's import (the peel laid in) and render (a frame's passes) and then imports
  place_build's `blender_views.py`, which runs usd_views.main() with the laid place's look; the peel's drawing is
  body_peel.py's.
- `layered.py`: a film's frames as layers (`../layered.py` plans, keeps and composes them; owner 2026-11-19): the
  place once with every person hidden, each walker and peel layer alone over it with the place a shadow catcher
  (Cycles only), each an EXR in linear light; walker_peel.py draws its peel's layers through it when its job names
  `layered`. `compose.py`: the layers composed (catcher shadows, then depth-ordered alpha over) and the place's look
  (glare, view transform) applied once; no scene is drawn. Its `composite` is tested without Blender.
