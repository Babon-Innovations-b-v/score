# score/stages/library/

The library rows (`__init__.py`'s docstring has the make, `checks.py`'s the gate, `handover.py`'s the report's
shape): `library@<place>` and `library-world` hand every accepted output of an environment to the creator's library, so what
is in an environment shows up in the library by construction, never by an agent's hand.

- **score never imports the library.** It runs the library's own command (`backend.py`, the template
  `SCORE_LIB_HANDOVER`) and reads only the report it writes, `handover.json`. No provider, host or company name in
  the template, the code or the data: every setting is an environment variable, else its default (the score_lib
  checkout beside score; the blob store the cloud backend's `object_store()`, its key from the secret store, handed
  to the command in its environment only, never a settings file: owner, 2026-10-20).
- **The route** (`route`, `runner_route`): the route stages' code versions and contracts hashed, a callable param
  the runner works out, so a new route re-keys these rows and the handover (`--route`) stamps it into every entry's
  provenance; prepare's library match reads it. Never a hand-bumped constant.
- **Drafts only.** The node never locks, withdraws or deletes an entry; locking is the owner's (the cockpit's library
  actions).
- **The rows are read by nothing**, so a change here re-keys these two rows alone: nothing is bought again. Never
  make another row read them, and never fold their gate into `complete`: demo-film (paid) reads complete.
- **No paid preview of a library item** (owner, 2026-10-22: "you should just never do it that way ... thats
  waste"): the cockpit's Library page shows each item live from its web copy, free; the `library-clips` row (a
  Cycles clip per new item on an L4) was retired.
- **The report's shape is a contract both ways.** A change is a new version (`handover.VERSION`), never an edit;
  `handover_example.json` holds one full report, and the library repository keeps its own copy of the shape.
- **The library repository names files in this one.** Its `definitions/algorithms/*.toml` list score paths (roots,
  constants, tests) read at the commit its world pins; deleting or renaming such a file under `score/` or `tools/`
  breaks that definition at the next pin bump. Say so in the commit, and fix the definition in the library repository.
- **`handed`** holds an output through what it was made into (owner's rule: everything shown comes from the library, not every intermediate file): one no exporter takes on its own (a finish route's list, a light layer) passes when an entry holds a row read here made from it (reads.json `into`, from the table's `after` in the `made into` param), and a world output the places' rows are made from (`beyond`) is held by those places' library nodes. Never a per-place exception for it.
- **`traced`** wraps the library-finish check (`score/stages/complete/library`, its overlay) in `traced.py`, taken
  as it landed: the place's assembled stage traced against the library folder after the handover and the store's
  accepted bakes, read only. A change of that check's rules is made there, never here.
- **A library-free environment** is an owner's dated decision in `data/checks/library-free.json`; write one only on his
  word.
- **The invariant** (`invariant.py`, pure; `sweep.py` gathers and writes): each library node's accepted handover
  against the library's entries and the store's accepted outputs, one plain problem a mismatch (not handed, not in
  the library, made from an output that moved on, shown nowhere, not pushed). Every cockpit sync pass runs the sweep
  first (`score/dashboard/sync/client.py` `library_sweep`) and writes `WORK/checks/library-handover/<place>/
  findings.json`, which the place pages show as problems; by hand: `.venv/bin/python -m score.stages.library.sweep`.
  Neither is imported by the rows, so editing them re-keys nothing. The export side (library rows against the
  export's `library/entries.json`) is not compared yet.
- **`pictures.py`** fetches the pictures the cockpit shows (every kind's by default: the place tiles and the Library
  screen's thumbnails) into the library cache through the library's own command (`library_files.from_library`,
  hash-checked), and the small files an item page's viewer plays (`viewed`: a light web copy, a model's close-up, a surface's material
  and print, a sound's first takes, an effect's settings, a light's OpenUSD), so the cockpit and its export have their
  bytes with no blob folder; each sync pass runs it (`score/dashboard/sync/client.py` `library_pictures`). A file the
  library lost is counted and named in its line, never stops the others; one the blob store answered 404 for is
  marked `<file>.lost` beside it and not asked for again until its entry names other bytes. Never a row. By hand: `.venv/bin/python -m score.stages.library.pictures [--kind place ...]`.
- **`demos.py`** makes each library algorithm's demo for its cockpit page from real data, one module an algorithm in
  `demo/` (its overlay has the shape and the rules), into the library cache's `demos.json`; each sync pass runs it
  (`score/dashboard/sync/client.py` `library_demos`), free and local, its files fetched once like the pictures. One
  with no real example (a withdrawn entry's included: the old places' layers, 2026-10-21), or that fails, is named in
  its line and on its page, never stops the others. Never a row.
  By hand: `.venv/bin/python -m score.stages.library.demos [--only <algorithm id> ...]`.
- `library_test.py` drives the runner over a toy table with a fake library command; `invariant_test.py` each
  mismatch on small fixed sets.
