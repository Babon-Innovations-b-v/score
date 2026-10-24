# score/stages/people/inside/

Scripts that run inside Blender on a rented card (`tools/cloud/blender_cloud.py`), never on the owner's PC:
`bake_body.py` bakes a dressed body's library surfaces into one picture set with the library's own bake
(`tools/props/library/inside/bake.py` `Atlas.bake_self`), for `../baked_body.py`, the dress's bake. It reads the
library's bake and ProcFunc from the folders the job sends, never a copy of its own. The rules are `../CLAUDE.md`'s
and `tools/props/library/inside/`'s.
