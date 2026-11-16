# tools/characters/clips/

`scene_clips.py` is the scene-made clips' program (CONTEXT.md "scene-made clip", row `scene-clips@<place>`,
`score/stages/scene_clips`): on the rented characters machine it runs `kimodo_gen` on each clip's constraints file
with people/clips.py's walking sentence, model and seed, lowers each clip by its spec's `lift` (`lowered`: the
constraints are asked with the walk's lowest ground on Kimodo's floor), then the maker's rig step; it builds no
constraint itself.

- Never edit `../maker/` or `../people/` from here. Both folders are declared inputs of the paid people rows, so
  an edit there re-keys every body.
- Tests: `scene_clips.py` is held by the scene clips' own test (`score/stages/scene_clips`). The video clip route
  (a body's motion read off an uploaded video) was dropped with its rows (#128).
