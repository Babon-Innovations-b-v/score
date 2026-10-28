# score/stages/sim_body/inside/sizing/

MyoFullBody sized to one person's SOMA body (#70: SOMA is the truth, its size included): `Size(rig)` from the person's
rig and mesh at its bind; `Size.scales` gives each body's scale, every bone group (trunk and pelvis included) scaled
evenly so its stretch at the default pose is SOMA's joint distance, all groups solved together by scipy's bounded
`least_squares` on the model posed as `sized` places it (`posed_lengths`); `Size.weigh` gives each group's bodies its
mass, centre of mass and inertia's trace from SOMA's segment volumes (`volumes`); `assumed` marks what SOMA does not
give (muscle strength, joint ranges, segment density, bone shape) with a plausible range; `sized` scales the spec
body by body; `path_lengths` reads each muscle's path for OpenSim's muscle scaling.

- Measured 2026-10-28 on the template rig (both test walkers' person): every group's stretch within 0.1 mm of SOMA's
  after sizing, against 15 of 22 within 1 cm with the old sizing (limbs by joint distance, the rest by standing
  height). The widths are not sized: the hip joints stand 65 mm narrower than SOMA's, the shoulders 35 mm wider
  (recorded in `assumed`'s bone shape); placing the joint centres is #70's solver's.
- The torso is placed in lumbar1 by its own scale (`OWN_PLACED`): its origin sits 8.9 cm below lumbar1's, so by its
  parent's scale a longer lumbar stretch moved T12/L1 down and no scale fit Spine2 (measured 2026-10-28).
- A body under `FRAME_KG` is a frame, not a bone (MyoFullBody's phantoms carry 1 g and inertias of several kg m2):
  `weigh` leaves it as sized: counted in, the shoulder's and upper arm's own inertias summed 3.7 and 7.7 kg m2
  against SOMA's 0.03 and 0.05 (measured 2026-10-28).
- Never size a group by the landmark joint centres: they stand 4 to 24 mm off SOMA's joints (`landmarks`), and the
  sim body's joints are to sit on SOMA's. They are the solver's starting shape.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
