# tools/unreal/scene/

A place's scene package (`python -m score.stages.place_build package <folder> <out> --film`) and its film path into
the Unreal editor (#221). `plan.py` works out everything (no engine; its docstring the plan's format), `editor.py`
runs inside Unreal's Python and carries the plan out. Rules: the parent overlay's.

- **Axes are measured, not assumed.** `frames.BASIS` (glTF's -z ahead as Unreal's +x, +x as +y, +y as +z,
  metres as centimetres) is only the expected one: `editor.py` imports the calibration box first and reads the
  import's own basis from its bounds, and every copy, lamp, sun and camera key is turned through that.
- **A copy is an actor of its object's one mesh** at its laid transform (scene.json's `matrix`, a turn and an even
  scale), Nanite on every object with no see-through look and no skin.
- **One Material Instance a look**: equal master, factors and pictures are one instance across objects; a baked
  recipe's map is its own. Glow (factor times KHR_materials_emissive_strength) and glass (opacity 1 - transmission,
  refraction at its IOR) are set by us, never left to the glTF import.
- **Light units are an assumption to measure**: `layout.LUMENS_A_WATT` and the manual exposure that divides it back
  out are checked against Blender's frames in the side-by-side test (#218), not trusted.
- Plain Python with no numpy in every file but `editor.py` (which needs `unreal`): Unreal's own Python imports them.
