# tools/blender/inside/

Scripts that run inside Blender (with `bpy`), never with the system python: `startup.py` at
launch, the rest imported by `session.py run`/`artifacts` or a `session.py batch` job. They load
no model and open no window of their own; the rules are the parent overlay's (`../CLAUDE.md`).

`test_ink_at_edges_and_each_prim_its_own.py` is the one file here that is not: it checks the parts that need no
Blender (the ink rule, annotate's object numbering, the effect lookup) with `bpy` and `mathutils` stubbed, in the gate
with `.venv/bin/python`.
