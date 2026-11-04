# score/stages/sim_body/inside/sizing/

MyoFullBody sized to one person's SOMA body (#70: SOMA is the truth, its size included): `Size(rig)` from the person's
rig and mesh at its bind; `Size.scales` gives each body's scale, every bone group (trunk and pelvis included) scaled
along its length (a limb's width by its girth, below) so its stretch (`SIZE_ENDS`: two landmarks or joint centres the landmarks define, the same rule on both
models) at the default pose is SOMA's on its skin at the bind, all groups solved together by scipy's bounded
`least_squares` on the model posed as `sized` places it (`posed_lengths`); `Size.weigh` gives each group's bodies its
mass, centre of mass and inertia's trace from SOMA's segment volumes (`volumes`); `assumed` marks what SOMA does not
give (muscle strength, joint ranges, segment density, bone shape) with a plausible range; `sized` scales the spec
body by body; `path_lengths` reads each muscle's path for OpenSim's muscle scaling.

- Measured 2026-10-28 on the template rig (both test walkers' person): every group's stretch within 0.1 mm of SOMA's
  after sizing, against 15 of 22 within 1 cm with the old sizing (limbs by joint distance, the rest by standing
  height). The joints' widths are not sized: the hip joints stand 65 mm narrower than SOMA's, the shoulders 35 mm wider
  (recorded in `assumed`'s bone shape); placing the joint centres is #70's solver's.
- **A limb's bones are as wide as its girth asks** (#70, 2026-11-01, the coordinator's decision): a body's scale is
  three, one per axis of its frame; in `GIRTH_GROUPS` (upper arm, forearm, hand, thigh, shin, foot) the axis nearest
  the group's stretch (`long_axes`) takes the length's scale and the two across it that times the person's girth for
  its length over SOMA's mean shape's (`volumes.slenderness`, `MEAN_SLENDERNESS`: the mean shape's limbs are where
  MyoFullBody sized evenly fits). Measure `MEAN_SLENDERNESS` again with `Size(rig).slender` on the mean shape's rig
  (level 1's `mean` body, both sides averaged) after a change to the measure. The limb meshes stand in their bodies'
  frames, so a mesh's scale per axis is exact; the forearm's bones lie 11 degrees off the ulna's y, the feet 19 off
  the calcaneus's x, the fingers up to 30 off their hand's line. The toes are left out: their short stretch's girth
  reads 0.79 to 1.43 times the mean shape's over level 1's 41 bodies. env1 (the template person, a slim one): upper
  arm 0.82, forearm 0.89, hand 0.98, thigh 0.84, shin 0.87, foot 1.00 of its length's scale.
- **A foot is as wide across its forefoot as SOMA's** (#70, 2026-11-02): the forefoot body's axis across the foot
  (calcn's z) takes SOMA's metatarsal heads apart on its skin over MyoFullBody's heads' bone points apart, each across
  the heel to the heads' middle (`FOOT_WIDTH`, `forefoot_width`, `Size.fixed`), not the length's or girth's scale.
  MyoFullBody's heads stand 85.8 mm apart, SOMA's skin's 74.1 (env1), 73.4 (the mean shape), 79.0 (g01): env1's
  calcanei 0.864 across, not 1.0275. Measured on main 67ce22be's env1 path, the calcanei 9.8 and 11.3 % outside
  standing, 20.0 and 16.7 % seated; across alone at 0.85 standing 3.7 and 6.3 %, their height (y) changing nothing,
  the length a little (the heel's back stands 3 mm behind the skin's on the template); seated the share stays 13 % at
  0.85: the seated foot is placement, not shape. The talus (no bone outside) and the toes keep their rule.
- **A kneecap lies inside SOMA's skin at every bend of its knee** (#70, 2026-11-04, `kneecaps`): SOMA's linear-blend
  skin caves up to 17 mm in at the front of a bent knee (env1 seated, 88 deg), and MyoFullBody's kneecap, sized with
  its femur, stood up to 10 mm proud of the mean shape's knee even straight: the thigh's region (femur and patella)
  read 26 % outside seated, 23 points of it the patella. Each kneecap's two slides' polynomials in the knee are
  refitted (`in_range`: within the slides' published ranges at every bend, the exact QP by daqp since 2026-11-04;
  scipy's SLSQP failed at its optimum by chance, the mean body's lunge and twist on one machine) to the source's plus the move that lays
  its every bone vertex inside SOMA's skin posed at that bend (`kneecap_moves`: the femur laid on SOMA's thigh by its
  three landmarks, SOMA's shin turned about its knee joint by the model's bend less SOMA's own at its bind, which its
  tibia's five landmarks give: env1's bind knee stands 15 deg bent, the measure's skin and inside test). env1: moved
  6.4 mm straight, 26.6 at 90 deg, 33.9 at the range's 120; its forward slide 7.8 mm back straight, 12.4 at 88 deg,
  within 1 mm of its range's end from 88 deg on.
- The torso is placed in lumbar1 by its own scale (`OWN_PLACED`): its origin sits 8.9 cm below lumbar1's, so by its
  parent's scale a longer lumbar stretch moved T12/L1 down and no scale fit Spine2 (measured 2026-10-28).
- A body under `FRAME_KG` is a frame, not a bone (MyoFullBody's phantoms carry 1 g and inertias of several kg m2):
  `weigh` leaves it as sized: counted in, the shoulder's and upper arm's own inertias summed 3.7 and 7.7 kg m2
  against SOMA's 0.03 and 0.05 (measured 2026-10-28).
- Size by the landmarks, never by SOMA's skeleton joints (#70, 2026-10-29): SOMA's joints stand off the anatomical
  centres (the ankle 16 mm below the malleoli's middle on both models, the elbow 11), so a joint-to-landmark ratio
  pulled the shins short. The hips are Harrington's from the ASIS and PSIS on both models (owner, 2026-10-29:
  "Anatomical hip"); SOMA's hip joints, 19.4 mm wider a side, are only the measure. The masses' centres still stand
  at SOMA's joints (`soma_point`): where a group's mass sits is not its length.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
- A person's mesh is filled with cells once (`filled`, keyed by the mesh's bytes; 2026-10-31): level 1's centre sets
  size the person anew, its mesh the same (0.47 s a set).
- **No body's inertia sits on its triangle's edge** (`balanced`, 2026-11-04): MyoFullBody's lumbar vertebrae have
  their largest principal inertia exactly the other two's sum; sizing and weigh keep it, the written 6 digits tipped it
  past by about 1e-8, and SolverMuJoCo's compile failed the clip ('inertia must satisfy A + B >= C') by how its
  scales rounded. Each body's largest is kept 1e-5 under the sum before writing; more than 1e-4 over raises.
