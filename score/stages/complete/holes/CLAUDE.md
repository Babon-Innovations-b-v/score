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
  code work in words, with no price. `holes_test.py` keeps every stage it names in the table (or the ship kits' own).
- **A lost input is a place hole with its code work** (`inputs.py`, 2026-10-19: the old disk's work folder went with
  it): every node's declared world file under the work folder or in the repository that is not there, read from the
  stage table (the repository's data only), grouped by what it is (earth seed, ship seed, views copy, Pixal3D take, a
  folder), and the owner's reference pictures its concept views name. A take some place's pixal row makes is that
  node's hole, priced through it, never code work. The world's own nodes' go in `world/findings.json` (pseudo-place
  `world`, which the cockpit's total reads); a lost input's id names the thing, so the totals count it once however
  many places read it. Never fetched back as a loose file: an old paid output comes back only through
  `store/restore`'s key match.
- **A layer without models adds its own holes** (`layers.py`, #29): its `holes(place, data)` in `SOURCES`, worked out
  free from the place's records by the layer itself (sound: `score/stages/sound/needs.py`; light and sky:
  `score/stages/light/needs.py`; ground: `score/stages/terrain/needs.py`, #27), each a place hole with a
  generic id (`place:<layer>:<kind>:<item>`), source `layer:<layer>`, and the layer's node or its work. Never a
  list of places or objects written here.
- **The runner prices the holes, the cockpit only sums** (`price.py`, `score price world1 --holes --json`, free and
  local, minutes: run it in the background): each hole's chain (`score/graph/chain.py`: what does not stand before
  its node, and what the place's completion reads after it), each paid node priced once by `compute.run_price` with
  the units its stage's forecast rule counts (`data/costs/per-unit.json` `forecast`, each model once), written to
  `WORK/checks/holes-price/<world>.json` with the commit and per-unit prices it was made on. It reads the findings
  (the world's too) only while the outputs they stood over stay accepted; a place never checked, a stale one and a
  node outside every table are named in the record, never dropped. A ship kit (`ship_kit@<place>`, its own table:
  `price.own_tables`) is priced the same way on its own row, its chain the node alone. The rows waiting on their place's prop data get
  the prop route (every paid row up to `likeness`) priced apart, after that work, and so is the code work whose make
  is Pixal3D's (`code_work`: a lost take one model, at pixal's per unit). A missing rough model is no code work
  since its row is in the table: its route hole names `rough-model@<place>`, priced through its chain. A node with no
  measured price is unknown, its row's flat estimate never carried (owner, 2026-10-20). Nothing here buys: a Blocked
  node is priced, never dropped, and the plan and the run keep their refusals.
- **The runner's ETA is `schedule.py`** (#14): `schedule(nodes, edges, jobs, run_cap)` walks a plan's rows in
  dependency order (the stage table's order breaking ties), at most `jobs` rows at once (free ones too, as the
  runner's drive) and never more than `run_cap` cards held, each row on its measured minutes (`timed_row`: a paid
  row's from `compute.run_price`, a free row's from `compute.node_minutes`, read once a plan). A row without minutes
  is listed with why and walked as no time, so the walk is only a lower bound (`at_least_minutes`); likely and high
  are given only when every row has minutes. `price.plan_eta` runs it over every chain's and after-work row, and
  `score price <environment> --holes` writes it as the record's `eta`. The cockpit's launch guard still sums lines
  itself (`score/dashboard/state/costs.py` `time_of`); moving it onto `eta` is the cockpit's remake track (#10).
- **The remake's plan is the runner's too** (`milestones.py`, in the same record): a hole's chain and each place's
  line run past its completion gate to the line's ends (`chain.line_chain`: the nodes no node reads, the films and
  the hand-over; an optional read walked like any other, so the people are in), and the environment's own line;
  every paid node of them priced in the totals. `milestones` orders every node by a dependency sort of the reads,
  shapes first (ground, the shell's concept, plan and rough model, the split, the inside places' own, then what each
  place holds, completion, after it), the table's order only breaking ties; each milestone its stages, paid nodes,
  measured euros, the table's set budgets apart (labelled set, never summed), each unknown node with why, the
  holes' code work waiting at it (a lost input at its earliest reader) and the owner's steps (the month's books at
  the first paid one), then the environment's film (no row: unpriced) and the owner's approval of the final video.
  A route step whose rows the table lacks (`STEP_STAGES`, its names from the table's constants) is still a milestone,
  its missing rows named, unpriced with why when it has no node.
  No plan is written by hand or by an agent; the cockpit only shows it. Test: `milestones_test.py`.
- Run: `.venv/bin/python -m score.stages.complete.holes [--place P ...]`, seconds a place. Test: `holes_test.py`.
