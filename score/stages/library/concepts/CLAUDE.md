# score/stages/library/concepts/

The concept part of the library check: every locked concept in the store (a place's standing pick,
`score.review.concepts.picked`) is the library's `concept/<place>` entry holding the same picture (concept.png's
sha256). A pick hands its place over once (`score/review/concepts.handed_over`) and a failed hand-over is never tried
again, so this check is what keeps the library from going stale behind the concept review (base, missing from
2026-10-20 to 2026-11-19).

- Read only: the store through the library check's `stored.reading()`, the library through its `entries.Shelf`; no
  library code imported. Its own module, not under `score/stages/complete/` (that tree's test allowlist may not grow).
- Runs inside the library check (`python -m score.stages.complete.library` writes `<out>/concepts.json`) and alone:
  `SCORE_LIB_ROOT=<library> .venv/bin/python -m score.stages.library.concepts`, exit 1 on a finding. The fix
  for a finding is the place's hand-over again (`concepts.handed_over(store, place)`), never a hand-written entry.
- Test: `test_every_locked_concept_is_its_library_entry_with_its_picture.py`.
