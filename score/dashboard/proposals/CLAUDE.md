# score/dashboard/proposals/

A fix branch's proposal for one place: the shopping list's item, made for free on the store's machine
(`python -m score.dashboard propose <branch> <place>`). Layout and fields: `records.py`; the run: `propose.py`;
`finish.py` prices its paid part (`score price` through the backend, per commit), draws its own stills when it was
made without them, and its before stills (the same cameras on the place as it stands accepted), run by propose, by
`proposals-finish`, and (price only) by every sync pass. A department gives its proposal the owner's words with `python -m score.dashboard proposal-words <branch>
<place> --says "the fault this fixes, as he sees it" [--ask "..." --recommend "..."]`; they survive a rerun.

Rules:

- **Read the store, never write it.** `assemble.py` runs inside the branch's scratch checkout over an `Overlay`
  store: reads fall through to `$PROPS_HOME/store/objects`, every write (blobs, outputs, records, judgements, cache,
  locks) lands in `$SCORE_DASHBOARD_HOME/proposals-work/store`. Nothing is accepted; nothing is bought.
- **Free only.** A paid row, or one on pinned images, is never made here: its accepted output stands in, named "needs
  the paid batch". No cloud call, no `score run`, no clearance. Stills are one small local Blender job (640x360,
  4 threads, under the machine's one-heavy-job lock through `tools/blender/session.py batch`).
- **assemble.py is loaded by path** with the branch's checkout first on `sys.path`, so it imports only what every
  branch has (`score.graph`, `score.store`, `score.stages`, `score.contracts`), never `score.dashboard`. The three
  ways a node is taken are named in both `assemble.py` and `records.py`; a test holds them equal.
- **records.py stays light**: plain files only, read by the hosted process too (no store, no stages, no numpy).
- Tests: `score/dashboard/tests/proposals_test.py` (a toy stage table over a temp store; the real store is never
  touched).
