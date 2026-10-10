# paper/CLAUDE.md

The SCORE paper. **One source: `source/score.md`.** Everything under `out/` and `arxiv/` is generated
by `build/build.py`; never edit a `.tex` or the PDF by hand.

```
make paper                      # rebuild out/score.{tex,pdf} and arxiv/ (main.tex, content/, main.bbl, main.pdf)
python3 build/build.py --check  # exit 1 when a committed output is stale (also run by make check and the pre-commit hook)
```

## Layout

- `source/`: `score.md` (front matter: title, author, date, abstract), `refs.bib`, `ieee.csl`, `markers.lua` (gap boxes and TODO marks).
- `figures/`: the pictures the draft uses, JPEG, ours and safe to publish.
- `evidence/`: copies of the run records that numbers are read from (cloud ledger, benchmark sessions, triage and resting summaries, logs), scrubbed of local paths and addresses.
- `build/`: the build script and the check that the build is current.
- `out/`: pandoc's standalone `.tex` and `.pdf` (citeproc, IEEE), and `stamp.json`, the hashes the check compares.
- `arxiv/`: upload this folder as is. One `content/<section>.tex` per top-level heading, natbib with
  `unsrtnat`, and `main.bbl` because arXiv does not run BibTeX. `main.tex` compiles with pdflatex
  and with xelatex/tectonic.

## Rules for the draft

- **Every number is read from a file**, named in an HTML comment beside it. No number from memory. A new or rewritten source is public: a file in the repository (a run record goes into `evidence/`), a commit or an issue comment, never a personal path, a memory note or a private page. Gap: older comments still name run logs that are not published (git-ignored `tmp/` logs, handoffs, R&D progress logs); when a claim they carry is touched, its record moves into `evidence/` or the comment cites a commit or an issue comment.
- **The draft has the final paper's structure.** Settled content (problem, method) is written fully, tight, without hedging. Wherever final content will go (a figure, a results table, an evaluation), a gap box stands in its place: `::: gap` ... `:::`, starting `**Gap: <what>.**`, one or two sentences on what goes there and what it waits on. A gap is filled by replacing the box. `[text]{.todo}` (prints red) is only for a number still being checked, and does not reach a shared draft.
- **Short:** about 4 to 5 pages plus references while gaps are open; it grows as they fill. No filler: no disclaimers, no repeated hedges, related work only where it positions SCORE.
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
