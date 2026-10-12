# score/stages/physics/inside/

Scripts that run inside Blender on a rented machine (`blender -b`), sent by the physics trial
(`../__init__.py`): never with the system python, never on this PC but for a toy place of seconds. They read the
stage's UsdPhysics through Blender's bundled pxr; the rules are the parent overlay's.
