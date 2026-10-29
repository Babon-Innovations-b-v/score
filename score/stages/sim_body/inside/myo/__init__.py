"""MyoFullBody (MyoSuite's musculoskeletal body: its bones, 123 joints, 416 muscles and their tendons) made ready for
Newton and sized to one person (#65): `person_file` writes the person's file and returns its record.

The model is the pinned wheel the stage fetched (musclemimic_models 1.0.6, `SOURCE` in it). Each person's file is the
model with:
- its floor gone (the person stands on the scene's own ground);
- each bone group sized to the person's SOMA body, its masses from SOMA's volumes (`sizing`);
- each muscle's length range scaled by its path's length at the model's zero pose over the model's (OpenSim's
  muscle scaling: optimal fibre and tendon slack length with the path); its peak isometric force kept (#64: strength
  does not scale here); then its tendon slack length lengthened where it stands stretched (`resting`);
- #60's import fixes (`_fixes`): names without '-' or spaces, every muscle's full gain, bias and dynamics parameters,
  explicit inertials, a body with several joints split into 1 g wrapper bodies (one joint each), Euler written out.
"""
import pathlib

import mujoco
import numpy as np

import resting
from myo._fixes import full_muscles, multi_joint_bodies, renamed, split
from sizing import WRAPPER_KG, assumed, body_scales, kept_bodies, path_lengths, sized, stretches, ungrouped_kg

SOURCE = "musclemimic_models/model/body/myofullbody.xml"


def _source_model(folder):
    """The published model, compiled."""
    return mujoco.MjModel.from_xml_path(f"{folder}/{SOURCE}")


def _fresh(source):
    """A new spec of the published model, its floor gone."""
    spec = mujoco.MjSpec.from_file(source)
    spec.meshdir = spec.texturedir = str(pathlib.Path(source).parents[1])
    for geom in list(spec.worldbody.geoms):
        spec.delete(geom)
    return spec


def person_file(folder, size, kg, path, constants=None):
    """One person's MyoFullBody, written at `path`, sized by `size` (a `sizing.Size` of the person's SOMA) and, when
    given, the fit's `constants` ({"sizes": {group: factor}, "joints": {body: [3] m}}: each group's scale times its
    factor, each body moved in its parent), and (its record, each body's scale): the record holds each group's scale
    and its length against SOMA's, the inertia scale per group, its muscles' length scale, its total mass and what is
    assumed."""
    source = f"{folder}/{SOURCE}"
    model = _source_model(folder)
    scales = size.scales(model)
    if constants:
        factors = body_scales(model, {group: constants["sizes"].get(group, 1.0) for group in stretches(size.table)},
                              size.table)
        scales = {body: scale * factors[body] for body, scale in scales.items()}
    spec = _fresh(source)
    wrappers = multi_joint_bodies(spec)
    sized(spec, model, scales, kg, wrappers)
    for body, move in (constants or {}).get("joints", {}).items():
        spec.body(body).pos = np.asarray(spec.body(body).pos) + move
    grown = spec.compile()
    factors = size.weigh(spec, grown, scales, kg - wrappers * WRAPPER_KG - ungrouped_kg(grown, size.table))
    grown = spec.compile()
    stretch = path_lengths(grown) / path_lengths(model)
    for actuator in spec.actuators:
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator.name)
        actuator.lengthrange = model.actuator_lengthrange[index] * stretch[index]
    stretched = spec.compile()
    moves = resting.slack_moves(stretched)
    for actuator in spec.actuators:
        index = mujoco.mj_name2id(stretched, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator.name)
        actuator.lengthrange = stretched.actuator_lengthrange[index] + moves[index]
    final = spec.compile()
    xml = spec.to_xml()
    if "integrator=" not in xml:  # MjSpec.to_xml drops Euler (MuJoCo's default) and Newton would pick implicitfast
        xml = xml.replace("<option ", '<option integrator="Euler" ', 1)
    # an inertia written out to 6 digits may miss A + B >= C by a rounding
    xml = xml.replace("<compiler ", '<compiler balanceinertia="true" ', 1)
    path.write_text(split(full_muscles(renamed(xml), final)))
    return {"scales": {name: round(scale, 4) for name, scale in scales.items() if name in kept_bodies(size.table)},
            "lengths": size.record(final, scales), "inertia scale": {group: round(factor, 3)
                                                                     for group, factor in factors.items()},
            "centre of mass moved cm": size.moved,
            "muscle length scale": [round(float(stretch.min()), 4), round(float(stretch.max()), 4)],
            "kg": round(float(final.body_subtreemass[0]) + wrappers * WRAPPER_KG, 3),
            "resting": resting.record(stretched, final, moves),
            "assumed": assumed(final, scales, size.rig)}, scales
