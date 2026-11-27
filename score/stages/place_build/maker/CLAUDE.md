# score/stages/place_build/maker/

place_build's `make` (#128, owner 2026-11-16; TRELLIS.2 beat our picture-made models on 5 of 6 camp props): a prop's
model made with TRELLIS.2 from its picture, set in the place, graded to its palette, made sim-ready and taken into
score_lib as a draft `model/<name>_trellis.<place>` entry. `__init__.py` is the order; the steps are its own files.

- **Its own Python, built from source** (`setup.sh`, `$PROPS_HOME/envs/trellis2`): TRELLIS.2, FlexGEMM, CuMesh and
  o-voxel at pinned commits, compiled here with NVIDIA's CUDA 13.0 compiler from PyPI (math_functions.h patched for
  glibc 2.41+'s noexcept rsqrt); no prebuilt wheel from a third-party account. No flash-attn (`shim/flash_attn`, torch's
  own attention) and no NVIDIA nvdiffrast (`shim/nvdiffrast`, a UV rasterizer). Weights at pinned revisions and hashes.
  Never edit setup.sh while it runs (bash reads it as it goes).
- **The close-up picture model** (`setup.sh closeup`, `$PROPS_HOME/envs/closeup`, 2026-11-26): FLUX.2 klein 4B
  (Apache-2.0) in diffusers, weights a cache at the revision images/pictures/models.json pins; free on this PC for 2099,
  which has no money: it redraws a concept crop too small for TRELLIS.2 (45x32 px) as a clean close-up on plain ground.
