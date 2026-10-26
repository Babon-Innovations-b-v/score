# score/library/

The one reader of the creator's library (score_lib's `entries/` and `index/`) on the score side, ADR-0007.

- **score reads score_lib only here and through its `score-lib` command.** No other module globs `entries/` or
  `index/` or parses an `entry.json`; the cockpit (`score/dashboard/state/library.py`), the library check
  (`score/stages/complete/library/entries.py`), the library sweep (`score/stages/library/sweep.py`) and prepare's
  library first (`score/stages/complete/prepare/library.py`) call this. `tools/library/library_files.py` stays the
  fetch side (blobs), and `score/stages/library/backend.py` runs the command.
- **Versioned.** Each file is checked against `ENTRY_SCHEMA` / `INDEX_SCHEMA`; another version is refused
  (`Unread`). A new score_lib schema is a change here first, then in the callers.
- **Pure.** json, os and pathlib only: the hosted cockpit imports it (`score/dashboard/sync/test_the_cockpit_gets_the_store_whole_and_the_store_only_the_owners_asks.py`, its hosted-light case).
  Never import score_lib's own code.
- `test_read_only_at_known_schema.py`: pytest, a temp library.
