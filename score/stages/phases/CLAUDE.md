# score/stages/phases/

Environment 1's phases in order (owner, 2026-11-06, issue #21: check before, queue and freeze, lock, retry then gap,
next phase): models, surfaces, people, light-sound, assembly, film, each a name and the stage-table names or fnmatch
patterns it holds. Read `score/CLAUDE.md` first; its rules hold here.

- **Every stage of the table is in exactly one phase, and no stage reads a stage of a later phase.** The test holds
  both over the real table: a new stage gets its phase here in the same commit, at or after every phase it reads.
- **Framework only** (`score/graph/_code.py` FRAMEWORK): no stage imports this, so an edit here moves no row's key.
- Used by `python -m score run|status|plan --phase <name>` (as `--stage` with every stage of the phase) and the
  session Buy's `buy <yes id> --phase <name>` (`score/dashboard/checkout/flow.phase_kept`).
