# score/stages/light/inside/

Scripts that run inside Blender on a rented card (`tools/props/cloud/blender_cloud.py` ships this folder and
`tools/blender/inside`), never on the PC except a seconds-long check on a tiny stage made for it. `light_passes.py`
renders a stage as `usd_views.py` does, through usd_views' own functions, with each of the place's lamps in a Cycles
light group; change how a look is drawn in usd_views, never here, so the passes and every other look agree.
