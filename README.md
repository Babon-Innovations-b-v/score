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

Needs [`uv`](https://docs.astral.sh/uv/), and for the cloud steps a cloud backend's tools. With the current
backend, Scaleway, that is the [`scw`](https://github.com/scaleway/scaleway-cli) CLI logged in, with the project
named by `SCORE_SCALEWAY_PROJECT`. Secrets are read by name, never from files in the repo. Every step that loads
a model, bakes or renders runs on a rented machine that deletes itself; this machine runs plain Python only.

Local processing is also possible on a strong PC with an NVIDIA card (environment 1 runs on a 16 GB card): Docker
with NVIDIA's container toolkit, then `python3 tools/cloud/this_pc.py run <environment>`. Each step runs in a
container on your card, one card job at a time, at no cost; a step whose measured need is more than your card holds
is refused and waits for the cloud.

```bash
make env                                       # the Python environment (.venv) from pyproject.toml
make tests                                     # every framework check; TESTS="<module>/test_<invariant>.py" for some
.venv/bin/python -m score plan <environment> --json   # what a run would make and buy, running nothing
.venv/bin/python -m score run <environment>           # drive the environment's stages to their end
.venv/bin/python -m score status <environment>        # every line's state
```

Machines are rented by capability class (such as `gpu-24gb`), never by provider or machine type; how classes,
stock, limits and container images work is in [`tools/cloud/CLAUDE.md`](tools/cloud/CLAUDE.md).
An environment's made models and sounds are not in git: they are entries of the creator's library, score_lib,
fetched by `tools/library/library_files.py` and checked against each entry's hash.

### Add a cloud backend

1. Write `tools/cloud/backends/<name>.py` with everything `provider.py`'s docstring lists: `NAME`,
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
