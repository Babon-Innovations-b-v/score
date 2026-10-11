# score/

The layered framework's core (PRD #6, the design of 2026-10-11): stages run by one runner, every output kept in one
store by its content's hash, gates that block on unknown, a review page per output, and an accept only the owner
gives. Today's tools in `tools/` move in here stage by stage as each stage is built; nothing moves before.

- **`checks/`** the gate rules every stage shares: `Verdict` (pass, fail or unknown, a reason, measures, findings),
  `Check` (a judge and the evidence it needs), `judge` (missing evidence is unknown without asking), `overall`
  (fail, else unknown, else pass; nothing judged is unknown), `regressions` (what got worse than the accepted one).
- **`store/`** the store over `tools/cloud/runtime/store.py`'s interface (a folder at `$PROPS_HOME/store` by
  default; nothing in the cloud): outputs as content-hashed files and listings, finish records, judgements per
  evidence state, evidence per check and output, the owner's accepts and spend yeses. Written once, never
  overwritten; checkouts are read-only copies (never links to the stored bytes), made again when changed; an
  agent's process cannot write the framework store's accepts, waivers or spend yeses. Its docstring has the key layout.
- **`graph/`** the runner: `Stage` (the stage table's row), `World`, `Runner.run/status/why/ticket`. A node's key
  hashes its computed code version (`_code.py`: its make's and checks' files and every repository module they
  import, inside functions and through `sys.path` folders too), parameters, seed, pinned models and every input.
- **`review/`** the review page of one output from its own record, and the owner's `accept` and `spend`
  (`python -m score.review ...`, refused without a terminal; `.claude/hooks/accept_guard.py` blocks agents).
- **`adapters/`** `models` (pinned images and models from `tools/cloud/images`), `compute` (the refusal, then
  `tools/cloud/runtime/submit.write_job`), `engines` (Blender: the blender image's job, or
  `tools/props/cloud/blender_cloud.run_elsewhere` after clearance). Wrapped, not rewritten.
- **`stages/`** the stage table (`python -m score.stages status|run|why <place> ...`). Step 0 holds the worked
  example: `assembly` on world 1's round-three stages as unverified seeds (placeholder and resting gates) and
  `complete`. World 1's record is `data/definitions/world.json`.

Rules:

- **Never write an accept, a waiver or a spend yes**, by any route. Build the page and ask the owner. The runner and
  every stage read the accepted output only; a new output lands beside it and never replaces it by itself.
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
