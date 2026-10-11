# score/

The layered framework's core (PRD #6, the design of 2026-10-11): stages run by one runner, every output kept in one
store by its content's hash, gates that block on unknown, a review page per output, and accepts and paid runs the
runner gives by the gates' answers (the owner's answers of 2026-10-11: his picks are made, from concept and style on
everything runs automatically, no spend limit, spend logically). Today's tools in `tools/` move in here stage by
stage as each stage is built; nothing moves before.

- **`checks/`** the gate rules every stage shares: `Verdict` (pass, fail or unknown, a reason, measures, findings),
  `Check` (a judge and the evidence it needs), `judge` (missing evidence is unknown without asking), `overall`
  (fail, else unknown, else pass; nothing judged is unknown), `regressions` (what got worse than the accepted one).
- **`contracts/`** every output's schema, version and units, checked both ways: `Contract` (a schema, its version,
  the house units it uses, its faults check; other units than metres, seconds, degrees and Y up are refused),
  `stamp` (the runner checks an output and writes `contract.json` into it before storing; one off its contract is
  not stored), `expect` (a reader refuses an input of another schema or version, or with no stamp). The schemas in
  use: `OPENUSD_STAGE` (one root stage, metres, Y up, a default prim) and `PLACE_MANIFEST`.
- **`store/`** the store over `tools/cloud/runtime/store.py`'s interface (a folder at `$PROPS_HOME/store` by
  default; nothing in the cloud): outputs as content-hashed files and listings, finish records, judgements per
  evidence state, evidence per check and output, accepts (the runner's automatic ones and the owner's), the owner's
  rejects, waivers and spend yeses, the runner's clearances, the world's finish registry (append-only). Written
  once, never overwritten, and safe for lines side by side (each write lands whole through a `.partial` file of its
  own process; a write-once key is linked into place, so a second writer is refused); checkouts are read-only copies (never links to the stored bytes), made again
  when changed; an agent's process cannot write the framework
  store's owner areas (the runner's automatic accept excepted). Its docstring has the key layout.
- **`python -m score run <world> [--place P ...] [--stage S ...] [--jobs N] [--detach]`** and **`python -m score
  status [<world>]`** (`__main__.py`; `--stage` keeps only those stages and what they read): the runner drives every line (the world's own nodes, then each place's) to its end with no agent
  in the loop (`Runner.drive`, `Runner.lines`), the lines side by side: each node in a forked process of its own, at
  most `--jobs` at once (default 8), so a line waiting on a cloud step holds up no other, and a world node every line
  reads is made once. It starts each node the moment the nodes it reads stand accepted,
  gathers a gate's missing evidence itself (`Stage.gatherers`; a paid one cleared like a paid stage, and only when
  nothing else blocks the output) and waits on every cloud step itself. A node that does not end accepted stops its
  own line only and leaves a plain fault report, `faults/<node>.txt` beside the store (`$PROPS_HOME/store/`): the
  cause, every blocking check's reason, measures and findings, its log's tail (`logs/<node>.log`).
- **`graph/`** the runner: `Stage` (the stage table's row; a paid one names its estimate, `euros`; `applies`
  leaves out the places its world data says it has nothing to do for), `World`,
  `Runner.run/drive/status/lines/why/ticket/stale`. `run` accepts an output by itself when every gate passed
  (waivers counted), nothing got worse than the accepted output and the owner never rejected it, and makes a paid
  stage inside its clearance's ticket; `stale` (shown in status) names the earlier nodes whose accepted output moved
  since. A node's key hashes its computed code version (`_code.py`: its make's and checks' files and every repository module they
  import, inside functions and through `sys.path` folders too), parameters, seed, pinned models and every input.
- **`review/`** the review page of one output from its own record (who accepted it, and how the owner rejects it);
  `accept_automatically` (the runner's); and the owner's `reject` (the accepted output moves back to the one accepted
  before, later nodes that read it go stale, the runner never takes it again), `accept` (his own, a worse one with his
  reason), `waive` (one check passes for one key, with his reason; it ends when the key changes and shows on the page
  and in status) and `spend` (his override, a yes for a run outside the runner, node `override`). `python -m
  score.review ...` refuses those without a terminal, the store refuses their writes in an agent's process, and
  `.claude/hooks/accept_guard.py` blocks the other routes: a barrier, not a lock.
- **`adapters/`** `models` (pinned images and models from `tools/cloud/images`), `compute` (`clearance`: the runner's
  ticket for a node whose inputs passed and stand accepted, when the month's ceiling has room for the estimate over
  the ledger and every open reservation, cleared under one lock so two lines never both spend the last euros; kept
  in the store; then `tools/cloud/runtime/submit.write_job`; `require_cleared` at every rent point), `engines`
  (Blender: the blender image's job, or `tools/props/cloud/blender_cloud.run_elsewhere` after clearance). Wrapped, not rewritten.
- **`stages/`** the stage table (`python -m score.stages status|run|why <place> ...`). Step 0 holds the worked
  example: `assembly` on world 1's round-three stages as unverified seeds (placeholder and resting gates) and
  `complete`. `terrain` (one world node, paid) makes every ground from its plan in `data/ground/plan/`, gated on
  scale, slope, ground under objects and openings (its overlay). `surfaces` (step 1) is each place's own line of
  rows, the finish-map method to checked bake (its overlay; per-place data in
  `data/surfaces/`). World 1's record is `data/definitions/world.json`.

Rules:

- **Agents never walk a line by hand.** Start it with `python -m score run <world> [--place P] --detach` under the
  Bash tool's `run_in_background`, then end the turn or do other work: its one result line wakes you. Never start
  its steps one by one, never poll a cloud step. Step in only on a fault report (the result line exits 1 and
  `python -m score status` names it): read that file, put the cause right, run the line again.
- **Never write a reject, a waiver, a spend yes, a clearance or an accept by hand**, by any route, and never ask the
  owner to accept or to say yes to a spend: run the stages, and the runner accepts what passed and got no worse and
  clears what may spend. The runner and every stage read the accepted output only; a new output that failed, is
  unknown or got worse lands beside it and waits on its page for the owner.
- **Every stage names its output's contract** (`Stage.contract`) and, in `after`, the (schema, version) it was
  written for of each stage it reads. A schema change is a new version, never an edit of the old one.
- **A gate never passes on missing evidence.** A check that needs evidence names it (`Check.evidence`); a judge that
  cannot tell answers unknown. Unknown blocks like fail.
- **Method choices live in the stage's code or in accepted world data**; a stage's parameters are its true inputs.
  Every file a stage or its checks read is a declared input (`Stage.files`), or its node will not rerun when it
  changes. Over-declare rather than miss one (assembly declares the whole inventory folder for this reason).
- **Old outputs come in as unverified seeds** (`origin.json` in the output, a banner on the page), judged by the
  stage's own gates before anyone may accept them. A seed's references to other places (`/<place>/Places`) do not
  resolve in the store, where each place is its own node; OpenUSD warns about them and no gate reads them.
- **No `/tmp`, no hand-named folders** for outputs: a stage writes into the folder the runner gives it, and the
  store keeps the result. Tests use their own store (`Store.in_folder`); the worked example's test keeps it under
  `$PROPS_HOME/store-tests` and removes it.
- Tests are plain scripts beside each module (`make tests` runs `score/**/*_test.py`), driving the public interface.
