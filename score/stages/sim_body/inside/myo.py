"""MyoFullBody (MyoSuite's musculoskeletal body: its bones, 123 joints, 416 muscles and their tendons) made ready for
Newton and sized to one person (#65). Runs in Newton's own Python beside sim_body.py, which imports it.

The model is the pinned wheel the stage fetched (musclemimic_models 1.0.6, `SOURCE` in it). Each person's file is the
model with:
- its floor gone (the person stands on the scene's own ground);
- each body sized by its segment's scale (`scales_of`): a limb by the person's own SOMA joint distance over the
  model's (thigh, shin, foot, upper arm, forearm), every other body by the person's standing height over the model's
  (#64: SOMA's hip and shoulder widths carry no per-person signal); a body takes its parent's scale unless it starts
  a segment. Positions, geoms, sites, joint anchors, meshes and a slide joint's coupling and range scale with it;
- its mass the person's (#64's rule, worked out by the stage): each body's mass the model's times its scale cubed,
  all brought to the person's total, its inertia with its mass and its scale squared;
- each muscle's length range scaled by its path's length at the model's zero pose over the model's (OpenSim's
  muscle scaling: optimal fibre and tendon slack length with the path); its peak isometric force kept (#64: strength
  does not scale here);
- #60's import fixes: names without '-' or spaces, every muscle's full gain, bias and dynamics parameters, explicit
  inertials, a body with several joints split into 1 g wrapper bodies (one joint each), Euler written out.
"""
import pathlib
import re
import xml.etree.ElementTree as ElementTree

import mujoco
import numpy as np

SOURCE = "musclemimic_models/model/body/myofullbody.xml"
# The segments a person's SOMA rig gives a length for, by the MyoFullBody body that starts each (each side), and the
# body its far end is: the model's own length is the distance between their origins at its zero pose.
LIMBS = {"thigh": ("femur", "tibia"), "shin": ("tibia", "talus"), "foot": ("talus", "toes"),
         "upper arm": ("humerus", "ulna"), "forearm": ("ulna", "lunate")}
SIDES = {"l": "Left", "r": "Right"}
WRAPPER_KG = 0.001  # a split body's wrapper (MuJoCo's boundmass for MyoFullBody, which Newton does not apply)
WRAPPER_INERTIA = "1e-4 1e-4 1e-4"
NAMED = ("model", "name", "site", "sidesite", "tendon", "joint", "joint1", "joint2", "body", "body1", "body2", "geom",
         "geom1", "geom2", "childclass", "class")


def source_model(folder):
    """The published model, compiled."""
    return mujoco.MjModel.from_xml_path(f"{folder}/{SOURCE}")


def body_id(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def standing_height(model):
    """The model's standing height at its zero pose (metres): its bone meshes' top over their bottom."""
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    tops, bottoms = [], []
    for geom in np.flatnonzero(model.geom_type == mujoco.mjtGeom.mjGEOM_MESH):
        mesh = model.geom_dataid[geom]
        points = model.mesh_vert[model.mesh_vertadr[mesh]:model.mesh_vertadr[mesh] + model.mesh_vertnum[mesh]]
        heights = (points @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom])[:, 2]
        tops.append(heights.max())
        bottoms.append(heights.min())
    return float(max(tops) - min(bottoms))


def model_lengths(model):
    """The model's own segment lengths at its zero pose ({segment side: metres}) and its standing height."""
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    found = {"height": standing_height(model)}
    for side in SIDES:
        for segment, (start, end) in LIMBS.items():
            found[f"{segment} {side}"] = float(np.linalg.norm(
                data.xpos[body_id(model, f"{end}_{side}")] - data.xpos[body_id(model, f"{start}_{side}")]))
    return found


def scales_of(model, lengths):
    """Each body's scale ({body name: scale}): the person's segment length over the model's for a limb's bodies, the
    person's standing height over the model's for every other; a body not starting a segment takes its parent's."""
    own = model_lengths(model)
    starts = {f"{start}_{side}": f"{segment} {side}" for side in SIDES for segment, (start, _) in LIMBS.items()}
    found = {}
    for body in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body)
        parent = model.body_parentid[body]
        if name in starts:
            found[name] = lengths[starts[name]] / own[starts[name]]
        elif parent > 0:
            found[name] = found[mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, parent)]
        else:
            found[name] = lengths["height"] / own["height"]
    return found


