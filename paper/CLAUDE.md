# paper/CLAUDE.md

The SCORE paper. **One source: `source/score.md`.** Everything under `out/` and `arxiv/` is generated
by `build/build.py`; never edit a `.tex` or the PDF by hand.

```
make paper                      # rebuild out/score.{tex,pdf} and arxiv/ (main.tex, content/, main.bbl, main.pdf)
python3 build/build.py --check  # exit 1 when a committed output is stale (also run by make check and the pre-commit hook)
```

## Layout

- `source/`: `score.md` (front matter: title, author, date, abstract), `refs.bib`, `ieee.csl`, `todo.lua`.
- `figures/`: the pictures the draft uses, JPEG, ours and safe to publish.
- `build/`: the build script and the check that the build is current.
- `out/`: pandoc's standalone `.tex` and `.pdf` (citeproc, IEEE), and `stamp.json`, the hashes the check compares.
- `arxiv/`: upload this folder as is. One `content/<section>.tex` per top-level heading, natbib with
  `unsrtnat`, and `main.bbl` because arXiv does not run BibTeX. `main.tex` compiles with pdflatex
  and with xelatex/tectonic.

## Rules for the draft

- **Every number is read from a file**, named in an HTML comment beside it. No number from memory.
- **Not measured, not checked: mark it** `[what is missing]{.todo}`. It prints red in the PDF.
- **A change to the draft is rebuilt and committed in the same commit** as the PDF and LaTeX.
- **The world step** (World Labs Marble in our runs) is one optional step of the method. Never
  compare it with another model or judge it on its own (World Labs ToS §2.8(d)); results are
  "route with" against "route without" the step. Credit "Generated using World Labs" wherever its
  output or anything derived from it is shown.
- **Disclose** what was automatic, what a coding agent wrote, what was a hand fix and what was a human pick.
- **Pictures:** our own outputs only, no real person's likeness, models whose licence allows commercial use.
- Top-level headings are `#`; a new heading becomes a new `content/` file by itself.
- Write plain and direct, claims no stronger than the record; quote the owner only where the
  paper records what he said, and turn offhand remarks into proper wording.
