# tools/costs/

The cloud's cost and time as the paper's cost tables give them (Appendix G), from the spend ledger and the provider's
bill. `costs.py` is the way in (its docstring has the commands); `costs_test.py` checks its sums on a ledger written
in the test.

- **The ledger is never rewritten.** What a row lacks (a kind, a machine type) is added beside it: the reconciliation
  file tags rows by batch, and an engine run's type is read from its price. A fix to the runners goes in
  `tools/props/cloud/`, not here.
- **The paper reads the public copies** in `paper/evidence/cloud/`: `scrub` writes the ledger's first rows with every
  local root replaced (`$PROPS`, `$MOTION`, `$HOME`, repository-relative), `reconcile` and `tables` read only those
  copies and the saved bill, so anyone reruns them from the repository. The bill file carries no account or project
  id; check a new one before copying it.
- **"Per stage" is per kind of batch.** The ledger names batches, not worlds, places or the route's stages, so the
  tables group kinds of batch; a world's or a place's cost comes from Appendix B's attribution by work folder.
- **R&D against production is a rule on the row**, kept in `RND_GROUPS`, `RND_KINDS` and `RND_WHO`: work on the
  framework (engine runs, images and proofs, method experiments, benchmarks and comparisons named in `who`) is R&D,
  the rest production. The route's own batches carry no mark when they were reruns while the method changed, so
  production is an upper bound.