def sized(spec, model, scales, kg, wrappers):
    """The spec sized body by body (see the module's docstring), its mass brought to `kg` with `wrappers` wrapper
    bodies' mass left for them."""
    mujoco.mj_forward(model, mujoco.MjData(model))
    grown = sum(model.body_mass[body_id(model, body.name)] * scales[body.name] ** 3 for body in spec.bodies[1:])
    share = (kg - wrappers * WRAPPER_KG) / grown
    meshes = {mesh.name: mesh for mesh in spec.meshes}
    for body in spec.bodies[1:]:
        scale = scales[body.name]
        above = scales.get(body.parent.name, scale) if body.parent.name != "world" else 1.0
        body.pos = np.asarray(body.pos) * above
        index = body_id(model, body.name)
        mass = model.body_mass[index] * scale ** 3 * share
        body.explicitinertial = True
        body.ipos = model.body_ipos[index] * scale
        body.iquat = model.body_iquat[index]
        body.inertia = model.body_inertia[index] * (mass / max(model.body_mass[index], 1e-12)) * scale ** 2
        body.fullinertia = [float("nan")] * 6
        body.mass = mass
        for geom in body.geoms:
            geom.pos = np.asarray(geom.pos) * scale
            geom.size = np.asarray(geom.size) * scale
            if geom.type == mujoco.mjtGeom.mjGEOM_MESH:
                meshes[geom.meshname].scale = np.asarray(meshes[geom.meshname].scale) * scale
        for site in body.sites:
            site.pos = np.asarray(site.pos) * scale
            site.size = np.asarray(site.size) * scale
        for joint in body.joints:
            joint.pos = np.asarray(joint.pos) * scale
            if joint.type == mujoco.mjtJoint.mjJNT_SLIDE:
                joint.range = np.asarray(joint.range) * above
    slides = {body.name: scales.get(body.parent.name, 1.0) for body in spec.bodies[1:]}
    joints = {joint.name: joint for joint in spec.joints}
    for equality in spec.equalities:
        joint = joints.get(equality.name1)
        if joint is not None and joint.type == mujoco.mjtJoint.mjJNT_SLIDE:
            data = np.asarray(equality.data)
            data[:5] *= slides[joint.parent.name]
            equality.data = data


def path_lengths(model):
    """Each actuator's path length at the zero pose (metres)."""
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return data.actuator_length.copy()


def renamed(xml):
    """Names MuJoCo and Newton both read: '-' and spaces become '_' (Newton cleans tendon site names on one side
    only, #60)."""
    return re.sub(r'\b(' + "|".join(NAMED) + r')="([^"]*)"',
                  lambda found: f'{found.group(1)}="{found.group(2).replace("-", "_").replace(" ", "_")}"', xml)


def full_muscles(xml, model):
    """Every <general> actuator with its compiled gain, bias and dynamics parameters written in full (a partial gainprm
    loses its class defaults in Newton, #60)."""
    def full(found):
        tag = found.group(0)
        name = re.search(r' name="([^"]*)"', tag)
        actuator = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name.group(1)) if name else -1
        if actuator < 0:
            return tag
        for field in ("gainprm", "biasprm", "dynprm"):
            values = " ".join(f"{value:.9g}" for value in getattr(model, "actuator_" + field)[actuator])
            tag = re.sub(f'\\s{field}="[^"]*"', "", tag).replace("<general ", f'<general {field}="{values}" ', 1)
        return tag
    return re.sub(r"<general [^>]*>", full, xml)


def multi_joint_bodies(spec):
    """How many wrapper bodies the split adds: one for each joint past a body's first."""
    return sum(max(0, len(body.joints) - 1) for body in spec.bodies[1:])


def split(xml):
    """Every body with several joints split: its joints but the last move, in order, into new wrapper bodies at its
    frame (the same motion as MuJoCo's in-body joint order), each WRAPPER_KG; Newton builds an equality only on a
    joint that is its body's own (#60)."""
    root = ElementTree.fromstring(xml)

    def visit(parent):
        for body in [child for child in parent if child.tag == "body"]:
            visit(body)
            joints = [child for child in body if child.tag == "joint"]
            if len(joints) < 2:
                continue
            at = list(parent).index(body)
            parent.remove(body)
            holder = parent
            for number, joint in enumerate(joints[:-1]):
                wrapper = ElementTree.Element("body", {"name": f"{body.get('name')}__j{number}"})
                if number == 0:
                    for key in ("pos", "quat", "euler", "axisangle", "xyaxes", "zaxis"):
                        if body.get(key) is not None:
                            wrapper.set(key, body.attrib.pop(key))
                if body.get("childclass"):
                    wrapper.set("childclass", body.get("childclass"))
                ElementTree.SubElement(wrapper, "inertial", {"pos": "0 0 0", "mass": str(WRAPPER_KG),
                                                             "diaginertia": WRAPPER_INERTIA})
                body.remove(joint)
                wrapper.append(joint)
                holder.insert(at, wrapper)
                holder, at = wrapper, len(wrapper)
            holder.append(body)

    visit(root.find("worldbody"))
    return ElementTree.tostring(root, encoding="unicode")


def person_file(folder, lengths, kg, path):
    """One person's MyoFullBody, written at `path`, and its record: each body's scale and mass, its muscles' length
    scale, its total mass."""
    source = f"{folder}/{SOURCE}"
    model = source_model(folder)
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


def kept_bodies():
    """The bodies named in a scale record: those that start a segment, and the pelvis and torso."""
    return {f"{start}_{side}" for side in SIDES for start, _ in LIMBS.values()} | {"pelvis", "torso"}
