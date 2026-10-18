# score/stages/complete/materials/

The materials checks (2026-10-18, the materials audit on PRD #10): why props and code-built objects look like
different worlds when their finishes are the same library surface. Three checks, free and local: pxr, numpy and PIL
on each place's accepted assembly, read only, no Blender, no cloud.

- `texel.py` texture detail near cameras against the room's kit (px/m), `borders.py` finish-border raggedness per
  part, `kit_age.py` kit bakes older than the bake code that made them. Each module's docstring has its rule and
  its numbers.
- **Standalone, not a gate**, as the library check beside it. The cockpit reads its findings
  (`score/dashboard/state/local.py` `check_findings`, any `WORK/checks/<check>/<place>/findings.json`) as the place's
  problems with their pictures, only while the assembly and film outputs it judged are still the accepted ones. No
  stage imports this package, so no row's key moves with it.
- `measure.py` gathers (store to evidence folder, about a minute a big place), `judge.py` and the three rule modules
  judge evidence alone (no store), `pictures.py` draws from the linked assembly. Keep them apart: the tests'
  fixtures are evidence alone.
- **Never the store's checkout**: it writes into the store's cache. `assets.linked` links the stored files into the
  check's own folder instead.
- Run: `.venv/bin/python -m score.stages.complete.materials [--place P] [--out FOLDER] [--judge-only]` under
  `systemd-run --user --scope -q -p MemoryMax=16G -p CPUQuota=400%`, in the background; it writes
  `WORK/checks/materials/<place>/` and `contact_sheet.png`.
- The fixtures `data/checks/materials/<place>.json.gz` are real evidence (hangar fails all three, the cockpit's
  consoles hold the kit's detail, the garage's wheel stand has clean borders); measure again with `measure.gather`
  only when a rule needs a case they lack.
- Test: `materials_test.py`.
