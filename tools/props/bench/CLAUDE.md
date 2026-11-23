# tools/props/bench/

The prop benchmark (#163, PRD #159, design on #162): the prop pipeline scored step by step against adopted NVIDIA
SimReady models (score_lib `model/simready_*`). Each part is its own module directory with its own test.

- `truth/`: the set (`data/checks/prop-bench-set.json`, #162's rule) and each object's truth read from its entry.
- **Nothing is taken into score_lib** and nothing reads it but through `score.library` and `library_files`; the
  benchmark ids are held out from the route's own library lookups.
- **Results live in the store bucket** (runner rows, `score/store/offload`): inputs, each step's model, `measures.json`,
  `summary.json`. The repo holds only the set file; a disk only capped caches and job scratch.
- **The held-out split is never looked at while tuning**; fixes are developed on the tune split only.
