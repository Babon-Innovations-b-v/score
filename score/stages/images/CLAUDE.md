# score/stages/images/

The images environment (2026-10-12): each job image of `tools/cloud/images` with a proof plan (`<kind>/prove.json`) rebuilt
and proved by the runner, as an environment of its own with its own stage table (`stages.TABLES`), so maintenance builds are
cleared against the month's ceiling like any paid row, with no owner override. The module docstring is the contract.

- `image-pins-<kind>` is free: pins exact and hashed, they resolve (uv), `build_test.py` passes, and `models.json` and
  the Dockerfile's instructions match the published build's (the folder at the commit that first named its tag).
- `image-proof-<kind>` is paid (the plan's `euros`): `build.py` and `prove.py` write into a copy of images.json in the
  output, never the repository's. Its gates: every planned job ran, and the kind's own output check (`PROOF_CHECKS`;
  a kind without one answers unknown, so add its check with its plan).
- `python -m score images publish <kind>` writes an accepted proof's record into images.json. Before pushing a
  publish, show that no environment 1 node's code, files or models moved (images.json is read per kind, so a kind environment 1
  pins moves its nodes: publish those only between environment runs).
- Nothing in environment 1's stages imports this package; keep it so (its code would then enter their code versions).
