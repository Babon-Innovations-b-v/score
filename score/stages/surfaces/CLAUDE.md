# score/stages/surfaces/

The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library), step 1 of PRD #6, as rows of world 1's stage table (`__init__.py`, `ROWS`). Bible: `architecture/components`
and `architecture/experimental`; method: the paper's Methods, "Shape and surface apart".

- **One line per place, run by the runner**: `python -m score run world1 --place <place> --detach` (score's overlay:
  never walk the rows by hand). Rows are place grain (`split-inputs@greenhouse` ... `surfaces-check@greenhouse`); the
  registry's seed (`surfaces-seed-inputs`, `surfaces-seed-turntable`, `surfaces-seed`) is the one world node chain
  every line reads. No place waits on another.
- **The method sits behind one interface**: its rows end in two contracts, `surfaces-parts` v1 (`parts.json`: per
  model its parts, each with its measured finish `{centre, spread}` or null, the judge's surface or null, its words,
  set aside or not; `<take>/parts.npy` one part per welded face; `<take>/colours.npy` each face's seen colour) and
  `surfaces-seed` v1 (`seed.json`: the registry's first groups). Another method (the finish-map one being tested,
  2026-10-11) replaces the method's rows and writes the same two; the framework's rows (`place_line.py`: paint,
  bake, check) do not change.
- **Today's method is g-texture** (round 4's best arm, EXPERIMENTAL): `split_batch.py` (free split rows),
  `split_batch_paid.py` (turntable, unlit, regions, both judges, masks; its own module so a free change never pays
  again), `g_texture.py` (asks, parts, the seed), `multiview.py`, `measure.py`, `paint.py`, `inside/turntable.py`.
  Only what g-texture uses is kept; the trial's arms, flat light, the round pages and GeoSAM2's fallback (no take had
  its guided split) are gone (their record: branch `surface-first`, rounds 1 to 4). Do not tune its internals while
  the finish-map method is tested (owner, 2026-10-11).
- **The judge is Gemini 3.1 Pro** (`tools/props/cloud/gemini_judge.py`, the models adapter's `gemini-judge`, its
  record in the judge rows' keys): temperature 0, an enum answer, one ask each, every request asked once and read
  back from google_spend's cache by its input's hash.
- **The finish registry is a store item** (`registry.py`; `registry/finishes/` and `registry/surfaces/` in the
  store): append-only, a finish group gets its library surface on first sight and keeps it; the owner's hub picks
  (`data/surfaces/finish-seed.json`, round six) are read first and never replaced; a new library surface a method
  proposes stands as first proposed. The paint reads it outside its key (an appended group never changes a given
  surface; each part records its group).
- **Per-place data is world data** (`surface_data.py`, `data/surfaces/<place>.json`): the takes a place splits (each
  split by one place only), the library name, the bake (the route's make_chunky job, model per take, entries the job
  lacks). A place with no file blocks at `split-inputs`; one with no `bake` blocks at `surfaces-bake` before
  anything is cleared. Picked rows (an inventory row with `pick`) are never listed: they keep their model and paint.
  A place with nothing to paint has a file with no takes and a `nothing` line saying why; its line has no surface
  rows (`Stage.applies`, `surface_data.paints`). A shared model is listed, split and baked by the place that claims
  it only (the other place's bake does not have it). Every world-1 place has its file (2026-10-11).
- **Gates never crash or pass on what is missing** (`surface_gates.guarded`: unknown with the missing file named). A
  model whose split mixes finishes is named in the split's fail and stops its place's line; once the owner waives it,
  the later rows leave that model out.
- **Painting is 3D parts plus the shared library, only.** A picture's colours never reach a model: pictures feed the
  regions, the split's vote and the judge (the owner rejected picture colours on 10-07 and 10-09).
- Steps needing trimesh run in the prop environment through their module's command line (`prop_env.py`), each make
  defined in its step's own module so that module is its code version. Tests: `surfaces_test.py` (the framework
  side, the framework's Python) and `surface_test.py` (the method's steps, handed to the prop environment).
