"""MyoFullBody sized to one person (#64): the person's limb lengths from its rig's bind (`limb_lengths`), each body's
scale against the published model's own lengths and standing height (`scales_of`), the model's spec sized body by
body with its mass brought to the person's (`sized`), and each muscle's path length at the zero pose
(`path_lengths`, OpenSim's muscle scaling). A limb (thigh, shin, foot, upper arm, forearm) by the person's own SOMA
joint distance over the model's, every other body by the person's standing height over the model's (SOMA's hip and
shoulder widths carry no per-person signal); a body takes its parent's scale unless it starts a segment. Positions,
geoms, sites, joint anchors, meshes and a slide joint's coupling and range scale with it; each body's mass the
model's times its scale cubed, all brought to the person's total, its inertia with its mass and its scale squared."""
import mujoco
import numpy as np

# The segments a person's SOMA rig gives a length for, by the MyoFullBody body that starts each (each side), and the
# body its far end is: the model's own length is the distance between their origins at its zero pose.
LIMBS = {"thigh": ("femur", "tibia"), "shin": ("tibia", "talus"), "foot": ("talus", "toes"),
         "upper arm": ("humerus", "ulna"), "forearm": ("ulna", "lunate")}
SIDES = {"l": "Left", "r": "Right"}
WRAPPER_KG = 0.001  # a split body's wrapper (MuJoCo's boundmass for MyoFullBody, which Newton does not apply)


def limb_lengths(person):
    """The person's own limb lengths from its rig's bind (metres, LIMBS' segments)."""
    names = [str(name) for name in person["rig"]["names"]]
    bind = np.asarray(person["rig"]["bind"], dtype=float)
    ends = {"thigh": ("Leg", "Shin"), "shin": ("Shin", "Foot"), "foot": ("Foot", "ToeBase"),
            "upper arm": ("Arm", "ForeArm"), "forearm": ("ForeArm", "Hand")}
    return {f"{segment} {letter}": float(np.linalg.norm(bind[names.index(side + far), :3, 3]
                                                         - bind[names.index(side + near), :3, 3]))
            for segment, (near, far) in ends.items() for letter, side in SIDES.items()}


def _body_id(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def _standing_height(model):
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


def _model_lengths(model):
    """The model's own segment lengths at its zero pose ({segment side: metres}) and its standing height."""
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    found = {"height": _standing_height(model)}
    for side in SIDES:
        for segment, (start, end) in LIMBS.items():
            found[f"{segment} {side}"] = float(np.linalg.norm(
                data.xpos[_body_id(model, f"{end}_{side}")] - data.xpos[_body_id(model, f"{start}_{side}")]))
    return found


def scales_of(model, lengths):
    """Each body's scale ({body name: scale}): the person's segment length over the model's for a limb's bodies, the
    person's standing height over the model's for every other; a body not starting a segment takes its parent's."""
    own = _model_lengths(model)
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
    grown = sum(model.body_mass[_body_id(model, body.name)] * scales[body.name] ** 3 for body in spec.bodies[1:])
    share = (kg - wrappers * WRAPPER_KG) / grown
    meshes = {mesh.name: mesh for mesh in spec.meshes}
    for body in spec.bodies[1:]:
        scale = scales[body.name]
        above = scales.get(body.parent.name, scale) if body.parent.name != "world" else 1.0
        body.pos = np.asarray(body.pos) * above
        index = _body_id(model, body.name)
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


def kept_bodies():
    """The bodies named in a scale record: those that start a segment, and the pelvis and torso."""
    return {f"{start}_{side}" for side in SIDES for start, _ in LIMBS.values()} | {"pelvis", "torso"}
