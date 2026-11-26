# tools/characters/hair/

Strand hair for the people line (PRD #223, first slice #227; experimental): grown in Blender on a kept person's
made hair, bound to the body by its UV, rendered with Cycles' Principled Hair BSDF and written as USD BasisCurves by
our own code. `groom.py` (Blender, its docstring has the steps and its outputs) and `basis_curves.py` (the venv's
pxr) are the whole route; nothing here is a row of the runner yet.

- **Only clean pieces.** Blender's own nodes (Geometry Nodes curves: Distribute Points on Faces, Interpolate Curves,
  Deform Curves on Surface, Raycast) and Cycles; no strand model or hair dataset (every released one is
  non-commercial: the deep dive on #56). A learned prior comes only from grooms made here.
- **The style is read, not invented**: `data/people/hair/<look>.json` holds what the look's close-up shows (length,
  curl, parting, fringe, colour) with who read it and when; groom.py takes its numbers from there.
- **The finish is the library's**: groom.py's shell route draws the people line's library surface the style names
  (its `surface`, colour and roughness). The whole person's strands wear the style's `library` surface: a strand
  finish written by `finish.py` (`hair_strands_ash_brown`, taken into score_lib as a draft) carries a `hair` block, a
  fibre's melanin and redness, roughness, radial roughness, coat, index and cuticle tilt from pbrt-v3's hair material
  (Chiang et al. 2016), each strand's spread and the tips' lightening, which `../face/blender_face.strands_material`
  draws in the Principled Hair BSDF's melanin terms. A new look's colour is a new finish there, with its source.
- **Nothing through the body**: every strand is kept off the rest surface, resampled and kept off again, and a strand
  that still crosses it at rest is left out whole (`uncrossed`); a root whose UV does not find it again is left out
  (`untorn`). `measures.json` counts roots off the surface and segments crossing the body at the bind and every clip
  frame; never loosen OFF_ROOT, PAST or the pushes to make those numbers pass.
- **The kept body's head is one made part**: woman_stair's face and hair are one Pixal3D shell whose dress paints the
  face skin and the hair the tee; `hair_materials` and `shell_faces` read that off the dress record. Another look
  may part them otherwise: look at a picture of the shell (the faces coloured) before growing on it.
- **Unreal groom, next slice**: Unreal imports Alembic in its groom schema (curves with `groom_root_uv`,
  `groom_width`, `groom_color`, `groom_guide`, `groom_group_id`, `groom_id`, `groom_closest_guides` and
  `groom_guide_weights`, imported in centimetres, Y up), binds it to the skeletal mesh by root UV and simulates it in
  Niagara. `basis_curves.py` already names its per-strand primvars `groom_root_uv` and `groom_guide` so that writer
  maps them one to one; the scalp UVs must be the same in Blender and Unreal.
- Run on this PC's card through the card queue (`tools/cloud/backends/card_queue.py run ... -- <blender> -b
  --python groom.py -- ...`), about 4 minutes. Its outputs (npz frames, USD, pictures) go to a tmp folder outside
  the repo; nothing generated is committed.
- Tests: `test_a_groom_reads_back_strand_for_strand_or_is_refused.py` (the writer; groom.py is proven by its pictures
  and measures, it needs Blender).
