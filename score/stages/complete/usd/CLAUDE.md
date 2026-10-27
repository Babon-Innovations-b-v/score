# score/stages/complete/usd/

The USD correctness check: each place's composed stage (its accepted neighbours output, else its accepted assembly,
the stage complete judges) judged by SCORE's curated rule set over usd-validation-nvidia (Apache-2.0, a pinned pip
dependency; never `usd-exchange`, which ships its own `pxr`). Free and local: the store read through links to its
stored bytes (the library check's `stored.laid_out`), pxr and the validator only; no Blender, no cloud.

- **Standalone, not a gate of any row.** Nothing in a stage's code imports it, so no key moves; wiring it into a gate
  would move that stage's key and re-buy paid rows. The sync pass runs it (`score/dashboard/sync/client.py`
  `usd_sweep`) and the cockpit reads `WORK/checks/usd/<place>/findings.json` (`state/local.py` `check_findings`):
  its `findings` (the errors) are the place's problems, while the output it judged stays accepted; `warnings` are
  kept beside them, never listed as problems.
- **The rule set is SCORE's, named in `rules.py`** (ERRORS, WARNINGS, by class name: a package update that drops one
  fails loudly). The package's default set fails SCORE's good stage: `UpAxisZChecker` is off (SCORE is Y up, metres),
  the ASCII-size and weld rules are out (a seam needs split vertices); normals, manifold, zero-area faces and
  unindexed primvars are warnings. SCORE's own rule: no triangle-mesh collider under a dynamic rigid body
  (`TriangleColliderOnDynamicBody`; the package misses it).
- **Opened in SCORE's resolver context** (`judged.opened`: the default resolver anchored at the root file), so a
  missing reference is a real one.
- **Fix a finding in the writer that wrote it**, never in the check and never by hand in an output.
- Run: `.venv/bin/python -m score.stages.complete.usd [--place P ...] [--out FOLDER]`, about a second a place;
  last line its summary. Test: `test_the_rule_set_passes_a_good_stage_and_finds_each_bad_one.py` (its good and bad
  stages written in the test; a store of its own).
