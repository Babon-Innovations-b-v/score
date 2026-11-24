# tools/props/bench/measures/

The prop benchmark's measures (#163, design on #162, PRD #159): one step's model of the prop route held to the
NVIDIA SimReady asset it was made from. `__init__.py` is the way in (its docstring has the interface and the input
dicts); the rest is private. Pure functions over plain arrays: the truth reader, the render and the runner live
elsewhere in the bench and hand in `{vertices, faces, face_material, box, mass, colliders, friction}` per side.

- **Strict by design** (owner, 2026-11-23: our checks are "not strict enough"). The made model is measured as its
  route laid it: no rescale ever hides a size error, the silhouettes are drawn by one camera framed on the truth (not
  compare.outline's boxed masks), and the turn that stands it on the truth is its up-axis error. A tie between axis
  turns (within `_align.TIE` of the best fit) takes the least-leaning one, so a symmetric shape is not charged for a
  turn that changes nothing. The turn and ICP are fitted on the surface seen from outside (`_mesh.outside`):
  NVIDIA's inside (a fridge's liner and shelves, ~80% of its surface) is what a picture cannot show, and on tc3 it
  stood the upright fridge on its head (#178).
- **The heading is held as laid** (`_heading`, #192): the axis turns above set a model laid round back first, so a
  box-like one a half or quarter turn off passed every shape measure (tc4r's desk and fridge). `orientation.heading`
  turns the model only about up from as laid and holds its own paint (the side's `painted`) to NVIDIA's look on the
  truth's outside, each finish weighted alike (a cable hole as much as the top), by correlation: TRELLIS.2 paints its
  picture's light in, so a colour difference took a right-laid terminal for a half turn. `MARGIN` and `FLOOR` are from
  tc4r's 15 made models.
- **Reuse, never copies.** The ring is tools/usd/compare.py's (YAWS, ELEVATION, FOV), the input view the close-up's
  (tools/props/closeup/check.py TURN_DEGREES, look_down), ownership split_compare.py's rule (OWN_PURITY,
  FINISH_LEAST, finishes_owned), the flat share and swell place_build/shapes', the least wall the model gate's,
  the finish bounds tools/props/library/likeness/measure.py's `passes`. Change those at their source.
- **BARS are set by the calibration pass** (tools/props/bench/calibrate, #163 step 3): each with its numbers beside
  it, the known-good copies passing with margin and the kind's other assets (laid at the truth's size) failing; a bar
  is never loosened to pass a made model. NVIDIA's own assets are open, many-pieced and thin-walled, so the
  cleanliness bars are against the truth's own value, never absolute.
- **What the calibration fixed here**: silhouettes drawn by pixel centres for every triangle size (dots left holes in
  a finely cut copy), materials carried by the exact nearest truth triangle and read by finish (surface), not by
  material prim (but a surface painted for one model by its material names: its prims are NVIDIA's finish groups, #168), the turn tie at 5% (sampling noise stood a copy on its head), overhang read off the drawn shape's
  convex hull (a hull over an open crate is NVIDIA's own collider), the rank and the floors against others laid at the
  truth's size with its twins (recoloured same geometry) left out, a single hull's own volume. A measure whose input a step lacks (a raw model's parts, mass, colliders) is left
  out, never failed.
- **The Newton drop runs in the runner** (tools/usd/drop.py on the truth's and the made model's convex colliders;
  #155: a triangle-mesh collider crashes Newton); `rested` compares the two rests. A collider piece with no volume (its points in a plane, tc6's anesthesia machine's card) is `_physics.Flat`: no volume, no inside, its outline its surface, and never convex. Finish likeness needs each matched
  pair drawn by tools/props/library/likeness; `finish_likeness` judges those measures.
- **The finish is judged on what each group got, not only the grouping** (#172, owner 2026-11-23: tc2's toaster body
  passed finish 4/4 in stainless #e0e0e0 where NVIDIA's is dark grey). Each made face carries its nearest truth
  triangle (`_finish.carried`), so each counted part is held to NVIDIA's look on its own faces (the truth's
  `face_look`, read off NVIDIA's maps): colour (CIE76 delta E of its surface's token from NVIDIA's albedo mean,
  `COLOUR_REACH`), metal or not (`METAL_REACH`), roughness (`ROUGHNESS_REACH`), class (sim.py's); `finish.colour`,
  `metal`, `roughness` and `class` are the area shares held; `see_through` (#186) the share of the parts over NVIDIA's
  glass (its `m_trans` and OmniGlass materials, over half a part's area) drawn see-through, and of see-through parts
  over it, at bar 1.0: the tc4r fridge's glass door drawn an opaque panel fails it. `pattern` (#186) the share whose
  drawn lightness detail (bench/run finish.drawn_patterns: the look's and NVIDIA's close-up's median high-pass on the
  part, at one scale) lies within PATTERN_REACH of NVIDIA's either way: the surgical chair's granite seat over a smooth
  one and the humidifier's lost ribs fail it. `drawn` (#198) the share whose colour as its look draws it (under
  the close-up's own light, the same view) lies within DRAWN_AB in a*b* and DRAWN_L in L* of the input close-up's
  on the part: tc5r's royal chair seat and navy heat gun, inside NVIDIA's albedo reach, fail it. `clipped` (#159) the
  share whose look draws no more of it clipped white than the input close-up does, within CLIPPED_REACH (a part that
  gives off light left out): tc6's blown-out locker and anesthesia machine, white on both sides by `drawn`, fail it. The made side's `looks` are its parts' settings as the
  route set them (bench/run finish.part_looks); a calibration copy wears its finishes' own library surfaces.
- **How cleanly the finishes meet** (`_edges`, #179; owner 2026-11-23: tc3s's "table and toaster mesh became messy
  compared to run 1"): a finish given triangle by triangle on TRELLIS.2's uneven triangles meets in a sawtooth and
  leaves specks. `edge_density` (finish edge length per area, read off surface points so NVIDIA's finishes, mostly
  pieces of their own, count) against the truth's; `edge_wander` (each run of shared finish edges against parabola
  fits behind, about and ahead of each point, across the edge within its faces, so corners, curves and the surface's
  bumps are no wander); `specks` and `speck_share` (islands of one finish inside another under a size and a few of the
  model's triangles: NVIDIA's modelled stickers are tens of triangles), on a made side with a look only those its look
  draws (`face_seen`, #159: tc5r's surgical chair counted 112, 98 inside its mechanism, under its seat and inside its
  wheels, its look clean; a texture's speckle is `pattern`'s and the picture judge's). The made side is read by its seen finishes
  (parts in one surface and look are one). NVIDIA's tune truths share few finish edges, so the wander and speck bars
  rest on them and on the tc3s models cut cleanly along a plane (run 1-like edges); the numbers are beside BARS.
- **Moving parts and joints** (`_joints`, #177, #161 rules 1 and 11): the truth's moving parts are the bodies its
  revolute and prismatic joints move (the joint's lesser-area body: the door, not the cabinet); each made face carries
  its nearest truth triangle's body (`_finish.carried`), so a made part and a truth part are compared on the made
  surface (area in common over area together), paired one to one best first. `parts.count_gap`, `faces_least`,
  `type_held`, `axis_most` (as lines), `pivot_most` (a hinge's pivot off NVIDIA's hinge line, over the diagonal),
  `range_most` (its open span against NVIDIA's). Its bars are design bars until the calibration pass reads the tune
  split's jointed truths; the made side's `face_part` and `joints` come from branch B's `parts` step.
- **A model with no NVIDIA truth** (`pictured`, `PICTURED_BARS`; #159: the 2099 cockpit cases) is held to its
  close-up and target size alone: the IoU of its outline through the camera fitted on the close-up (close_up_fit,
  the runner's), its box against the target, no open edge, crumb or bad face (its largest piece 0.99), the gate's wall at the
  target, its finish edges at the truth's absolute bars, every label of the close-up printed as a decal, its finishes
  of the classes the close-up shows and of no recipe it does not (`never`). The truth-relative bars are not judged.
- **The look by eye** (`picture`, #184): tools/props/bench/judge holds branch B's look to NVIDIA's render and the
  previous round's look (one Claude ask, EUR 0); measures.measured does not compute it, the runner adds the group.
  Its bars: no kind of judge.KINDS at fault, no regression, a drawn look.
- **The look reads its words** (`text_read`, `look.read` in BARS and PICTURED_BARS, #185; tc4r's sign drew a garbled
  "C" for tc3's clean "03" and every measure passed): each text mark of the close-up must be read back, as compared
  by `label_words`, where branch B's look drew it (bench/run finish.marks_read); a misread or unclear glyph fails.
- Not measured yet: self-intersecting faces (no free exact test at a million faces); the route's own checks
  (straight.py, the model gate's pass, sausage and lump) run in the calibration pass, not here.
- Check: `test_a_made_model_passes_only_where_it_matches_its_truth.py`, one table of made models against one small
  box truth, each row the bar a known fault must break or a known-small error must keep.
