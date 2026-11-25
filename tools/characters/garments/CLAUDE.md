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
- **GarmentCode's own steps, Newton's solver**: the box mesh's triangles rest at their flat panels (going over to them
  from as laid while the gravity-free fifth of sewing runs: rested flat at once, the seam triangles laid 15 to 50 times
  their panel overran Newton's float32 membrane), seams sewn by shared points, a waistband's top worn on the skin at its own level (`laying.worn_places`: carried
  to the skin nearest it, the box's flat panels 7 to 15 cm off her hips put the top 6 cm higher at the back's sides
  and held the side seams open), its whole ring held, the side seams' tops too, and spaced round her as it is cut
  (`laying.top_ring`: held at the flat panels' points alone, the side seams were left 16.5 cm unheld and the band's
  ends torn across them), a neckline's halves kept inside the planes either side of
  the neck (`holds`, GarmentCode's attachments: one-sided, a point inside its plane left), speeds capped only while
  sewing.
- **Runs on this PC's card through the card queue** (`tools/cloud/backends/card_queue.py`), each step in its own
  Python: the score venv (body, measures, cache), GarmentCode's (`inside/pattern.py`), Newton's
  (`inside/drape.py`), Blender (`inside/render.py`, its missing libSM/libICE from `blender-mcp/libs`).
- **A garment that does not stay seated fails the run** (`seated.py`, owner 2026-11-24: "clothes falling off"):
  shoulder seams off centre when sewn, a shoulder seam off the shoulder's top or moved over the clip, the neckline
  fallen below its places on the skin, the body out through the cloth over it, a garment out through the one
  laid over it (`layered`); `measures.json` carries each garment's `seating` and its `faults`,
  and the run exits non-zero after its pictures. Limits are never loosened to pass.
- **Other builds** (`shaped.py`, several people): an outfit's `body` ({"shape": {SOMA direction: standard
  deviations}, "height_m"}) reshapes the look's SOMA body in SOMA's own shape space (`SOMA_neutral.npz`,
  nvidia/soma-x, Apache-2.0; `SOMA_NEUTRAL` overrides its path) and scales it to the height. Direction 0 is left
  out: it carries SizeUSA's scan poses, its shorter bodies' arms down into their sides. A wider build's arms are
  turned out until none past the armpit's fold sinks in the torso at the bind or walking (`arms_cleared`, up to 20
  degrees; a build that needs more is refused): cloth caught between a sunk arm and the chest blew the drape up.
- **A relaxed clip is stood at ease first** (`relaxed_clip`, `../posture`, owner 2026-11-25: "the posture head ...
  so weird"): standing and walking get their feet under the hips, their arms hung against the skin that plays them
  and their gaze levelled with the face's own look counted, before any build clears the arms; a posture that still
  faults stops the run.
- **Layers** (an outfit's `layer_m` per garment): sewn a layer at a time, innermost first (`sewn_in_layers`); an
  outer garment's box mesh is laid that much further off the skin and outside the cloth sewn under it, so a shirt and
  the coat over it start apart and meet by contact as they are sewn (laid all at once, a jacket's hem lay inside the
  trousers' waistband box and the two tangled as the waistband was carried in). A garment over another's neckline
  holds its own neckline two cloth thicknesses further out per neckline under it.
- **A box mesh starts outside the body** (`inside/laying.py`): GarmentCode lays its panels round its own mean body,
  and on ours some points stand inside (a tee's sleeve fronts up to 5.7 cm in the arms, jeans' front crotch curve
  above the crotch between thighs that cross each other). Each is put out through its nearest skin, else the
  shortest way out along an axis; one left inside refuses the garment in the drape, never sewn.
- **Crossed cloth is left out of self contact** (`laying.crossing_filters`): VBD's self contact holds a crossed pair
  together, and woman_stair_modern's tee, its sleeve caps laid through its torso by GarmentCode's box mesh, was held
  behind her as she walked until it blew up (2026-11-25). A box mesh closes with no self contact in the gravity-free
  fifth of sewing; self contact then starts with the pairs still crossed left out, looked for again before the turn.
- **Trouser legs are laid over her legs** (`laying.over_legs`): GarmentCode lays a leg's panels flat, the back one
  reaching far to the side, so the laid leg stood 12 cm outside hers, its inseam strip through her calf; sewn, the lower
  leg caught on the wrong side of the calf and hung as a flap (#225 rounds 6 and 8). Each leg is moved across over
  the body's leg before laying out, short of the crotch's middle. A torn edge is judged against its cut length, not
  its sewn one (a garment torn as it was sewn passed).
- **A slim leg is taken in at the knee** (an outfit garment's `knee_ease_cm`, `inside/pattern.py` `slim_legs`):
  GarmentCode's Pants run each leg straight from the thigh to the hem, so jeans cut to a slim hem stood 56 cm round a
  37 cm knee and gathered at the calf. Each leg seam gets a point at the knee's height as cut, moved in to the knee's
  girth (`measure.below_knee`) and the ease, and the stitches are matched again; a leg narrower than the calf is
  refused.
- **Neckline holds keep a point from going further out, never pull it in** past where the pattern lays it (drawn in
  at once, a dress's and a jacket's neckline ends were gathered into lumps on the shoulders).
- **Bands** (`bands.py`, an outfit garment's `bands`: tape round the torso over the hem and round each sleeve over
  the cuff) are cut out of the cloth along their edges in the point cache and bound to their own library surface.
  The garments' own finishes (high-visibility yellow, retroreflective tape) are written by `finishes.py` for
  score_lib take-in. GarmentCode's box mesh
  crossing itself (its SimpleLapel collar, 2026-11-24) is refused in `inside/pattern.py`, never draped.
- **Fabrics and construction marks** (owner 2026-11-25: flat single-colour basic patterns "look from 1950"):
  `fabrics.py` draws denim (3/1 twill, ring-dyed indigo) and jersey (V loops, heather melange) tiles at their real
  thread counts, and decals (seam lines, topstitching, hems, a rib neck, pockets, a fly, belt loops, rivets) at their
  makers' measures, written as score's own score_lib surfaces (MIT) for take-in. `details.py` lays an outfit
  garment's `details` on its cloth as `/Outfit/Garments/<name>_details`: strips along seams and open edges (from the
  pattern's panels: a seam is an edge two panels share), patches at an anchor of a panel, each point carried by its
  flat triangle and lifted past the cloth's drawn thickness. GarmentCode's halved panels' centre seams a real
  garment has none of are listed `plain seams`.
- **Accessories** (shoes, a belt: `../accessories`, #228) are fitted after the drape from the outfit file's
  `accessories` and written into the same `outfit.usda`; their faults fail the run like a garment's.
- Tests: `test_a_garment_is_sized_to_and_stays_on_the_body_that_wears_it.py` (a toy body of tubes measured, a toy tee
  on a toy torso worn each way; no GarmentCode, Newton or Blender).
