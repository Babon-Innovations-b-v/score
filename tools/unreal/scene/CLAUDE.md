# tools/unreal/scene/

A place's scene package (`python -m score.stages.place_build package <folder> <out> --film`) and its film path into
the Unreal editor (#221). `plan.py` works out everything (no engine; its docstring the plan's format), `editor.py`
runs inside Unreal's Python and carries the plan out. Rules: the parent overlay's.

- **Axes are measured, not assumed.** `frames.BASIS` (glTF's +x as Unreal's +x, +z as +y, +y as +z, metres as
  centimetres: what UE 5.8's Interchange gave in #222's run 8) is only the expected one: `editor.py` imports the calibration box first and reads the
  import's own basis from its bounds, and every copy, lamp, sun and camera key is turned through that.
- **The film path is in its place's own frame**, the package in its area's when seated: scene.json's `seat` lays the
  path on the package (camera.on_seat), and a package in an area's frame with no seat is refused (run 9's camera stood
  27 m off the street, behind a block).
- **The camera stands at the first key and its keys must land.** The cine camera is spawned at key 0 with its focal
  length, and `keyed` refuses a section whose channels did not all take every key (`camera.unlanded`, a fault in
  made.json): runs 9 and 10 drew from the spawned camera at the level's origin, unturned, at 35 mm, the keys absent.
- **A copy is an actor a part of its object** at its laid transform (scene.json's `matrix`, a turn and an even
  scale): the import gives one mesh asset a glTF mesh node even when told to combine (run 8), so an object comes in
  as 1 to `parts` meshes (plan.py), never silently fewer; Nanite on every object with no see-through look and no skin.
- **One Material Instance a look**: equal master, factors and pictures are one instance across objects; a baked
  recipe's map is its own. Glow (factor times KHR_materials_emissive_strength) and glass (opacity 1 - transmission,
  refraction at its IOR) are set by us, never left to the glTF import.
- **Light units are an assumption to measure**: `layout.LUMENS_A_WATT` and the manual exposure that divides it back
  out are checked against Blender's frames in the side-by-side test (#218), not trusted. Everything Unreal reads as
  light (lamps, sun, sky light, glow) is Blender's figure times LUMENS_A_WATT, or the exposure leaves it 683 times too
  dark; a night's ambient is an even sky light, and every light is Movable (no built lighting).
- Plain Python with no numpy in every file but `editor.py` (which needs `unreal`): Unreal's own Python imports them.
