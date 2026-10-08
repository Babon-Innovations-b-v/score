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

Needs [`uv`](https://docs.astral.sh/uv/), and for the cloud steps a cloud backend's tools (see "Cloud
capacity"). With the current backend, Scaleway, that is the [`scw`](https://github.com/scaleway/scaleway-cli)
CLI logged in, with the project named by `SCORE_SCALEWAY_PROJECT`. Secrets are read by name, never from files
in the repo. Every step
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

Every model step runs on machines rented from a cloud provider through one interface
(`tools/props/cloud/provider.py`). The runners ask for a **capability class**, such as `gpu-24gb` (one
card with 24 GB), `gpu-80gb-x2` (two 80 GB cards) or `cpu-32c-128gb` (a processor machine), and never name a
provider, a machine type, a zone or a price. The backend maps each class to its own machine types, zones
and prices. Scaleway is the current backend (`tools/props/cloud/backends/scaleway.py`); `SCORE_CLOUD`
chooses another.

Stock is the bottleneck: on 2026-10-08 the cheapest cards in one zone were out of stock most of the day.
The cloud credits cover far more than a world costs, so a job takes whatever card is in stock, in the
order that waits least, and is never tied to one card or one zone.

- **Which classes a job may use** is set per job kind in `KINDS` in `tools/props/cloud/capacity.py`.
  Pixal3D may use any card of 24 GB or more, including two-card machines, because its fleet spreads
  work over cards. Every other kind was measured on a 24 GB card, so it may use the single-card
  classes of 24, 48 and 80 GB.
- **Order and fallback.** Offers are taken best stocked first, then in `SPEED_ORDER` (24, 48 and 80 GB,
  then the two-card classes), then the zone with the fewest of the run's machines, so a big batch
  spreads over the zones. An offer that is refused, says "out of stock" for a minute, or gives a
  machine that does not answer within `START_MINUTES` (5, in `batch.py`) is dropped and the next one
  tried. In a Pixal3D fleet, a machine that never answers is replaced from the remaining offers.
- **Several jobs on one big card.** A card runs as many Pixal3D jobs at once as its memory holds:
  three for every 24 GB (`RUNS_PER_24GB`), so an 80 GB card runs ten. `batch.py --per-card` overrides it.
  Other kinds run one job at a time until their memory per job is measured.
- **Limits.** The month's ceiling is `SCORE_MONTH_EUROS` (EUR 1,500 by default). It is checked
  against the ledger and the provider's bill before every machine is rented, and nothing more is
  rented once it is reached. A batch is also held to 4 h and EUR 60 (`ledger.py`).
- **Forcing a class** for a measuring run: `batch.py --classes` and `library_bake.py --classes`.
- **Secrets** are read by name through `tools/props/cloud/secret_store.py`: the environment variable
  `SCORE_SECRET_<NAME>` first (for local use; `gemini-api-key` is `SCORE_SECRET_GEMINI_API_KEY`), else
  the backend's secret store (Scaleway Secret Manager today). No secret is written into the repo.
- **The record.** Every run writes one row per machine to the ledger
  (`~/.farm-factory-props/cloud/ledger.jsonl`). A row holds the job kind, class, machine type, zone,
  wait until the machine answered, minutes worked, cost and, where the runner counts them, seconds per
  unit of work. Failed starts are recorded too. `python3 tools/props/cloud/capacity.py report
  [--since YYYY-MM-DD]` prints time and cost per job kind per card type, and `capacity.py offers
  <kind>` shows where a kind can be rented right now.

The machines keep their safety on every backend: each deletes itself when the runner's heartbeat goes
quiet or the batch's time limit passes (`self_delete.py`), every run deletes its machines when it ends,
and nothing is deleted before its own record is checked to belong to the configured account.

### Add a cloud backend

1. Write `tools/props/cloud/backends/<name>.py` with everything `provider.py`'s docstring lists: `NAME`,
   `CLASSES` (each capability class as your machine types, in the order to try them), `account()`,
   `offers()`, `price()`, `month_spend()`, `allow_key()`, `create()`, `start_if_stopped()`, `address()`,
   `delete()`, `ours()`, the leftover sweeps and `secret()`. Copy the shape of `backends/scaleway.py`.
   Check every resource's own account field before deleting it, never only a list filter.
2. Give `self_delete.py` the backend's way for a machine to learn its id and delete itself (its
   `BACKENDS` table), using only the standard library and a key that can do nothing but that.
3. Run with `SCORE_CLOUD=<name>`, first with `--dry-run`, then one small batch, and compare its rows in
   `capacity.py report` with the current backend's.

AWS is the likely next backend: EC2 instance types per class (for example `g6.xlarge` for `gpu-24gb`,
`g6e.xlarge` for `gpu-48gb`, `p5` for `gpu-80gb`), regions as zones, Secrets Manager for `secret()`, and
instance metadata plus a narrowly scoped role for the self-delete.

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. The scene export uses usd-core (Pixar's OpenUSD)
under the Tomorrow Open Source Technology License 1.0, which is Apache 2.0 with a different trademark
clause. Every model the framework uses must allow commercial use of what it makes; the paper lists
each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
