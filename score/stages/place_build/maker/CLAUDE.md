# score/stages/place_build/maker/

place_build's `make` (#128, owner 2026-11-16; TRELLIS.2 beat our picture-made models on 5 of 6 camp props): a prop's
model made with TRELLIS.2 from its picture, set in the place, graded to its palette, made sim-ready and taken into
score_lib as a draft `model/<name>_trellis.<place>` entry. `__init__.py` is the order; the steps are its own files.

- **Its own Python, built from source** (`setup.sh`, `$PROPS_HOME/envs/trellis2`): TRELLIS.2, FlexGEMM, CuMesh and
  o-voxel at pinned commits, compiled here with NVIDIA's CUDA 13.0 compiler from PyPI (math_functions.h patched for
  glibc 2.41+'s noexcept rsqrt); no prebuilt wheel from a third-party account. No flash-attn (`shim/flash_attn`, torch's
  own attention) and no NVIDIA nvdiffrast (`shim/nvdiffrast`, a UV rasterizer). Weights at pinned revisions and hashes.
  Never edit setup.sh while it runs (bash reads it as it goes).
- **The card queue only** (generate.py through tools/cloud/backends/card_queue.py, a 20 GB scope): one model a
  process, about two minutes and 14 GB of card. A made model is kept under `<folder>/made/<entry>/` and not made again.
- **Lossless edits** (glb.py): the fit is a root node's matrix, the grade replaces the base colour picture only.
- **The fit** (fit.py) covers the model it replaces (`--like`): quarter turns and uniform scales, the smallest two-way
  point distance; `--height` stands a new prop on the floor.
- **The grade** (grade.py) moves each colour group GRADE of the way to its nearest palette token; a large group far from
  every token is a `mismatch` in the answer: repaint it from the library (`surface`), never grade harder.
- **A graded paint is not a finish**: grade.py's `parts` names its paints, and `put` lays each as the palette
  variant nearest its colour (finished/), so a made model never shows TRELLIS.2's paint as its finish.
- **Mass** (sim.py): the hulls' outside skin (faces inside another hull left out) times the class's sheet and density;
  a sheetless class (stone) is solid. Steel is data/physics/materials.json's row, read; the maker's other classes stay
  here, since that table keys the physics rows. Hulls close over a frame's gaps, so a steel frame's mass is high.
- Test: `test_a_made_model_fits_its_place_its_paint_and_its_weight.py` (no TRELLIS.2, no CoACD; its flash-attn part
  runs where torch is).
