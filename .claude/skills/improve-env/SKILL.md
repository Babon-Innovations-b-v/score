---
name: improve-env
description: Brute-force an environment toward its locked concepts in rounds, each round a large workflow that scores every place's still against its concept, finds the shared causes and lands one fix stream per cause, then a free PC run and new stills. Use when the owner runs /improve-env.
disable-model-invocation: true
---

# Improve env

A *ratchet*: each round measures every place against its locked concept, fixes the shared causes it finds, remakes the scenes for free on this PC and measures again. The score only counts when it is measured; the loop stops when it stops rising. The owner asked for it on 2026-11-15: "a massive workflow, with the new fable model, ... using all the tools the framework has to offer by now, and just gets the simple goal, of making the env better, following our rules and objectives".

Argument: the environment (default `world1`, env1). Its rework issue holds every round (env1: #128).

## A round

1. **Stills.** Make a free 1080p still of every place's first film frame from the PC store, into a fresh scratch folder `$STILLS` under the job's tmp (never `/tmp`):
   - per place, side by side: `STILLS=<dir> SCORE_REPO=<checkout at main> bash scripts/stills/prep.sh <place>` (compose and plan, read-only);
   - then `render.py <place> ...` in the background with `tools/cloud/detached.py --`: Blender one place at a time on the card queue.
   Done when `$STILLS/out/` holds a JPEG for every place or `render.jsonl` names why one has none.
2. **Workflow.** Run `scripts/round.workflow.js` through the Workflow tool (`scriptPath`), args `{environment, places, stills: $STILLS, out: <job tmp>/improve-<round>, issue, round, streams: 8, model: "fable", notes}`. It compares (one agent per four places), plans the causes and lands up to 8 fix streams, each in its own worktree. Done when it returns.
3. **Record.** Post one comment on the issue: the round's mean and per-place scores against the last round, the commits landed, each stream's undone work, the decisions agents made (one line each), and the `owner` list with prices. Done when the comment is posted.
4. **Remake, free.** Bring the PC store onto the new main: re-readings and plan writings where the round changed reading or plan code (the owner's standing allowance), `python -m score.review.plans_pass refit <place>` for each place, then a free PC run of the environment (`tools/cloud/this_pc.py`), free only. Where a run session owns this PC, hand it these steps by message instead. Watch the run to its end with Monitor; done when every place has reached its lit stage again or names its fault.
5. **Next round** from step 1.

## When to stop

- The mean has not risen for two rounds: stop and write what blocks it (usually an owner item).
- The mean is above 8 with no place under 6: stop; the film can be planned.
- The owner says stop.

## Rules that bite here

- **Free unless he said yes.** Owner items (paid model remakes, a concept against a game number, bought batches) wait on the issue with their price; the loop never buys. Remakes that cost money come only under an approved batch (root `CLAUDE.md`, Autonomy boundaries).
- **Paid model rows stay put.** A fix that would move the keys of picture-made models, people-dress or model bakes is found another way or left for the owner (the workflow brief repeats it).
- **One run on one commit.** No pushes while the PC remakes; a round's streams land before step 4 starts.
- **Measure the same way every round.** The compare prompt's 0-10 scale is fixed; never change it mid-loop.
- Each round's scratch, causes and scores stay in its `out` folder; the issue gets only the summary.
