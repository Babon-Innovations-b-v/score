# score/dashboard/proposals/

The basket's details (CONTEXT.md: basket, basket item): what a run on main would buy, grouped into items, each with
details made for free on the store's machine before anything is bought (`python -m score.dashboard basket`, in the
background: the runner's plan of the whole environment takes minutes). Layout and fields: `records.py`; the command:
`make.py`; the free after and each paid node's inputs: `assemble.py`; the after's 3D copy and what changes:
`details.py`. A department declares an item, its words and its questions with `python -m score.dashboard basket-item
<id> --title ... --says ... --node '<pattern>' --picture ... --ask ... --recommend ...` (kept across makes; an item
may span places); the owner's answers are in `answers.json` (`python -m score.dashboard basket-answers`). The
benchmarks are one item, "Benchmarks" (`benchmarks.py`, #21): prepare's listed benchmarks at prepare's estimate,
written into the index by each sync pass and each make, launched by the checkout as their own batch.

Rules:

- **Read the store, never write it.** `assemble.py` runs in a subprocess over an `Overlay` store: reads fall through
  to `$PROPS_HOME/store/objects`, every write (blobs, outputs, records, judgements, cache, locks) lands in
  `$SCORE_DASHBOARD_HOME/proposals-work/store`. Nothing is accepted; nothing is bought.
- **Free only.** A paid row, or one on pinned images, is never made here: its accepted output stands in, named "needs
  the paid batch". No cloud call, no `score run`, no clearance, no Blender render: the after is shown as a 3D web copy
  (web3d/convert.py) of the free assembly, the before is the place's own web copy.
- **What changes is read, not written by hand.** `details.py` compares the two OpenUSD stages (the accepted one and
  the free after, linked the same way): objects added, removed, moved, reshaped, refinished (their bound materials
  and inputs, textures by blob), lamps, sounds, the scene record's cameras; each with its layer and box for the
  viewer's outlines. Where nothing changes for free, the item shows what its paid steps would be made from.
- **Prices are the runner's** (`score plan`'s buys, C19); a node never measured is said apart as a guess.
- **`--plan-only` assembles no place**: the plan and its items (with the plan's missing inputs and refusal) only,
  `plan_only` in the index. Use it whenever a place's free rows before its first paid one could run heavy local work
  or cannot stand (after the store's loss, 2026-10-19, every place's assembly fails at its first unmade paid node).
- **records.py stays light**: plain files only, read by the hosted process too (no store, no stages, no numpy). The
  three ways a node is taken are named in both `assemble.py` and `records.py`; a test holds them equal.
- Tests: `proposals/test_a_basket_shows_what_a_run_on_main_would_buy.py` (a toy stage table over a temp store; the real store is never
  touched) and `score/dashboard/tests/basket_test.py` (the pages, the choices, the answers, the checkout's queue).
