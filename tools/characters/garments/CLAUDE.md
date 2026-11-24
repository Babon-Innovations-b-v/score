# tools/characters/garments/

Sewn clothes on a person of the people line (PRD #223, first slice #225): GarmentCode patterns sized to the person's
SOMA body, sewn and worn over one clip on Newton's VBD, a time-sampled OpenUSD point cache, library finishes, Blender
pictures. `__init__.py`'s docstring has the steps; `python -m tools.characters.garments <outfit.json> --out <folder>`
runs them (an outfit file per look in `data/people/outfits/`).

- **Licences, outputs included.** GarmentCode / pygarment (MIT, maria-korosteleva/GarmentCode pinned at d449629 by
  `inside/garment_env.sh`): its pattern programs, design files and measurement files only. Its simulation runs on a
  fork of NVIDIA Warp under a non-commercial licence: never installed, never imported (`pattern.py` refuses `warp`).
  Its SMPL-based bodies (`*smpl*`) are never read; the unread measurements come from its own mean body's measurement
  file (GarmentMeasurements' model). Newton and Warp (Apache-2.0) drape; Blender (GPL, outputs free) renders.
  Finishes are score_lib surfaces under their own entries' licences.
- **Not people_cloth.** `score/stages/people_cloth` keeps a built garment and simulates only its loose points; this
  sews whole garments. The people_cloth overlay's "never sew" is that stage's rule.
- **Cloth values are the library recipe's row** of `data/physics/cloth.json` (`cloth_material`, the people cloth
  stage's own conversion), never typed here. Solver and contact numbers name their source in `DRAPE`.
- **GarmentCode's own steps, Newton's solver**: the box mesh's triangles rest at their flat panels, seams sewn by
  shared points, a waistband's top worn on the skin, a neckline's sides drawn to the neck while sewing
  (`holds`, GarmentCode's attachments), speeds capped only while sewing.
- **Runs on this PC's card through the card queue** (`tools/cloud/backends/card_queue.py`), each step in its own
  Python: the score venv (body, measures, cache), GarmentCode's (`inside/pattern.py`), Newton's
  (`inside/drape.py`), Blender (`inside/render.py`, its missing libSM/libICE from `blender-mcp/libs`).
- Tests: `test_a_pattern_is_sized_to_the_body_that_wears_it.py` (a toy body of tubes; no GarmentCode, Newton or
  Blender).
