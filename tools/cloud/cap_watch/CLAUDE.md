# tools/cloud/cap_watch/

The env1 cap's watcher (the plan of 2026-11-09, B3): `watch.py pass`, every 5 minutes as the CronJob
`score-cap-watch` (`tools/cloud/k8s/conductor` `cap_watch`: babon's system pool, 240 s, Replace, a fresh shallow clone
of main, no store volume), reads the whole bill (`backends/scaleway.bill_all`) and every machine, disk and address
standing (`scaleway.live_rate`), keeps a reading under `caps/<name>/readings/` in the SCORE object store, and stops
paid work at the cap's line or the November cap (its docstring has the counter). In `_code.FRAMEWORK`: no row's key.

- **It fails closed.** A bill or machine list that cannot be read (an empty bill, a lower one, a cluster node missing
  from the machines listed, a missing right) is an unread reading carrying the last good one's time; past 15 minutes
  of that every cloud rent point and cluster poll refuses (`score/adapters/compute/guard.cap_refusal`) and the pass stops
  paid work. Never turn an unread pass into a zero.
- **Only what is proven babon's is taken off** the shared project's lines: a babon machine, or a disk or address on
  one, seen by a pass; anything else on a counted line is env1's.
- **A stop is no latch**: the reading itself refuses, so the first pass back under the line lets paid work start.
- The cap record itself is the owner's (`decide-yes cap env1 ...`, `score/dashboard/sync/chat_decisions.py`), written
  through `score.review.web.cap`; the watcher never writes or moves it.
- Test: `test_paid_work_stops_at_the_cap.py`, no cloud: a folder book, the readers faked.
