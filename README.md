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
`py=.venv/bin/python`:

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

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. Every model the framework uses must allow
commercial use of what it makes; the paper lists each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
