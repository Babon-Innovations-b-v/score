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

## Licence

MIT, see [`LICENSE`](LICENSE). The IEEE citation style in `paper/source/ieee.csl` is from the
Citation Style Language project under CC BY-SA 3.0. Every model the framework uses must allow
commercial use of what it makes; the paper lists each one with its licence.

## Working in this repo

The repo follows the owner's working loop (grill, plan, code, close), set out in
[`CLAUDE.md`](CLAUDE.md) and [`docs/bible.md`](docs/bible.md).
