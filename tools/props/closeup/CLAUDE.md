# tools/props/closeup/

The close-up stage: one clean, three-quarter picture of each generated row of a place, the input to the prop
pipeline. Entry: `stage.py`; its docstring says how to call it. The owner's decision (2026-10-08): Qwen-Image-
Edit-2511 draws every close-up first, the shape check (`check.py`) decides without a person whether each may go on,
and Nano Banana Pro (`pro.py`) draws only the ones it fails. Pro's pictures are checked the same way. Pro draws from
the crop alone (given the whole room it drew the room behind the object, a miniature or dimension lines on half the
lab's), with the room as a second reference only when the crop is too small; a row whose every take fails is left
for the creator.

- **No model runs here.** Qwen draws on rented cards (`../cloud/pictures.py --model qwen-edit`), the judge answers on
  one (`../cloud/judge.py`); the measurements and the decision are plain Python.
- **The check leans to failing.** A close-up passed wrongly costs a bad 3D model; one failed wrongly costs one Pro
  picture. Its limits were tuned on the 40 hand-scored close-ups of job openpics (2026-10-08); a change to a limit
  or to the judge's question is measured on those again before it lands.
- **Pro draws through the Batch API at half price** (owner, 2026-10-24): `pro.draw` sends a step's close-ups as one
  job (`../cloud/google_batch.py`), the same request as one call would send; only `stage.py` calls it, and only for
  rows the check failed.
  `pro.draw` refuses outside a cleared run (`score.adapters.compute.require_cleared`), as every paid call does.
- **The object's own size, the check's own view, strict retries** (owner, 2026-10-24, from the Buy's 80 gaps;
  2026-10-25, "fix all"): a close-up is asked for and checked at `stage.object_size` (the row's `read_size`, its
  inventory reading's metres, else its `size`; a plan's item is the footprint it is laid in, never the object's size);
  every wording states the check's turn and look-down (`stage.VIEW` from `check.TURN_DEGREES`, `LOOK_DOWN_DEGREES`); a
  picture the check rejects gets up to three retries in the same step (`PRO_TAKES`): `RETRY` added to its wording,
  then `FIRMER` too on a seed of its own (`RETRY_SEEDS`), so each take is a new request, every one priced and on the
  ledger like the first, at the same settings. Never loosen the check to pass more.
- **A picture is keyed by its request, the check judges it apart** (coordinator, 2026-10-25): every Pro picture stays
  in google_spend's cache, a rejected one too; the close-up row first reads back every take the cache holds (free)
  and judges it with today's check, and draws only for the rows none passed. A check change re-judges kept pictures
  without drawing them; a passing picture is kept, so its model's take stands. Never change the first two takes'
  requests (`pro`, `retry`): the pictures of the batches before are cached under them.
- **The outline is held to a look-down range** (`check.LOOK_DOWN_DEGREES` to `LOOK_DOWN_MOST`, 15 to 30 degrees,
  2026-10-25): Pro draws from that high whatever the wording says, and a flat object's outline is nearly all
  look-down, so one angle faulted the camera, not the object (34 of 74 proportion faults of Batch 1's first try were
  good pictures seen from higher; re-measured and looked at, the openpics set was not on the PC).
- **A person is the one exception to the three-quarter view** (the people layer's own close-up, CONTEXT.md "layer
  adapter"): a row whose `layer` is `people` is drawn with `stage.PERSON` (one person, front on, in the rig's A-pose,
  arms and legs clear) and measured by `check.person_faults` (framed, arms apart: `arm_gap_share`, which the maker's
  `prop_person.py` reads from here), never by a box's proportions.
- **Print does not matter** on a close-up: labels and print go on the model as decals later.
- Checks are plain scripts (`*_test.py`) run by `make tests`.
