# score/stages/proposals/

The partition-proposals row (experimental, 2026-10-14): SAM 2.1's proposals on a new scene's concept views, one world
node, paid and cleared by the runner, so a new place's inventory is boxed from measured proposals before it lands (no
box is typed). `__init__.py`'s docstring has the record, the output and the gate.

- **Requests are world data** (`data/definitions/partitions.json`): each scene's views (pictures under the seeds
  folder) and why. The tiling and the merging are `tools/props/scene/partition.py`'s, unchanged; the masks are
  `tools/props/cloud/segment.py`'s.
- **The agent maps, the row measures.** The output's proposals are mapped to the scene's rows with `partition.py
  apply` (a drop needs its reason); the row never writes boxes itself.
- **Found artwork stays private.** A view may be the creator's found reference; it stays in the work folder and the
  store, never in the repository or on a public page.
- Run: `python -m score run world1 --stage partition-proposals --detach`. Test: `proposals_test.py` (a stand-in
  SAM 2.1, no spend).
