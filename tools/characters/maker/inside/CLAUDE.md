# tools/characters/maker/inside/

Scripts that run inside Blender on a rented processor machine (`tools/props/cloud/blender_cloud.py`), never on the
PC. `body_checks.py` runs a built person's checks (pokes, outline, the two body-through-cloth counts) side by side
in Blender's own Python with the prop environment's pinned packages, as the surface stage's paint does
(`score/stages/surfaces/inside/paint_take.py`); `prop_person.py checks_cloud` writes its listing and job. Keep its
pins equal to the paint's.
