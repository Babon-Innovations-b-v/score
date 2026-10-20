# score/stages/complete/library/

The library check (owner's hard rule, 2026-10-18): everything a place shows comes from the library (score_lib) or is a
written exception. Free and local: a place's accepted assembly read from the store through links to its stored
bytes (never a checkout, never a write), the library read from SCORE_LIB_ROOT, the film's frames for the pictures;
no Blender, no cloud. `trace.py`'s docstring has the tracing rules. Bible: `architecture/components`.

- **Standalone, not a gate of any row.** Wiring it into a stage would move that stage's key and re-buy paid rows;
  the cockpit reads its findings instead (`score/dashboard/state/local.py` `check_findings`, any
  `WORK/checks/<check>/<place>/findings.json`), as the place's problems with their pictures, and only while the
  assembly it judged is still the accepted one.
- **Two aspects a thing.** Its source (model, place, ground, sky, structure, character, effect, light, sound, loose
  geometry) traces by `score:library` (an entry's address, the attribute the export writes), a place by name, a
  model by its gltf (`score:model_sha256`), the prim an entry's provenance names (an effect entry names every placement
  of its one effect, `placements`), or the content hash of a file it is
  made of. Its finishes (each bound material once) trace by `score:library`, a library surface it names, or its
  model's finish record (an accepted bake that paints every part from the library: `stored.BAKES`). A baked texture
  nothing names, a picture's texture, a constant colour or no material is a finding.
- **Exceptions are data, never code**: `data/checks/library-exceptions.json` (`exceptions.py` has the fields). One
  without a reason or an owner refuses the whole file. Only the owner allows one; an agent never writes one for him.
- **No library code and no entry data here**: score is public, the library private. `entries.py` reads entry.json
  files the way the cockpit's `state/library.py` does; tests write a temp library.
- Run: `SCORE_LIB_ROOT=<library> .venv/bin/python -m score.stages.complete.library [--place P] [--out FOLDER]
  [--no-pictures]`, in the background (about 20 s a place; the pxr warnings about neighbours it does not lay out go
  to stderr). It writes `WORK/checks/library/<place>/` (rows.json, findings.json, marks/) and summary.json.
- Fixtures: `data/checks/library/bad.usda` (a picture's texture, a default grey, a model no entry holds: fails) and
  `good.usda` (passes). Test: `library_test.py`.
