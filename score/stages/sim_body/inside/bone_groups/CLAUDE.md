# score/stages/sim_body/inside/bone_groups/

Which MyoFullBody body each SOMA segment rides (`RIDES`), the segments the fit follows as orientation sensors
(`TARGETS`), the femurs that place the pelvis (`HIPS`), the feet (`FEET`), the lumbar leaders RRA moves (`TRUNK`) and
what MyoFullBody lacks (`LACKS`, recorded with each body); `sided` and `sided_map` write a `{Side}` name out for both
sides. Pure Python: no MuJoCo, no Newton, so its test runs in the score venv.

- These are SCORE's own tables (#70: the bone-group and static calibration tables land here as code with their test).
  Never a per-joint table of axes, weights and offsets, nor anything fitted to reference data (the parent overlay:
  the owner's own method is never used).
