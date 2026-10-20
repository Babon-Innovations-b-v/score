# score/stages/library/clips/blender/

What the library-clips row ships to the rented card: `render_clips.py` (runs inside Blender, every item of a manifest
in turn through the films' drawer) and `framing.py` (plain Python: the views of a clip from the box of what it shows,
shared with the tests). The whole folder goes up with the job (`blender_cloud.shipped`), so keep only these here.

- `framing.py` imports nothing but the standard library: no bpy, no pxr, so it runs in the tests on this PC.
- No Blender runs on this PC: test the framing in `../clips_test.py`, the rest on the card.