- **On a cloud card** (`cloud.made`, 2026-11-19: GPU work goes to the cloud; the player models' stills): generate.py in
  the meshparts image's TRELLIS.2 (SegviGen's checkout of its code, its author's wheels), weights from the node cache
  (images/meshparts/models.json `trellis2-4b-make`, `trellis-image-large-ssdec`), any pictures in one job, each in its
  own process (its cumesh wheel of 2025-12-10 predates CuMesh's no-boundary returns: `generate.closed_skipped` skips fill_holes on a mesh with no boundary loop, `generate.cache_emptied` gives torch's cache back before decode's; 2026-11-27, 12 of 191 cluster makes stopped there); kept apart from `make`, whose package the finish's code version hashes (finished imports grade). `make`
  itself still uses the card queue (tools/cloud/backends/card_queue.py, a 16 GB scope): one model a process, the whole
  card (CARD_GB), about two minutes. `make --card-only` runs only that card step (kept in made/<entry>/), the same make after it finishing on the processor, so a queue starts the next card step meanwhile (2026-11-26). Its TRELLIS.2 models are built without torch's random fills (generate.unfilled, the
  load 38 s to 4 to 12 s) and each flow model read when its stage asks (generate.OnUse, 11.0 GB at the most); two makes
  side by side were slower, 2 to 3 times each (#159). A made model is kept under `<folder>/made/<entry>/` and not made again.
- **Fits this PC's card, the model unchanged** (#169: a printer box and a fridge stopped with 'CUDA driver error:
  device not ready', WSL's answer to a card overrun): `generate.lean` runs the sparse convs on FlexGEMM's implicit
  GEMM, LayerNorm32 and the decoders' last norm a block of rows at a time, and the remesh on `remesh.py` (CuMesh's,
  each step's scratch dropped once read); each is bit for bit the code it replaces (the test's torch rows, run in the
  maker's Python). `generate.capped` holds torch's allocator to the card's free memory, so a real shortage is an
  out-of-memory, never the driver error. The printer box: 10.2 GB of tensors at most, 13.1 GB of card, 17.4 GB of RAM.
- **Thin sheets kept whole, small detail kept open** (#191, #159 r15): to_glb's remesh contours the surface `band`
  voxels off TRELLIS.2's and projects each vertex back to one voxel off (`generate.band_for`). At BAND (3) every gap up
  to six voxels across closes: the fridge's 2 mm glass door's pinholes (#191), but also hand drill b01's gear teeth, the
  tool cart's pegboard holes and the locker's vents (r15: the decoded surface 5.5 voxels off the band 3 remesh at its
  99th percentile on the drill, 1.2 at band 1). So BAND is laid only on a model whose decoded voxels are SEE_THROUGH
  (1%) or more under CLEAR alpha (glass, where TRELLIS.2's pinholes are), every other at band 1 unprojected; `made`
  records `see_through` and `band`.
- **The decoded mesh kept beside it** (#159 r11: the remesh closes the drawer seams, door lines and vents a voxel or
  less wide with #191's pinholes, while TRELLIS.2's decoded mesh still holds them): generate.py writes it at
  `decoded_path` (<out>-decoded.glb, cut to FACES whatever the model's faces, its shape alone: `decoded_shape`, to_glb's own no-remesh cleaning and cuts with no UV unwrap or bake, 2026-11-26: their processor work held the card 1 min 54 s of a 3 min 21 s generate; the same surface area, cumesh's cut differs run to run either way), and `make` sets it in
  the place under the placed model's root matrix (`decoded_placed`: `decoded_file`, made/<entry>/<entry>-decoded.glb).
  Never shown and never taken into score_lib: the bench look and the place's package bake (scene_package.shade_of,
  #209) shade the model's seams from it (bake.seamed), the package reading it in the place's made/ folder, so a model
  laid in another place is shaded by its own occlusion alone, as is one made before it was kept. `cloud.made` brings
  it back beside the model (`brought_back`).
- **Its mesh repaired, its shape kept** (repair.py, #167: tc1's TRELLIS.2 models held 30 to 2,290 edges four faces
  held, membranes of two opposite faces and, on the rack, 289 crumbs). On the fitted GLB, every attribute carried with
  its vertex: collapsed faces and membranes out; a corner where two solids touch is one corner a fan, the further
  fan's copy moved NUDGE (1e-5) of the diagonal into its own fan (a four-face edge paired by the solid wedge between
  its faces; a fold of one surface cut); pieces under LOOSE (the bench's crumb, 0.1% of the area) out (every one on
  tc1, 692 of 698, lay inside the body); each piece wound one way and outward as TRELLIS.2's own vertex normals look (a
  signed volume of an open piece turned real parts inside out); a vertex normal pointing against its faces set to
  theirs (`facing_normals`, #159: the printer box's normals turned into its body drew black holes through its
  front). The bench's shape measures moved by 0.005 at most.
- **Only a cut-out goes in** (#156: the capsule's throttle, levers on a console top, came out a cube): `concept/<n>`
  is refused without its SAM 3 mask, and any picture whose opaque part is its own rectangle (no transparency, or a
  box cut) is refused (`cut_out`); a missing noun is asked with `split --nouns`.
- **Lossless edits** (glb.py): the fit is a root node's matrix, the grade replaces the base colour picture only.
- **The fit** (fit.py) covers the model it replaces (`--like`): quarter turns and uniform scales, the smallest two-way
  point distance; `--height` stands a new prop on the floor; `--size wide,deep,tall` (the prop benchmark's row, #163)
  brings it to each side, each axis at most STRETCH (a quarter) off the uniform scale that sets its longest side (#170:
  uniform, tc2's sign came out 13% too thick and its desk 9% too wide; past a quarter the row and the model disagree,
  so a leg or panel is not thinned further, and the record's `off` says how far the box stayed off). Set at a size, it
  is first turned to its close-up's heading (`fit.headed`, #166: TRELLIS.2 keeps its own heading, so the desk, rack and
  sign lay wide for deep): the quarter turn whose outline from the close-up's camera (tools/props/closeup/check.py's
  turn and look-down) best overlaps the picture's, never a mirror (#159 r15: TRELLIS.2 makes its picture's hand; hand
  drill b01, mirrored on a 0.05 better outline, laid its crank behind its knob). Turns within
  FRONT_BAND of the best (a box-like object's front and back: tc4r's desk a half turn off, its fridge's glass door on
  its side, #192) go to `front.picked`: each drawn in the model's own texture from the close-up style's camera, and one
  ask (Claude, EUR 0) picks the drawing whose content sits where the close-up shows it.
- **`--no-take-in`** (the prop benchmark, #163) makes, fits, grades and makes sim-ready as usual and takes nothing into
  score_lib: the files stay under `<folder>/made/<entry>/`, the address is None.
- **The grade** (grade.py) moves each colour group GRADE of the way to its nearest palette token; a large group far from
  every token is a `mismatch` in the answer: repaint it from the library (`surface`), never grade harder.
- **A graded paint is not a finish**: grade.py's `parts` names its paints, and `put` lays each as the palette
  variant nearest its colour (finished/), so a made model never shows TRELLIS.2's paint as its finish.
- **Physics** (sim.py, #159 by #161's rules): the classes are NVIDIA's per-class table
  (data/physics/surface_classes.json, its odd rows out; aluminium its own row); a part's class its finish's library
  surface's (an NVIDIA surface's name, else its recipe's), a hull's the class of most face area inside it, friction
  and restitution the hulls' rows by volume. The mass is a real-world figure a part, never area x sheet x density
  nor volume x density: Claude answers it from the picture, words, size and parts (`weighed`, EUR 0, kept by the
  ask's hash), held to NVIDIA's bulk density band for the size class and named, not refused, outside it (NVIDIA's own
  empty box is). `make` weighs the whole as one part of its `--material`; the benchmark's `physics` step weighs the
  finished parts. A part under UNWEIGHED (1e-4) of the surface is not asked and weighs 0 (#159: the toaster's one-face
  ink, which the split no longer makes a part, finish_parts.NO_AREA).
- **Moving parts** (parts.py, #177, #161 rules 1 and 11): one ask (Claude, EUR 0) names what moves in the close-up
  (function word, hinge, slide or spin, its box, a hinge's side, how far it opens, its thickness); its faces are those
  the close-up's camera sees in its box, from its outer face in by its thickness; its joint sits on its box's edge or
  axis, the model's own axes; it is written in moving_parts' node interface (`<part>__<joint>_<axis>[n]`, origin the
  pivot), which place_build's glTF conversion keeps as its own Xform, the motion layer reads (`parts_of`) and the
  physics layer joins (`write_parted`). The benchmark runs it (branch B's `parts` step), and `make` runs it too
  (`parts.made`: its camera fitted to the cut-out's outline as the finish route fits one, surfaces/close_up_fit.py;
  the model taken in holds the part nodes, its record `moving_parts` each part's joint, limits and kg).
- Test: `test_a_made_model_fits_its_place_its_paint_and_its_weight.py` (no TRELLIS.2, no CoACD; its flash-attn part
  runs where torch is).
