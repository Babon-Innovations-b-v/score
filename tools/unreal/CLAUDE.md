# tools/unreal/

Unreal Engine 5 for SCORE's films (PRD #215): a place's scene package rendered in Unreal beside Blender. Unreal is free
for us (Babon under $1M a year; rendered films owe no royalty, EULA §3(a)).

- **No Unreal engine file and no Epic code or asset in this public repository** (the EULA): only our own Python that
  runs in Unreal's editor and names its classes. An image recipe may name Epic's container image only for a private
  registry.
- **Every finish is ours** (the library rule): our baked maps and factors from the scene package on our own master
  materials built from code, never a Megascans, Fab or Poly Haven texture matched by name (#217, #215's decisions).
- **Logic outside Unreal, the editor a thin layer**: what can be worked out from files (scene.json, the glTFs,
  film/path.json) is plain Python with no numpy, tested here with the repo's Python; the part that calls `unreal` only
  carries out its plan.
- **Rendering is elsewhere**: the headless Movie Render Queue run on a cluster card, its image and shader cache are
  `tools/cloud/unreal/` (#222); this folder makes the level and the Level Sequence it renders.
