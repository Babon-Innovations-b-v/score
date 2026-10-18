# score/stages/complete/visual/

The visual check (2026-10-18): what the owner saw by eye in the films and no gate flagged, a flat grey plane cutting
through the old station's view (a neighbour's untextured ground standing across it) and the wreck's untextured light
floor; and, the same day, the walkway tube's panels standing inside the airlock room (`room.py`). Free and
local: frames from the store's accepted films and stills, rays cast into the stage each was drawn from (pxr and
trimesh, read only), no Blender, no cloud. `judge.py`'s docstring has the rules.

- **Standalone, not a gate of the complete row.** It reads the films, and the films (demo-film) are made only once
  their place passes complete, so a complete gate that read them would be a loop. It writes
  `WORK/checks/visual/<place>/findings.json` in the standalone checks' shared format (`outputs`, `findings`: `rule`,
  `prim`, `sentence`, `picture`), which the cockpit lists as problems with their marked pictures
  (`score/dashboard/state/local.py` `check_findings`) while the film and still outputs it judged stay accepted.
- `measure.py` gathers (store to evidence folder, heavy: about a minute a place with neighbours), `judge.py` judges
  an evidence folder (light, no store), `marks.py` draws. Keep them apart: the test's fixture is evidence alone.
- Run: `.venv/bin/python -m score.stages.complete.visual [--place P] [--judge-only]` under
  `systemd-run --user --scope -q -p MemoryMax=16G -p CPUQuota=400%`, in the background; it writes
  `WORK/checks/visual/<place>/` and `contact_sheet.png`.
- The fixture `data/checks/visual/<place>/` is real evidence (old_station and wreck fail, workshop passes); measure
  it again with `measure.gather` only when the rules need a case it lacks.
- Test: `visual_test.py`.
