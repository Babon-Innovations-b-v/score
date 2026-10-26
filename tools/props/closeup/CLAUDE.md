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
  then `FIRMER` too on a seed of its own (its number, `pro_ask`), so each take is a new request, every one priced and on the
  ledger like the first, at the same settings. Never loosen the check to pass more.
- **A picture is keyed by its request, the check judges it apart** (coordinator, 2026-10-25): every Pro picture stays
  in google_spend's cache, a rejected one too; the close-up row first reads back every take the cache holds (free)
  and judges it with today's check, and draws only for the rows none passed. A check change re-judges kept pictures
  without drawing them; a passing picture is kept, so its model's take stands. Never change the first two takes'
  requests (`pro`, `retry`): the pictures of the batches before are cached under them.
- **A gap's step bought again draws new takes** (owner, 2026-10-25: "a place needs every object"): the takes go on
  past `PRO_TAKES` (`stage.take_at`: `retry-4` on, each `FIRMER` on its own seed), at most `len(PRO_TAKES)` new ones a
  row a run, after every cached take is judged. Before, a row whose four takes failed read the same four pictures back
  and drew nothing, so every close-up gap could only come back as it was.
- **The outline is held to the one stated look-down** (`check.LOOK_DOWN_DEGREES`, the angle every wording states;
  2026-10-25): never a best fit over a range, whose free angle absorbs a wrong size. No documented camera of the
  picture model backs a range and Batch 1's flat close-ups fit 6 to 60 degrees, so a picture off the stated view is a
  retry. The likeness gate draws the model at the same look-down (`score/stages/props/likeness.look_down`).
- **A gap's later takes are asked from the crop alone, upright, casting no shadow** (`stage.UPRIGHT`, the takes past
  `PRO_TAKES`, retry-4 on; Batch 1 try 4, 2026-10-26): the "room" rows' four takes drew the corridor behind the object
  (the room reference), a cast floor shadow the outline counts as object (the corner shelves and the right dome door:
  without it 3 and 2 of their 4 takes were inside the limit), or the wall keypad lying on its back. The first four
  takes' requests are unchanged, so their kept pictures still read back free.
- **A row laid far off is drawn from its crop alone** (`far`, prepare's groups.far_made; `stage.pro_wording`): its crop
  is a speck of the whole painting, and given the room as well Pro drew the room (Batch 1 try 4: the street's distant
  rocket's and floodlight's first takes were the whole street). Every other row's request is unchanged. A row
  anchored in the sky is far too (prepare's groups.beyond_of; 2026-10-26: the square's rocket, never marked far, took
  the room and three of its four takes were the whole square), and a far row is asked at the width its box shows
  (groups.seen_size), never its read core's: its one clean take failed only on a 12:1 read size against a 3.8:1 outline.
- **A row that lies flat is drawn and checked from straight above** (`check.lies_flat`, the model gate's flat class
  with its height its thinnest side; Batch 1 try 4, 2026-10-25: the rug, poster and sticky note failed the proportion
  check on all four takes, their outline at the stated look-down nearly all view): worded `stage.VIEW_ABOVE`, its
  outline held to its face's wide:deep either way round, the likeness gate drawing the model from above
  (`likeness.look_down(size)`) and its take laid on its face (`pixal.py --flat`, `pixal_row.lies_flat`). Every other
  row's request is unchanged, so its cached pictures read back free. A slender row (a pipe) is not flat: it keeps
  the three-quarter view.
- **A person is the one exception to the three-quarter view** (the people layer's own close-up, CONTEXT.md "layer
  adapter"): a row whose `layer` is `people` is drawn with `stage.PERSON` (one person, front on, in the rig's A-pose,
  arms and legs clear) and measured by `check.person_faults` (framed, arms apart: `arm_gap_share`, which the maker's
  `prop_person.py` reads from here), never by a box's proportions.
- **Print does not matter** on a close-up: labels and print go on the model as decals later.
- Checks: `test_only_a_clean_closeup_goes_on.py` (pytest, `make tests`): check, stage and pro through their own
  functions, pictures drawn in the test, Google's batch faked at its send and status.
