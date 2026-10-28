# SCORE

> **Demo film: coming.** It waits on environment 1's batch; the film replaces this box once it exists.

**SCORE: Synthesising Complete, Owned, Responsive Environments for Simulation.**

SCORE is a framework that synthesizes 3D environments a simulator can step as written: every object its own
body with a collider, mass and material, doors on hinges, ground under its own planet's gravity, light and sound
that come from somewhere, and nothing in it the creator does not own. One environment serves many uses: games,
film, robotics, embodied AI. It is one OpenUSD record, a scene inside its parent scene and each kind of work on it
(layout, surfaces, physics, light, motion, effects, sound, people) a layer of its own, so it stays editable, and
an edit runs again only the steps behind it. Its physics trial and settle run on Newton with MuJoCo's solver;
effects follow.

The creator writes the score; coding agents and open tools play it.

## How it builds an environment

The creator locks the design from the top down: an environment concept (its style and its physics), then a
concept for each scene, from which the framework reads a scene inventory and writes a plan in metres. Everything
below runs offline in cloud batches: models from close-ups through the prop route, surfaces from one shared
library, then the settle, physics, light, motion, effects, sound and people layers, each behind measured gates
and accepted before the next step reads it. Cheap checks run before every paid step, and the creator decides
only at fixed points: locks, accepts, waivers and the batch's budget.

Environment 1 is the evidence. Its first run was not accepted and its store was lost, so the paper shows none of it yet; its new
batch makes the demonstrations: every layer of one environment, physics that holds, the same environment in a
game engine, a robot simulator and a film render, and an edit that stays cheap.

**Next.** Every character gets a sim body on Newton, driven by its SOMA segment rotations and standing on a
SCORE floor, starting minimal. Beyond that: bodies true to the person, motion from the SOMA ecosystem turned
into scenes without video or identifying information, trained models (brains) that drive a sim body in invented
worlds, and a data loop in which simulation data trains better models. The paper's last sections say what is
done and what is a goal.

## What is here

- **The paper**, a working draft: [`paper/out/score.pdf`](paper/out/score.pdf). Its one source is
  [`paper/source/score.md`](paper/source/score.md); an arXiv-ready LaTeX tree is generated from it in
  [`paper/arxiv/`](paper/arxiv/).
- **The framework**: `score/` (the runner, stages, gates, store, review pages and the creator cockpit),
  `tools/` (the prop pipeline, Blender and OpenUSD tools, sound, cloud runners), `data/` (environment 1's
  designs and the library's records) and `vendor/` (vendored tools, as released). The bible's
  [`architecture/components`](docs/bible.md#architecturecomponents) chapter says what is where.

## Running the framework

Needs [`uv`](https://docs.astral.sh/uv/). Secrets are read by name, never from files in the repo.

```bash
make env                                       # the Python environment (.venv) from pyproject.toml
make tests                                     # every framework check; TESTS="<module>/test_<invariant>.py" for some
.venv/bin/python -m score plan <environment>   # what a run would make and buy, running nothing
.venv/bin/python -m score run <environment>    # drive the environment's stages to their end (--free: free steps only)
.venv/bin/python -m score status <environment> # every line's state
.venv/bin/python -m score price <environment>  # what the remaining paid steps cost
```

Steps that load a model, bake or render run on a machine with a graphics card, in one of two places:

- **Your own PC**, if it has an NVIDIA card (environment 1 runs on a 16 GB card): Docker with NVIDIA's container
  toolkit, then `python3 tools/cloud/this_pc.py run <environment>`, and `pause`, `resume` or `status` to free
  the card for something else and pick up where it stopped. Each step runs in a container, one card job at a time,
  at no cost; a step whose measured need is more than your card holds waits for the cloud.
- **The cloud**, on machines rented by capability class (such as `gpu-24gb`) that delete themselves when done. The
  current backend is Scaleway: the [`scw`](https://github.com/scaleway/scaleway-cli) CLI logged in, with the project
  named by `SCORE_SCALEWAY_PROJECT`. Paid steps run only after the creator approves their price.

What an environment makes is kept in score_lib, the library of every SCORE asset, fetched by
`tools/library/library_files.py` and checked against each entry's hash. How classes, stock, limits and container
images work is in [`tools/cloud/CLAUDE.md`](tools/cloud/CLAUDE.md); how to add a cloud backend is in
[`tools/cloud/backends/CLAUDE.md`](tools/cloud/backends/CLAUDE.md). The paper's source and build are in
[`paper/`](paper/CLAUDE.md).

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. The scene export uses usd-core (Pixar's OpenUSD)
under the Tomorrow Open Source Technology License 1.0, which is Apache 2.0 with a different trademark
clause. Every model the framework uses must allow commercial use of what it makes; the paper lists
each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
