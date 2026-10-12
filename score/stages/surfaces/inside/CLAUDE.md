# score/stages/surfaces/inside/

Scripts that run inside Blender on a rented machine (`tools/props/cloud/blender_cloud.py`, the surface stage's
turntable row, `../turntable_row.py`), never on the owner's PC: `turntable.py` draws a raw Pixal3D model's own texture
unlit from the close-up's camera and round it, with the face under every pixel, for the finish-map method's view maps
(`../turntable_views.py`, `../finish_parts.py`);
`paint_take.py` hands one take's paint to Blender's own Python outside Blender (`../place_line.py` paint-take) on a
processor machine, with pinned packages installed once a machine, and says its peak memory. The rules are `../CLAUDE.md`'s and `tools/blender/inside/`'s.
