# tools/characters/face/

A person's face (#226, PRD #223; experimental, a first slice): the SOMA body's own face as the base, ICT-FaceKit's
face fitted onto its head for detail and joined into its skin, with eyes, teeth, gums and lashes; MHR's 72 expressions
the controls of both; every finish a score_lib surface; drawn close up in Blender.

- `body_face.py` (the motion environment: SOMA-X): the kept person's body (`made/fit/identity.npz`, SAM 3D Body's MHR
  read) at rest on SOMA-X's mid mesh, and MHR's 72 expressions carried onto it by SOMA-X's own MHR transfer.
- `ict.py`: ICT-FaceKit fetched at its pinned commit and packed once into a capped cache (`~/.cache/score/ict-facekit/
  <commit>/model.npz`, 22 MB, the OBJs dropped); nothing of it is in the repo.
- `fit.py`: the face's similarity and identity solved to the body's head (eyes on the eye joints, the narrow face on
  the skin), the identity held near ICT's mean (`IDENTITY_PULL`; weakly held it chased SOMA's coarse head into puffed
  cheeks and a lump down the throat, 2026-11-25) and refused past `IDENTITY_LIMIT` standard deviations
  (`within_population`, a caricature); the face's skin is ICT's face piece plus each ear's back (`ear_backs`: head_and_neck points grown from the
  face's border while they face the head; ICT's face piece ends on the helix's back, and laid as the border, the
  helix was glued flat onto the head); the band within `BLEND_METRES` of its border moved by its border's (smoothed)
  moves onto the skin, by its share of the body (ICT's jaw stood 20 mm off the officer's), the body cut inside a wall
  of body points drawn along the border plus the skin under the face near the border joined to that cut, SOMA-X's
  filled eye and mouth bags cut with it, the cut cleared off the face's border (`cleared`, `LOOP_CLEAR`: left on it,
  the strip folded into a ridge down the neck), and a strip zipped between the two loops by their places along the
  face's border: one shut skin. The throat is the body's (`throat_share`, `throat_laid`): ICT's face piece runs down
  the neck to the collar, and below the jaw's outline it lies on SOMA's smoothed skin (its own stood 8 to 10 mm proud,
  a lump down the throat; owner, 2026-11-25: "also geeze neck"). `ears_standing` refuses a squashed ear (its edge's
  distance off the head and its back's depth, `EAR_PROTRUSION_MM`, `EAR_DEPTH_MM`), `neck_normal` a neck whose girth
  or chin-to-notch length is outside the normal range for the height (ANSUR II, the sternomental distance), and
  `seam_smooth` a ridge or fold on the join (a strip triangle turned more than `SEAM_TURN_DEGREES` from the skin under
  it); the run's measures go to `<out>/measures.json`.
- `expressions.py`: MHR's control names onto ICT's ARKit-named expressions; a control ICT has none for moves the face
  by the body's own MHR offsets. On the face, each control is ICT's expression blended into the body's offsets by the
  face's share of the body (1 on the border), so the seam never opens.
- `strands.py`: the brows and lashes as short strands, grown as the hair route grows (#227) and drawn as Blender hair
  curves in its Principled Hair BSDF (the library surface's colour): brows over a band along ICT's brow landmarks,
  pointing up at the head and outward and down at the tail, each point bound to the skin under it; lashes rooted on
  ICT's lash cards' root edges (the lids' margins) and curled off them (ICT's cards are flat strips standing straight
  out, their curl painted in ICT's picture), each bound to its root's card triangle so it turns with a blink.
  `checked` refuses brow hairs off or inside the skin.
- `face.py`: the pieces (skin with its region tones, mouth, teeth, eyes by UV ring, the cornea, brows and lashes from
  `strands.py`, tears); `tones` marks each skin point's flush (cheeks, nose, chin, ears), thin bluish skin (under the
  eyes) and lips round ICT's 68 landmarks, the skin's library record saying what each region is toned to; `cornea` is a
  clear shell over each eye, Gullstrand's corneal dome over the iris and a tear film over the white, so the eye
  catches the sky; `face.npz`, and the stills (front, three quarters and the side, which shows the neck) through the card queue (`blender_face.py`, Cycles, each finish the library
  entry's own `material.usda` imported by Blender's USD reader). `finishes.py` writes the face's own finishes as
  score_lib drafts (taken in with `score-lib take-in`): what UsdPreviewSurface cannot hold (light through the skin,
  regions, crevices, the oil's coat, the eye white's vessels, the iris's fibres, the cornea's glass) rides in each
  record and `blender_face.library_material` lays it on. The stills end with one hand at rest (`hand.png`): the skin
  is one finish over the whole body, so a face and a hand show the same skin.
- `skin_scan.py`: the skin's small detail photographed, not procedural (procedural pores and noise read as wax,
  owner 2026-11-25): a 41 mm forehead square of Infinite-Realities' head scan (CC BY 3.0) made periodic, its colour
  over 6 mm and its relief over 1 mm taken out, written as the skin finish's own tiles (`skin_detail_colour.png`,
  `skin_detail_height.png`) and laid by box projection on the object's coordinates; the scan cached under
  `~/.cache/score/skin-scan/<commit>/`, checked by its sha256.
- Run: `<motion python> body_face.py <identity.npz> <body.npz>`, then `python face.py <body.npz> <out>` (SCORE_LIB_ROOT
  the score_lib checkout).
- **Look at the stills.** The fit's numbers (median skin distance) say it is near; only the close-ups say the seam,
  the lids and the mouth are right.

## Licences

- ICT-FaceKit (USC ICT Vision and Graphics Lab), MIT, code and model, commit `ict.COMMIT`.
- MHR's expressions and body (Meta), Apache-2.0, through nvidia/soma-x's `mhr_model_lod1.pt` (SOMA-X Apache-2.0).
- The skin's detail tiles: "Infinite, 3D Head Scan by Lee Perry-Smith", CC BY 3.0 (keijiro/InfiniteScan's
  License.txt at `skin_scan.COMMIT`); the tiles carry its licence block and credit in score_lib
  (`infinite_head_scan`), never MIT.
- Not here: FLAME (any version before 2023 Open), SMPL or SMPL-X files, DECA, EMOCA, Pixel3DMM, MetaHuman.
