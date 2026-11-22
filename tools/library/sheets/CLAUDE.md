# tools/library/sheets/

`sheets.py` makes the library's review contact sheets: every current (not withdrawn) entry that has a look as one
labelled tile, grouped by kind, so a reviewer spots broken entries by eye (owner, 2026-11-22: is the library "nice and
clean?", then "yes" to a full visual pass). Its docstring gives the three steps.

- **Rendered in the cloud, never on this PC**: the jobs run `tools/blender/inside/library_sheet.py` on rented cards
  through `tools/cloud/blender_cloud.py` under a spend ticket, and each machine fetches its entries' files itself from
  the library's public copy, each hash checked, so only small job lists go up. This PC fetches only small records
  (surface.json, face.json, an effect's clip, read and removed) and the pictures concept and place entries hold.
- **Review pictures are small and quick** (320 px, 32 samples, denoised): they never ship and do not change what the
  reviewer decides. The studio, camera and staging are `library_demo.py`'s; a recipe surface's palette slots are drawn
  in plain greys (`REVIEW_GREYS`), since a palette token belongs to a place.
- **A failure is a tile, never a stop**: an entry that fails to fetch or render, or holds no picture, is a red tile
  with its error and a row in `index.json`'s `failures`; a character or kit entry with no look by design (motion
  clips, a hand pose, a floor plan) is left off and listed under `skipped`.
- Its test, `test_every_current_entry_is_one_tile_or_one_reason.py`, covers the planning and the index, which need no
  Blender.
