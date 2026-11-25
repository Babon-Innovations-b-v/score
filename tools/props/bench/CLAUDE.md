# tools/props/bench/

The prop benchmark (#163, PRD #159, design on #162): the prop pipeline scored step by step against adopted NVIDIA
SimReady models (score_lib `model/simready_*`). Each part is its own module directory with its own test.

- `truth/`: the set (`data/checks/prop-bench-set.json`, #162's rule) and each object's truth read from its entry.
- `calibrate/`: the free calibration pass: every measure on an exact copy of each truth and on its kind's other
  assets, the route's checks on the truths; the bars in `measures/` are set from it.
- `run/`: each object drawn as its close-up (Blender on this PC's card) and made again by both routes from it, every
  step's output a store object.
- `joints/`: a made model's moving parts run in Newton (#177): its parts step's parted GLB staged, joined, driven
  to their limits and measured.
- **Nothing is taken into score_lib** and nothing reads it but through `score.library` and `library_files`; the
  benchmark ids are held out from the route's own library lookups.
- **Results live in the store bucket** (runner rows, `score/store/offload`): inputs, each step's model, `measures.json`,
  `summary.json`. The repo holds only the set file; a disk only capped caches and job scratch.
- **The held-out split is never looked at while tuning**; fixes are developed on the tune split only.
