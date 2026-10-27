# score/stages/demo_film/blender/

`film_frames.py` runs inside Blender on the rented card that draws a demo film's frames (blender_cloud.py ships this
folder and `tools/blender/inside` with the job): `tools/blender/inside/usd_views.py` as it is, its camera keyed to the
next frame's for motion blur (its docstring). The shutter and the next camera are worked out free, before the job, by
`../__init__.py` (`motion_blurred`).

- **usd_views.py stays untouched for this.** Many paid rows declare it (light passes, library clips,
  stills, crops); a change there moves all their keys. The films' own look goes here, which only the demo-film rows
  and the environment film declare (`TOOLS`).
- Blur only what moves: the camera and the stage's moving transforms, never a mesh's deformation (it doubles a skinned
  body's evaluation, which no ledger has priced).
- `film_frames.py`: never run here: it needs `bpy`. Checked with the `bpy` module of the cloud's Blender version, never
  a local render.
- `body_peel.py` is the other way round: a layer peel's three passes, run on this machine by `../peel.py` (`blender
  -b`), no paid job runs it; no demo-film row declares it.
