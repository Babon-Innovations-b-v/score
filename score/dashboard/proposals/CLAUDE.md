# score/dashboard/proposals/

The basket (CONTEXT.md: basket, basket item): what a run on main would buy, grouped into items, made for free on the
store's machine before anything is bought (`python -m score.dashboard basket`, and every upkeep pass; the runner's
plan of the whole environment takes minutes). Layout and fields: `records.py`; the command: `make.py`. A department
declares an item, its words and its questions with `python -m score.dashboard basket-item <id> --title ... --says ...
--node '<pattern>' --ask ... --recommend ...` (kept across makes; an item may span places); the owner's answers are in
`answers.json` (`python -m score.dashboard basket-answers`). The benchmarks are one item, "Benchmarks"
(`benchmarks.py`, #21): prepare's listed benchmarks at prepare's estimate, written into the index by each make,
launched by the checkout as their own batch. The free details of each place (its free after, 3D copy and what
changes) went with the cockpit (owner, 2026-11-16).

Rules:

- **Read the store, never write it.** Nothing is accepted; nothing is bought; no cloud call, no `score run`.
- **Prices are the runner's** (`score plan`'s buys, C19); a node never measured is said apart as a guess.
- **records.py stays light**: plain files only (no store, no stages, no numpy).
- Test: `proposals/test_a_basket_shows_what_a_run_on_main_would_buy.py` (the plan's buys grouped, the records read
  back, the benchmarks item).
