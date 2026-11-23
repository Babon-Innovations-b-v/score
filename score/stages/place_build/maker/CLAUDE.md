# score/stages/place_build/maker/

place_build's `make` (#128, owner 2026-11-16; TRELLIS.2 beat our picture-made models on 5 of 6 camp props): a prop's
model made with TRELLIS.2 from its picture, set in the place, graded to its palette, made sim-ready and taken into
score_lib as a draft `model/<name>_trellis.<place>` entry. `__init__.py` is the order; the steps are its own files.

- **Its own Python, built from source** (`setup.sh`, `$PROPS_HOME/envs/trellis2`): TRELLIS.2, FlexGEMM, CuMesh and
  o-voxel at pinned commits, compiled here with NVIDIA's CUDA 13.0 compiler from PyPI (math_functions.h patched for
  glibc 2.41+'s noexcept rsqrt); no prebuilt wheel from a third-party account. No flash-attn (`shim/flash_attn`, torch's
  own attention) and no NVIDIA nvdiffrast (`shim/nvdiffrast`, a UV rasterizer). Weights at pinned revisions and hashes.
  Never edit setup.sh while it runs (bash reads it as it goes).
- **On a cloud card** (`cloud.made`, 2026-11-19: GPU work goes to the cloud; the player models' stills): generate.py in
  the meshparts image's TRELLIS.2 (SegviGen's checkout of its code, its author's wheels), weights from the node cache
  (images/meshparts/models.json `trellis2-4b-make`, `trellis-image-large-ssdec`), any pictures in one job, each in its
  own process; kept apart from `make`, whose package the finish's code version hashes (finished imports grade). `make`
  itself still uses the card queue (tools/cloud/backends/card_queue.py, a 20 GB scope): one model a process, about four
  minutes and the whole card (CARD_GB). A made model is kept under `<folder>/made/<entry>/` and not made again.
- **Fits this PC's card, the model unchanged** (#169: a printer box and a fridge stopped with 'CUDA driver error:
  device not ready', WSL's answer to a card overrun): `generate.lean` runs the sparse convs on FlexGEMM's implicit
  GEMM, LayerNorm32 and the decoders' last norm a block of rows at a time, and the remesh on `remesh.py` (CuMesh's,
  each step's scratch dropped once read); each is bit for bit the code it replaces (the test's torch rows, run in the
  maker's Python). `generate.capped` holds torch's allocator to the card's free memory, so a real shortage is an
  out-of-memory, never the driver error. The printer box: 10.2 GB of tensors at most, 13.1 GB of card, 17.4 GB of RAM.
- **Its mesh repaired, its shape kept** (repair.py, #167: tc1's TRELLIS.2 models held 30 to 2,290 edges four faces
  held, membranes of two opposite faces and, on the rack, 289 crumbs). On the fitted GLB, every attribute carried with
  its vertex: collapsed faces and membranes out; a corner where two solids touch is one corner a fan, the further
  fan's copy moved NUDGE (1e-5) of the diagonal into its own fan (a four-face edge paired by the solid wedge between
  its faces; a fold of one surface cut); pieces under LOOSE (the bench's crumb, 0.1% of the area) out (every one on
  tc1, 692 of 698, lay inside the body); each piece wound one way and outward as TRELLIS.2's own vertex normals look (a
  signed volume of an open piece turned real parts inside out). The bench's shape measures moved by 0.005 at most.
- **Only a cut-out goes in** (#156: the capsule's throttle, levers on a console top, came out a cube): `concept/<n>`
  is refused without its SAM 3 mask, and any picture whose opaque part is its own rectangle (no transparency, or a
  box cut) is refused (`cut_out`); a missing noun is asked with `split --nouns`.
- **Lossless edits** (glb.py): the fit is a root node's matrix, the grade replaces the base colour picture only.
- **The fit** (fit.py) covers the model it replaces (`--like`): quarter turns and uniform scales, the smallest two-way
  point distance; `--height` stands a new prop on the floor; `--size wide,deep,tall` scales it uniformly so its longest
  side is the size's (the prop benchmark's row, #163), its other sides what the picture gave. Set at a size, it is
  first turned to its close-up's heading (`fit.headed`, #166: TRELLIS.2 keeps its own heading, so the desk, rack and
  sign lay wide for deep): the quarter turn whose outline from the close-up's camera (tools/props/closeup/check.py's
  turn and look-down) best overlaps the picture's, its mirror only when it beats them all by MIRROR_GAIN.
- **`--no-take-in`** (the prop benchmark, #163) makes, fits, grades and makes sim-ready as usual and takes nothing into
  score_lib: the files stay under `<folder>/made/<entry>/`, the address is None.
- **The grade** (grade.py) moves each colour group GRADE of the way to its nearest palette token; a large group far from
  every token is a `mismatch` in the answer: repaint it from the library (`surface`), never grade harder.
- **A graded paint is not a finish**: grade.py's `parts` names its paints, and `put` lays each as the palette
  variant nearest its colour (finished/), so a made model never shows TRELLIS.2's paint as its finish.
- **Mass** (sim.py): the hulls' outside skin (faces inside another hull left out) times the class's sheet and density;
  a sheetless class (stone) is solid. Steel is data/physics/materials.json's row, read; the maker's other classes stay
  here, since that table keys the physics rows. Hulls close over a frame's gaps, so a steel frame's mass is high.
- Test: `test_a_made_model_fits_its_place_its_paint_and_its_weight.py` (no TRELLIS.2, no CoACD; its flash-attn part
  runs where torch is).
