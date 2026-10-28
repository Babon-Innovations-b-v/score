# score/stages/sim_body/inside/fit/

The clip's SOMA segment turns to MyoFullBody's joint angles, OpenSense's way (the parent overlay): `calibration`,
`offsets` (IMUPlacer, its heading corrected), `refitted` (the offsets again over the whole clip), `motion` (per frame
damped least squares on the leading dofs, couplings kept, the pelvis where SOMA's Hips carry it, the standing feet
held on the ground) and `landed`.

- #70 replaces this module's solve: one call fitting the person's constants and every frame's angles to the bone
  groups' rotations and the landmarks' markers, mink per frame and scipy's `least_squares` over the constants.
- Its test runs in Newton's own Python by subprocess and prints `skipped` where no env is built.
