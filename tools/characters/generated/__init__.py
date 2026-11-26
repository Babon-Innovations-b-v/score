"""The generated person (#223; CONTEXT.md "generated person"), mended where the generator fails: its eyes (`eyes.py`,
its docstring has the steps) and its hair. A TRELLIS.2 model's hair, painted on one solid shell with the head, is
split off and regrown as strands in the generated hair's own shape (owner, 2026-11-26: "just segment the hair and
turn into strands like original"); a man's lumpy painted beard the same way, as short facial hair.

1. `labels.py`: which triangles are hair, from the model's own paint (a colour vote against the skin's and the
   clothes', settled by neighbours, joined to the head's top) and place (never the face in front). `pictures.py` draws
   them.
2. `scalp.py`: the hair's triangles removed, a smooth skull-shaped scalp closes the hole, tucked under the skin at its
   edge; where the hair hung over a neck the model never had, the neck's back.
3. `volume.py`: the hair's shape as a volume (inside the model, near its hair, outside the skin and scalp) with its
   depth, the strands' layers.
4. `strands.py`: roots on the scalp at a head's density, guides grown through the volume along the comb of
   `../whole/hair.py` (its parting, whorl, density, baby hairs, locks, cut, wave, flyaways and frizz, reused), ending
   where the shell ends. `beard.py`: the beard's triangles smoothed into skin and short strands grown on it.
5. `fibre.py`: the library's strand finish with its melanin fitted to the close-up's hair colour.
6. `blender_sheet.py` (Blender, CPU): the raw model and the regrown one drawn the photo way, side by side.
"""
