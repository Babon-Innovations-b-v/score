# score/stages/surfaces/inside/

Scripts that run on a rented machine (`tools/cloud/blender_cloud.py`), never on the owner's PC:
`paint_take.py` hands one take's paint to Blender's own Python outside Blender (`../place_line.py` paint-take) on a
processor machine, with pinned packages installed once a machine, and says its peak memory; `paint_bake.py` runs it
on the bake's card, then `../route_bake.py` bake-job and make_chunky, one job a take (the finish route's bake, #18). The rules are `../CLAUDE.md`'s and `tools/blender/inside/`'s.
