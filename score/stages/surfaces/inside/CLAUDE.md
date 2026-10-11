# score/stages/surfaces/inside/

Scripts that run inside Blender on a rented machine (`tools/props/cloud/blender_cloud.py`, the split rows' turntable,
`../split_batch_paid.py`), never on the owner's PC: `turntable.py` draws a raw Pixal3D model's own texture unlit from
the close-up's camera and round it, with the face under every pixel, for `../multiview.py` (the g-texture method,
EXPERIMENTAL). The rules are `../CLAUDE.md`'s and `tools/blender/inside/`'s.
