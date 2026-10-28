# score/stages/sim_body/inside/sizing/

MyoFullBody sized to one person (#64): `limb_lengths` (the person's thigh, shin, foot, upper arm and forearm from
its rig's bind), `scales_of` (each body's scale: a limb by its length over the model's, every other body by the
standing height over the model's, a body not starting a segment its parent's), `sized` (the spec scaled body by body,
its mass brought to the person's, `WRAPPER_KG` left for #60's wrappers) and `path_lengths` (OpenSim's muscle scaling).

- #70 replaces the parameterisation here: bone-group sizes as the person's constants, starting from SOMA mesh
  landmarks, masses from SOMA's segment volumes, assumed inputs marked.
- Its test runs in Newton's own Python (MuJoCo pinned there) by subprocess and prints `skipped` where no env is built.
