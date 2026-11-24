# tools/characters/face/

A person's face (#226, PRD #223; experimental, a first slice): the SOMA body's own face as the base, ICT-FaceKit's
face fitted onto its head for detail and joined into its skin, with eyes, teeth, gums and lashes; MHR's 72 expressions
the controls of both; every finish a score_lib surface; drawn close up in Blender.

- `body_face.py` (the motion environment: SOMA-X): the kept person's body (`made/fit/identity.npz`, SAM 3D Body's MHR
  read) at rest on SOMA-X's mid mesh, and MHR's 72 expressions carried onto it by SOMA-X's own MHR transfer.
- `ict.py`: ICT-FaceKit fetched at its pinned commit and packed once into a capped cache (`~/.cache/score/ict-facekit/
  <commit>/model.npz`, 22 MB, the OBJs dropped); nothing of it is in the repo.
- `fit.py`: the face's similarity and identity solved to the body's head (eyes on the eye joints, the narrow face on
  the skin), the band within `BLEND_METRES` of its border moved by its border's (smoothed) moves onto the skin, by its
  share of the body (ICT's jaw stood 20 mm off the officer's; each point snapped on its own, the ears were crushed
  flat), the body cut inside a wall of body points drawn along the border plus the skin under the face near the
  border joined to that cut (cut by nearness alone, the neck under the jaw and the skin before the ear were cut far
  past it; the wall alone left half its points inside the border and the strip folded in flaps), SOMA-X's filled eye
  and mouth bags cut with it, and a strip zipped between the two loops by their places along the face's border: one
  shut skin.
- `expressions.py`: MHR's control names onto ICT's ARKit-named expressions; a control ICT has none for moves the face
  by the body's own MHR offsets. On the face, each control is ICT's expression blended into the body's offsets by the
  face's share of the body (1 on the border), so the seam never opens.
- `face.py`: the pieces (skin, mouth, teeth, eyes by UV ring, lashes grown as thin ribbons along ICT's lash cards,
  tears), `face.npz`, and the stills through the card queue (`blender_face.py`, Cycles, each finish the library
  entry's own `material.usda` imported by Blender's USD reader). `finishes.py` writes the face's own finishes as
  score_lib drafts (taken in with `score-lib take-in`).
- Run: `<motion python> body_face.py <identity.npz> <body.npz>`, then `python face.py <body.npz> <out>` (SCORE_LIB_ROOT
  the score_lib checkout).
- **Look at the stills.** The fit's numbers (median skin distance) say it is near; only the close-ups say the seam,
  the lids and the mouth are right.

## Licences

- ICT-FaceKit (USC ICT Vision and Graphics Lab), MIT, code and model, commit `ict.COMMIT`.
- MHR's expressions and body (Meta), Apache-2.0, through nvidia/soma-x's `mhr_model_lod1.pt` (SOMA-X Apache-2.0).
- Not here: FLAME (any version before 2023 Open), SMPL or SMPL-X files, DECA, EMOCA, Pixel3DMM, MetaHuman.
