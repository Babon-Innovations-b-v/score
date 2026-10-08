# tools/blender/inside/

Scripts that run inside Blender (with `bpy`), never with the system python: `startup.py` at
launch, the rest imported by `session.py run`/`artifacts` or a `session.py batch` job. They load
no model and open no window of their own; the rules are the parent overlay's (`../CLAUDE.md`).
