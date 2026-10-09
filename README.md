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

Measured on 2026-10-08, from the recorded close-ups: 12 Pixal3D models in 51 min on cloud cards (EUR 1.43),
PartCrafter parts for all 12 (EUR 0.72), labels here, one bake of 16 models in 24 min on one L4 (EUR 0.33); the
model gate passed all 16, and the package (16 objects, 22 copies, 0.36 M triangles, 218 MB) passed its check with
every copy where the game 2099's own layout puts it. EUR 2.48 in all, about two hours, most of it waiting for cards.

### A place's characters

A place's people are part of its stage. Its cast (`data/characters/<place>.json`) says who is there, how many, where,
doing what and why: named people at a spot, groups mixed from the character kit by seed along a band, and a crowd of
thousands of one cheap body. `tools/characters/cast.py` writes them into the stage as skinned UsdSkel characters, each
playing its clip from its own start, in a layer of their own (`layers/characters.usda`, between the creator's edit
layer and the framework's base); the crowd is one PointInstancer with a prototype per clip, phase and palette. The
bodies are the files `tools/characters/people/run.sh` builds (SOMA-X bodies shaped by SAM 3D Body, Kimodo clips from
sentences, GarmentCode clothes; `tools/characters/skel_usd.py` converts each).

```bash
$py tools/characters/cast.py square --stage ~/.farm-factory-props/work/usd/square   # after tools/usd/export.py
```

The review page then has a Characters section: why each entry is there, each character close up, each group and the
crowd from where they are seen, and short moving shots, rendered from the stage like the scene.

## The world's files

The first world's heavy files, its made models (about 256 MB packed) and its sounds (about 36 MB), are not in git: they are
a release of this repository (`world1-assets-4` now), and `data/assets/world1.json` names every file with its sha256, its
source and its licence. A record names a file by its name there (`models/hub_kit/console_1.gltf`,
`sound/generated/places/habitat.ogg`); `tools/assets/world.py` fetches and checks the release the first time a
tool needs one, into `~/.cache/score/world-assets/<tag>/` (or `SCORE_WORLD_ASSETS`). The framework reads nothing
from the game 2099's checkout; `tools/assets/game_free_test.py` fails when code or data names it.

```bash
python3 tools/assets/world.py fetch                       # the release, checked
python3 tools/assets/world.py pack <folder> <new tag>     # a new release from the local files, then: publish
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
- **Order and fallback.** Offers are taken best stocked first, then in the kind's order of classes, then
  the zone with the fewest of the run's machines, so a big batch spreads over the zones. The default
  order is `SPEED_ORDER` (24, 48 and 80 GB, then the two-card classes). Pixal3D takes 80 GB cards first,
  since one runs ten takes at once. Bakes in Cycles take cards with ray-tracing cores first and an
  80 GB card without them only after 5 minutes with nothing else to be had (`KIND_ORDER`, `LATE`). An offer that is refused, says "out of stock" for a minute, or gives a
  machine that does not answer within `START_MINUTES` (5, in `batch.py`) is dropped and the next one
  tried. When a round finds no machine in stock anywhere, the slot asks again every 3 minutes
  (`STOCK_RETRY_MINUTES` in `batch.py`), with the offers read afresh across every class and zone the kind fits, until
  its run has no work left for it or reaches its deadline or the month's ceiling; a Pixal3D fleet short of cards rents
  more the same way as stock comes up. No slot settles for the one card it found first. In a Pixal3D fleet, a machine that never answers is replaced from the remaining offers.
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
  [--since YYYY-MM-DD]` writes time and cost per job kind per card type to
  `~/.farm-factory-props/cloud/capacity-report.txt` and prints one summary line (`--verbose` prints the table), and `capacity.py offers
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

## Reviewing a place

The review page shows one place the way the creator checks it: every stage's output side by side in the order the
stages ran (the concept and the creator's references, the dimensioned plan, the inventory boxed on the concept, the
close-ups, each made model with its route, its labelled parts and its baked look, the library surfaces, and the
assembled scene), before and after from the same cameras where a stage was rerun, and every check's result with what
it caught. It is a static folder built from the files the stages already wrote; the scene is rendered from the
place's OpenUSD stage by Blender with no window, in its baked materials on the place's own ground, from fixed cameras
and along a short walk round the place. Its checks include the resting check (`tools/usd/resting.py`): every object
looked at straight down on the stage's ground, failing when it floats, tips (its weight outside what it touches) or is
sunk into the ground below its own contact points.

```bash
.venv/bin/python tools/review/page.py wreck --run <the run's work folder> --out ~/.farm-factory-props/work/review/wreck \
    [--before <an earlier run's work folder>] [--concept <the concept folder>] [--references <the reference pictures>] \
    [--stage <wreck.usda>] [--before-stage <the earlier run's wreck.usda>] [--agreement <tools/usd/views.py's folder>]
```

A place with a scene record (`data/scene/<place>.json`: what the game drew in its own code, from room shells, stairs
and gameplay objects to the ground, water, backdrop, lights and sky) is exported whole with `export.py`, which reads
the files the record names from the world's release (below), and its page is drawn from the record's own cameras (the player's spots; a room from inside at
standing height and from a cutaway above) by the stage's own lights. `--game-shots <folder>` lays each view beside the
game's own shot from about the same place, with both pictures' mean brightness, and the page says what of the game's
place the scene carries, its people included, and what is still missing against the game's shots ("scene vs game").

Open `index.html` in the out folder in a browser, or publish the folder as it is: it needs no server. A run folder is
what `tools/props/library/place_route.py` works in; `tools/review/records.py` lists what is read from each folder.
Rendering takes a few minutes on the processor (the wreck: about eight); `--no-render` rebuilds the page from the
renders already in the out folder, and `--plain` draws the scene in one grey as a debug view. Needs `ffmpeg` for the
walk's video.

The stage comes from `tools/usd/export.py <place> --models <run>/made --work <run> --out <folder>`; a place outside
with a record in `data/ground/` stands on the planned ground as the game stands it (`tools/usd/ground.py level
<place>` holds the ground under a place's pieces at one height, its yard). When the resting check finds loose objects
that float, tip or are sunk, `tools/usd/settle.py <stage>` drops them in headless Blender onto the real ground with
their own triangles (buildings and other rows marked `"fixed": true` stay static) and writes where each came to rest
into the place's layout, with its turn as a `rotation`, as long as that is a small correction (at most 15° and
30 cm); a piece that would move more keeps its laid pose and is marked for its layout to be put right. Export again
and check. `--cloud` on settle.py and page.py runs the Blender work on rented machines
(`tools/props/cloud/blender_cloud.py`).

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. The scene export uses usd-core (Pixar's OpenUSD)
under the Tomorrow Open Source Technology License 1.0, which is Apache 2.0 with a different trademark
clause. Every model the framework uses must allow commercial use of what it makes; the paper lists
each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
