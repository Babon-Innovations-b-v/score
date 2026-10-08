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
- **The framework's code**, moved here from its first user, the game 2099, with its history:
  `tools/props/` (prop pipeline, scene tools, surface library, gates, cloud runners), `tools/blender/`
  (headless Blender), `tools/sound/`, the surface library's data (`data/library/`), the first world's data
  (`data/`, `design/tokens/`) and the vendored tools (`vendor/`). A place's output is a **scene package**:
  every object its own glTF model and `scene.json` saying where each copy stands, for any engine. The
  bible's `architecture/components` chapter says what is where.

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

## Running the framework

Needs [`uv`](https://docs.astral.sh/uv/), and for the cloud steps the
[`scw`](https://github.com/scaleway/scaleway-cli) CLI logged in to a Scaleway project. Name the project with
`SCORE_SCALEWAY_PROJECT`; secrets are read from its Secret Manager by name, never from files. Every step
that loads a model, bakes or renders runs on a rented machine that deletes itself; this machine runs plain
Python only.

```bash
make env       # the Python environment (.venv) from pyproject.toml
make tests     # every framework check; TESTS="tools/props/library/package_test.py" for some
```

### One place end to end: the wreck

The wreck is an outdoor place of the first world: 13 inventory rows, 22 copies. Its record is its scene
inventory (`data/inventory/wreck.json`), each kind's turn and allowed materials (`data/library/details.json`),
and one close-up a generated row (kept in the work folder, not in git). With `W` its run folder and
`py=.venv/bin/python`. Every command below runs in `.venv`, the cloud runners included: they load no model
here, and `picture.py` imports torch only where its model loads. On a checkout older than that change,
`pictures.py`, `parts.py` and `library_bake.py` stop on a missing torch; run them with an environment that
has it (the first world's `~/.farm-factory-props/env/bin/python`).

```bash
# 1. Pixal3D models from the close-ups, one cloud batch (a line a row: "<row>-s1 <close-up>")
$py tools/props/cloud/batch.py $W/pixal-list.txt --who me --inventory data/inventory/wreck.json
# 2. PartCrafter parts from each model's cut-out (~/.farm-factory-props/work/pixal/<take>.svviews/input.png)
$py tools/props/cloud/parts.py $W/cutouts --who me --parts 8
# 3. Labels: every part one allowed library material, checked for patchy paint
$py tools/props/library/labels.py <row>-s1 $W/parts/<row>-s1 --place wreck --kind wreck_<row> \
    --parts $W/cutouts/parts/<row>-s1-8
# the torn leg (2.4 m) is labelled into $W/parts/torn_leg-s1 and split into its two pieces
$py tools/props/library/place_route.py split $W/parts/torn_leg-s1 $W/parts/leg_strut-s1 $W/parts/leg_foot-s1
# 4. The plan and the bake jobs, baked in the cloud (--processor when no card is in stock)
$py tools/props/library/place_route.py plan wreck $W --take s1
$py tools/props/cloud/library_bake.py $W/job-*.json --who me
# 5. The model gate, then the scene package and its check
$py tools/props/library/place_route.py check wreck $W
$py tools/props/library/package.py wreck $W $W/package
```

## Cloud capacity

Every model step runs on graphics cards rented from Scaleway (`tools/props/cloud/`). Stock is the
bottleneck: on 2026-10-08 the L4 cards in pl-waw-2 were out of stock most of the day. Scaleway's
credits cover far more than a world costs, so a job takes whatever card is in stock, in the order
that waits least, and is never tied to one card or one zone.

- **Which cards a job may use** is set per job kind in `KINDS` in
  `tools/props/cloud/capacity.py`. A kind lists every machine type whose card has the memory for it.
  Pixal3D may use any card of 24 GB or more, including the two-card machines, because its fleet
  spreads work over cards. Every other kind was measured on an L4 (24 GB), so it may use the
  single-card L4, L40S and H100 machines. To add a card type, add it to `CARDS` (cards and memory
  per card), to `SPEED_ORDER`, and to the kinds it can hold. The 16 GB P100 (RENDER-S) is not used:
  the GPU image's driver does not see its card.
- **Which zones** are listed in `ZONES` in `tools/props/cloud/scaleway.py`: fr-par-1, fr-par-2 and
  pl-waw-2, the zones that rent cards.
- **Order and fallback.** Offers are taken best stocked first, then in `SPEED_ORDER` (L4, L40S,
  H100, H100-SXM, two-card H100, two-card L4), then the zone with the fewest of the run's machines,
  so a big batch spreads over the zones. An offer that is refused, says "out of stock" for a
  minute, or gives a machine that does not answer within `START_MINUTES` (5, in `batch.py`) is
  dropped and the next one tried. In a Pixal3D fleet, a machine that never answers is replaced
  from the remaining offers.
- **Several jobs on one big card.** A card runs as many Pixal3D jobs at once as its memory holds:
  three for every 24 GB (`RUNS_PER_24GB`), so an H100 runs ten. `batch.py --per-card` overrides it.
  Other kinds run one job at a time until their memory per job is measured.
- **Limits.** The month's ceiling is `SCORE_MONTH_EUROS` (EUR 1,500 by default). It is checked
  against the ledger and Scaleway's bill before every machine is rented, and nothing more is rented
  once it is reached. A batch is also held to 4 h and EUR 60 (`ledger.py`).
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
