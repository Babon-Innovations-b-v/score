# SCORE

**SCORE: A Framework for Synthesizing Complete, Owned, Responsive Environments.**

SCORE turns a creator's picks (references, a concept, a style) into a complete world a game engine
or simulator loads: every object its own model, rooms with collision, surfaces from one shared
library, sound for every surface and object, and nothing in it the creator does not own. It works
offline: coding agents and open models do the work in cloud batches, cheap checks
run before every paid step, and the creator decides at a few fixed points.

The creator writes the score; coding agents and open tools play it.

## What is here now

- **The paper**, a first full draft: [`paper/out/score.pdf`](paper/out/score.pdf). Its one source
  is [`paper/source/score.md`](paper/source/score.md); an arXiv-ready LaTeX tree is generated
  from it in [`paper/arxiv/`](paper/arxiv/).
- **The framework's code** is not here yet. It runs today inside its first user, the game 2099,
  and moves here next.

## Building the paper

Needs `pandoc` (3.x) and a PDF engine: `xelatex` from TeX Live if installed, otherwise
[`tectonic`](https://tectonic-typesetting.github.io/).

```bash
make paper     # paper/out/score.{tex,pdf} and paper/arxiv/ (main.tex, content/, main.bbl, main.pdf)
make check     # the local gate: fails when the committed PDF or LaTeX is older than the draft
```

Every change to the draft is rebuilt and committed with the PDF. `bash
.claude/scripts/bootstrap.sh` installs a pre-commit hook that refuses a commit leaving the paper
stale. There is no CI: checks run locally.

## Cloud capacity

Every model step runs on graphics cards rented from Scaleway (`tools/props/cloud/`). Stock is the
bottleneck: on 2026-10-08 the L4 cards in pl-waw-2 were out of stock most of the day. So no job
is tied to one card or one zone.

- **Which cards a job may use** is set per job kind in `KINDS` in
  `tools/props/cloud/capacity.py`. A kind lists every machine type whose card has the memory for it.
  Pixal3D (three runs at once peak at 10.6 GB) may use any card of 24 GB or more, including the
  two-card machines, because its fleet spreads work over cards. Every other kind was measured on
  an L4 (24 GB), so it may use the single-card L4, L40S and H100 machines. To add a card type, add
  it to `CARDS` (cards and memory per card) and to the kinds it can hold.
- **Which zones** are listed in `ZONES` in `tools/props/cloud/scaleway.py`: fr-par-1, fr-par-2 and
  pl-waw-2, the zones that rent cards.
- **Order and fallback.** Offers are taken cheapest card first. Among equally cheap offers, the
  zone with the fewest of the run's machines comes first, then the best stocked, so a big batch
  spreads over the zones. An offer that is refused, is out of stock, or gives a machine that does
  not answer within `START_MINUTES` (5, in `batch.py`) is dropped and the next one tried. In a
  Pixal3D fleet, a machine that never answers is replaced from the remaining offers.
- **Limits.** The owner's limits in `ledger.py` (4 h and EUR 60 a batch, EUR 700 a month) are checked
  as if every card were the dearest offered. A large batch therefore leaves out the dearest card
  types when they alone would break a limit.
- **Forcing a type** for a measuring run: `batch.py --types` and `library_bake.py --types`.
- **The record.** Every run writes one row per machine to the ledger
  (`~/.farm-factory-props/cloud/ledger.jsonl`). A row holds the job kind, card type, zone, wait
  until the machine answered, minutes worked, cost and, where the runner counts them, seconds per
  unit of work. Failed starts are recorded too. `python3 tools/props/cloud/capacity.py report
  [--since YYYY-MM-DD]` prints time and cost per job kind per card type, and `capacity.py offers
  <kind>` shows where a kind can be rented right now.

The machines keep their safety: each deletes itself when the runner's heartbeat goes quiet or
the batch's time limit passes, and every run deletes its machines when it ends.

## The scene as OpenUSD

A place is exported as one OpenUSD stage, the framework's canonical scene: its objects with their
kind, transform in metres, collision, the library surface of each part and its sounds. The stage
composes two layers. The base layer is generated and rewritten on every export; the edit layer above
it is the creator's and is never written by the framework, so an edit survives a regeneration.

```bash
make env       # the framework's environment in .venv, usd-core included
.venv/bin/python tools/usd/export.py wreck --models <the place's made .gltf folder> \
    --parts <the route's labelled parts folder> --out ~/.farm-factory-props/work/usd/wreck
```

This writes `wreck.usda` (open this one), `layers/base.usda`, `layers/edit.usda` and `assets/` (one
`.usdc` per model with PNG maps). `--parts` is optional; without it a model keeps its baked look but
its parts carry no library surface. Make edits in `layers/edit.usda`, by hand, with usd-core, or in
any USD editor with that layer as its edit target. Mass and friction are not written yet.

To load it in Blender, use File > Import > Universal Scene Description and pick `wreck.usda`, or
render it from fixed cameras without a window:

```bash
python3 tools/blender/session.py batch tools/blender/inside/usd_views.py -- <stage.usda> <views.json> <out folder>
.venv/bin/python tools/usd/views.py wreck <stage.usda> --shots <the game's shots> --out <folder>
```

`views.py` renders the wreck from the game's own bench cameras and compares the result with the game's
shots. A game engine adapter is next (#2).

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. The scene export uses usd-core (Pixar's OpenUSD)
under the Tomorrow Open Source Technology License 1.0, which is Apache 2.0 with a different trademark
clause. Every model the framework uses must allow commercial use of what it makes; the paper lists
each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
