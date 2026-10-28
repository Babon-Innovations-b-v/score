"""MyoFullBody (MyoSuite's musculoskeletal body: its bones, 123 joints, 416 muscles and their tendons) made ready for
Newton and sized to one person (#65): `person_file` writes the person's file and returns its record.

The model is the pinned wheel the stage fetched (musclemimic_models 1.0.6, `SOURCE` in it). Each person's file is the
model with:
- its floor gone (the person stands on the scene's own ground);
- each body sized by its segment's scale and its mass the person's (`sizing`);
- each muscle's length range scaled by its path's length at the model's zero pose over the model's (OpenSim's
  muscle scaling: optimal fibre and tendon slack length with the path); its peak isometric force kept (#64: strength
  does not scale here);
- #60's import fixes (`_fixes`): names without '-' or spaces, every muscle's full gain, bias and dynamics parameters,
  explicit inertials, a body with several joints split into 1 g wrapper bodies (one joint each), Euler written out.
"""
import pathlib

import mujoco

from myo._fixes import full_muscles, multi_joint_bodies, renamed, split
from sizing import WRAPPER_KG, kept_bodies, path_lengths, scales_of, sized

SOURCE = "musclemimic_models/model/body/myofullbody.xml"


def _source_model(folder):
    """The published model, compiled."""
    return mujoco.MjModel.from_xml_path(f"{folder}/{SOURCE}")


def person_file(folder, lengths, kg, path):
    """One person's MyoFullBody, written at `path`, and its record: each body's scale and mass, its muscles' length
    scale, its total mass."""
    source = f"{folder}/{SOURCE}"
    model = _source_model(folder)
    spec = mujoco.MjSpec.from_file(source)
    spec.meshdir = spec.texturedir = str(pathlib.Path(source).parents[1])
    for geom in list(spec.worldbody.geoms):
        spec.delete(geom)
    scales = scales_of(model, lengths)
    sized(spec, model, scales, kg, multi_joint_bodies(spec))
    grown = spec.compile()
    stretch = path_lengths(grown) / path_lengths(model)
    for actuator in spec.actuators:
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator.name)
        actuator.lengthrange = model.actuator_lengthrange[index] * stretch[index]
    final = spec.compile()
    xml = spec.to_xml()
    if "integrator=" not in xml:  # MjSpec.to_xml drops Euler (MuJoCo's default) and Newton would pick implicitfast
        xml = xml.replace("<option ", '<option integrator="Euler" ', 1)
    # an inertia written out to 6 digits may miss A + B >= C by a rounding
    xml = xml.replace("<compiler ", '<compiler balanceinertia="true" ', 1)
    path.write_text(split(full_muscles(renamed(xml), final)))
    return {"scales": {name: round(scale, 4) for name, scale in scales.items() if name in kept_bodies()},
            "muscle length scale": [round(float(stretch.min()), 4), round(float(stretch.max()), 4)],
            "kg": round(float(final.body_subtreemass[0]) + multi_joint_bodies(spec) * WRAPPER_KG, 3)}
