# score/stages/complete/materials/

The materials checks (2026-10-18, the materials audit on PRD #10): why props and code-built objects look like
different environments when their finishes are the same library surface. Two checks, free and local: pxr, numpy and PIL
on each place's accepted assembly, read only, no Blender, no cloud.

- `texel.py` texture detail near cameras against the room's kit (px/m), `borders.py` finish-border raggedness per
  part. Each module's docstring has its rule and its numbers. (`kit_age.py`, kit bakes older than their bake code,
  went with the code fallback's kit bake on 2026-10-22: every piece is the runner's own, keyed by its code.)
- **Standalone, not a gate**, as the library check beside it. The cockpit reads its findings
  (`score/dashboard/state/local.py` `check_findings`, any `WORK/checks/<check>/<place>/findings.json`) as the place's
  problems with their pictures, only while the assembly and film outputs it judged are still the accepted ones. No
  stage imports this package, so no row's key moves with it.
- `measure.py` gathers (store to evidence folder, about a minute a big place), `judge.py` and the two rule modules
  judge evidence alone (no store), `pictures.py` draws from the linked assembly. Keep them apart: the tests'
  fixtures are evidence alone.
- **Never the store's checkout**: it writes into the store's cache. `assets.linked` links the stored files into the
  check's own folder instead.
- Run: `.venv/bin/python -m score.stages.complete.materials [--place P] [--out FOLDER] [--judge-only]` under
  `systemd-run --user --scope -q -p MemoryMax=16G -p CPUQuota=400%`, in the background; it writes
  `WORK/checks/materials/<place>/` and `contact_sheet.png`.
- The fixtures of real evidence (`data/checks/materials/<place>.json.gz`, the old concepts' hangar, cockpit and
  garage) were retired with those places on 2026-10-21; the test holds the measures on meshes of known shape. Measure
  a place again with `measure.gather` when a rule needs a case of real evidence.
- Test: `test_finish_borders_and_texture_detail_measure_true_on_shapes_of_known_answer.py`.
