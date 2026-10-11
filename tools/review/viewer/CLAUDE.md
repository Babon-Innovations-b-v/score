# tools/review/viewer/

The owner's walk-through of a finished place before any film is made, and where he picks the viewpoints the films
start from. `export.py` writes a place's web copy from its OpenUSD stage; `serve.py` serves every copy and the viewer
(`viewer.html`, three.js) on this machine; `viewpoints.py` keeps his picked viewpoints, which `../demo.py` takes as a
film's cameras. Each file's docstring has its command.

- **From the stage, whole.** The web copy is the stage at its first moment (people in their first pose, the lights as
  they shine then), every mesh a renderer draws, never simplified: the owner rejects gutted meshes. gltfpack only
  merges by material and compresses (meshopt); positions stay floats, since 16-bit positions over a place with a far
  ground ball terrace a sloping sheet through its floor. Pictures go in at web size (TEXTURE_SIZE). What it cannot
  draw yet (a point instancer: rocks, crowds; a shape other than a mesh or a sphere) it counts in the sidecar's
  `left_out` and the export's line; never leave something out silently.
- **Light, so local.** A place exports in seconds within a few GB (the hangar: 8 s, 2.1 GB peak), under the 16 GB cap
  as the docstring says; it needs no Blender. A stage too big for that goes to the cloud through the runner, not
  onto the PC.
- **Picks are the owner's.** Only the viewer's save writes `data/review/<place>/viewpoints.json`; never write, edit
  or seed a pick for him, and a test or a demonstration saves into a folder of its own (`--picks`), never into
  `data/review`. A pick is in the scene record's camera form (eye, aim, fov across the picture), so the films take
  it as they are.
- **The viewer is a look, not the film.** The lights follow Blender's reading of the stage (usd_views.py) in three.js
  units, AgX like the films, but it is a rasteriser: no shadows, no bounce light; the ink lines are an approximation
  of the game's rule. Judge framing and layout here, the look on the films and the review page.
- three.js is loaded pinned (core from cdnjs, its add-ons and three-mesh-bvh from jsdelivr, where cdnjs has none);
  move a pin only to a release at least two weeks old.
- `viewer_test.py` exports a stage made in the test (gltfpack through npx), checks the copy and the sidecar, saves
  and reads back viewpoints and drives the server.
