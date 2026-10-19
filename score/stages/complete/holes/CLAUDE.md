# score/stages/complete/holes/

Holes (CONTEXT.md "hole", issue #12): what each place's route still needs, shown in its OpenUSD scene and in the
creator cockpit. A scene inventory row with nothing made for it, a made object a written fault names, a step of the
route the place has not been through (its concept, plan, rough model). Free and local: the store and the
environment's data read, pxr only; no Blender, no cloud, nothing judged. `__main__.py`'s docstring has the files and
findings.json's contract. Bible: `architecture/components`.

- **Standalone, never a gate or a row.** Nothing in complete's stage code imports it, so no key moves; the cockpit
  reads `WORK/checks/holes/<place>/findings.json` (`score/dashboard/state/local.py` `holes`) while the outputs it
  stood over stay accepted. `sync/client.py` runs it after the library sweep.
- **An overlay, never inside the accepted stage.** `holes.usda` sublayers `layers/holes.usda` over the accepted stage
  laid out as links (`stage/`). Writing the boxes into the assembly or `tools/usd/export.py` would move the keys of
  assembly, complete and every paid row after them.
- **A box is never a made object.** Missing objects carry `score:hole:*`, never `score:row`: the rows, contents,
  library and reach checks count `score:row`. Their boxes are purpose guide, so no render or game export draws them.
- **No position is made up.** A box stands at the inventory's spot, the kit's piece, a wall of the room's layout or
  its parent's top; anything else is unplaced (no transform, no low and high). `rows.py`'s docstring has the rules.
- **Nothing found is dropped.** A fault whose object is on no prim keeps its hole with no prim. A named gap is a
  decided fault: its reason is the work, never a node to buy.
- **What fills a hole is one table** (`fill.py`): a stage of the table that runs for the place (its node), else the
  code work in words. No price here: the cockpit joins the basket's prices at read time. `holes_test.py` keeps every
  stage it names in the table (or the ship kits' own).
- **A lost input is a place hole with its code work** (`inputs.py`, 2026-10-19: the old disk's work folder went with
  it): every place node's declared world file under the work folder or in the repository that is not there, read
  from the stage table (the repository's data only), grouped by what it is (earth seed, ship seed, views copy,
  Pixal3D take, a folder), and the owner's reference pictures its concept views name. Never fetched back as a loose
  file: an old paid output comes back only through `store/restore`'s key match.
- Run: `.venv/bin/python -m score.stages.complete.holes [--place P ...]`, seconds a place. Test: `holes_test.py`.
