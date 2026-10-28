"""MyoFullBody sized to one person's SOMA body (#70: SOMA is the truth, its size included), `Size`:
- each bone group (`bone_groups.GROUPS`, trunk and pelvis included; a group with no body of its own, Neck2, is
  sized with the one before it on its chain: `stretches`) scaled evenly so its stretch, start joint to end joint at
  MyoFullBody's default pose, is SOMA's at its bind (`soma_lengths`: SOMA's joints, the hand to its mesh tip); all
  scales solved together (`Size.scales`), as a group's end may sit on another group's body;
- each group's mass, centre of mass and inertia's trace from SOMA's segment volumes (`volumes`: Dempster's densities),
  laid on the group's bodies (frames under FRAME_KG left out) in the model's own proportions, the centre carried
  into the group's frame by the calibration table and the inertias scaled together to the trace (`weigh`); the
  bodies of no group (the kneecaps, the abdominal wrapper) keep the model's share;
- what SOMA does not give marked as assumed with a plausible range (`assumed`).
A body takes its group's scale, a body of no group its parent's; a body's place in its parent scales with its
parent, but OWN_PLACED's with its own. Positions, geoms, sites, joint anchors, meshes and a
slide joint's coupling and range scale with it (`sized`); each muscle's path length at the zero pose is read for
OpenSim's muscle scaling (`path_lengths`). The landmark joint centres (`landmarks.soma_centres`) are the solver's
starting shape, not the sizing's: they stand 4 to 24 mm off SOMA's joints, and the sim body's joints are to sit on
SOMA's."""
import mujoco
import numpy as np

import volumes
from bone_groups import groups
from calibration import turn
from landmarks import myo_parts, soma_point
from model import TO_OWN, Couplings, default_pose

WRAPPER_KG = 0.001  # a split body's wrapper (MuJoCo's boundmass for MyoFullBody, which Newton does not apply)
# Bodies placed in their parent by their own scale: the torso, welded on lumbar1 with its origin 8.9 cm below
# lumbar1's (inside its own bone, the source model): by lumbar1's scale a longer lumbar stretch moved T12/L1 down.
OWN_PLACED = {"torso"}
SCALE_RANGE = (0.5, 2.0)  # a bone group's scale's bounds
# More SOMA bone lines a group's volume is given by, beyond its stretch: the hips' line for the pelvis.
MORE_LINES = {"Hips": (("LeftLeg", "RightLeg"),)}
# What SOMA does not give, as assumed, with a plausible range (`assumed` adds the bone shape measured on the person).
ASSUMED = {
    "muscle strength": {
        "value": "MyoFullBody's own peak isometric forces, not scaled with the person",
        "plausible": "0.25 to 1.7 times: specific tension reported from 15 to over 100 N/cm2 (Rajagopal et al. 2016, "
                     "doi:10.1109/TBME.2016.2586891, whose 60 N/cm2 the model's legs take)"},
    "joint ranges": {
        "value": "MyoFullBody's own ranges (MyoSuite; the legs as Rajagopal et al. 2016)",
        "plausible": "a person's own differ by sex and age from the textbook norms (Soucie et al. 2011, Haemophilia "
                     "17:500, 674 healthy people); no spread read per joint, so none is given"},
    "segment density": {
        "value": "Dempster 1955 as Winter 2009 Table 4.1 gives it, per bone group (volumes.DENSITY)",
        "plausible": f"{volumes.DENSITY_RANGE[0]} to {volumes.DENSITY_RANGE[1]} times it (Chandler et al. 1975)"}}


def stretches(table=None):
    """The sizing stretches ({group: ((SOMA start, end), (MyoFullBody start, end), bodies)}): each bone group with
    bodies, a body-less one after it on its chain merged into it."""
    table = table or groups()
    found = {group: (soma, myo, bodies) for group, (soma, myo, _, bodies) in table.items() if bodies}
    for group, ((start, end), (_, myo_end), _, bodies) in table.items():
        if not bodies:
            host = next(name for name, ((_, last), _, _) in found.items() if last == start)
            (first, _), (myo_first, _), held = found[host]
            found[host] = ((first, end), (myo_first, myo_end), held)
    return found


def soma_lengths(rig, table=None):
    """Each stretch's length on SOMA at its bind (metres)."""
    return {group: float(np.linalg.norm(soma_point(end, rig) - soma_point(start, rig)))
            for group, ((start, end), _, _) in stretches(table).items()}


def myo_point(model, data, name, scales):
    """A MyoFullBody centre in MuJoCo's frame, its body-local point scaled with its body."""
    found = np.zeros(3)
    for body, local, weight in myo_parts(name):
        index = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body)
        found += weight * (data.xpos[index] + data.xmat[index].reshape(3, 3) @ (np.asarray(local) * scales[body]))
    return found


def myo_lengths(model, scales, table=None):
    """Each stretch's length on the model at its default pose (metres)."""
    data = default_pose(model, Couplings(model))
    return {group: float(np.linalg.norm(myo_point(model, data, end, scales) - myo_point(model, data, start, scales)))
            for group, (_, (start, end), _) in stretches(table).items()}


def posed_lengths(model, scales, table=None):
    """`myo_lengths` of the model as `sized` would place it (a body's place by its parent's scale, OWN_PLACED's by
    its own, joint anchors by their body's, a slide joint's coupling by its body's parent's), the model left as it
    was."""
    kept = model.body_pos.copy(), model.jnt_pos.copy(), model.eq_data.copy()
    name = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body) for body in range(model.nbody)]
    above = np.array([1.0] + [scales.get(name[model.body_parentid[body]], 1.0) for body in range(1, model.nbody)])
    placed = np.array([1.0] + [scales[name[body]] if name[body] in OWN_PLACED else above[body]
                               for body in range(1, model.nbody)])
    model.body_pos[:] = kept[0] * placed[:, None]
    model.jnt_pos[:] = kept[1] * np.array([scales.get(name[model.jnt_bodyid[joint]], 1.0)
                                          for joint in range(model.njnt)])[:, None]
    for equality in range(model.neq):
        joint = model.eq_obj1id[equality]
        if model.eq_type[equality] == mujoco.mjtEq.mjEQ_JOINT and model.jnt_type[joint] == mujoco.mjtJoint.mjJNT_SLIDE:
            model.eq_data[equality, :5] = kept[2][equality, :5] * above[model.jnt_bodyid[joint]]
    try:
        return myo_lengths(model, scales, table)
    finally:
        model.body_pos[:], model.jnt_pos[:], model.eq_data[:] = kept


def body_scales(model, scales, table=None):
    """Each body's scale ({body name: scale}): its group's, a body of no group its parent's."""
    owner = {body: group for group, (_, _, bodies) in stretches(table).items() for body in bodies}
    found = {}
    for body in range(1, model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body)
        parent = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.body_parentid[body])
        found[name] = scales[owner[name]] if name in owner else found.get(parent, 1.0)
    return found


def _body_id(model, name):
    return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)


def sized(spec, model, scales, kg, wrappers):
    """The spec sized body by body (see the module's docstring), its mass brought to `kg` with `wrappers` wrapper
    bodies' mass left for them, in the model's own proportions."""
    mujoco.mj_forward(model, mujoco.MjData(model))
    grown = sum(model.body_mass[_body_id(model, body.name)] * scales[body.name] ** 3 for body in spec.bodies[1:])
    share = (kg - wrappers * WRAPPER_KG) / grown
    meshes = {mesh.name: mesh for mesh in spec.meshes}
    for body in spec.bodies[1:]:
        scale = scales[body.name]
        above = scales.get(body.parent.name, scale) if body.parent.name != "world" else 1.0
        body.pos = np.asarray(body.pos) * (scale if body.name in OWN_PLACED else above)
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


class Size:
    """One person's sizing from its SOMA rig ({"names", "bind", "points", "faces", "weights"}, its bind in its own
    frame): `scales` (each body's), `weigh` (the masses from SOMA's volumes), `record`."""

    def __init__(self, rig, table=None, turns=None):
        self.rig, self.table = rig, table or groups()
        self.lengths = soma_lengths(rig, self.table)
        self.turns = turns or {group: turn(group) for group in stretches(self.table)}
        cells = volumes.filled(rig["points"], rig["faces"])
        names = list(stretches(self.table))
        lines = [[(soma_point(start, rig), soma_point(end, rig)) for start, end in self._pieces(group)]
                 for group in names]
        self.found = volumes.measured(cells, volumes.shares(cells, lines), len(names))
        self.names = names
        self.moved = {}  # each group's centre of mass moved by `weigh` (cm)

    def _pieces(self, group):
        """The SOMA bone lines a group's volume is given by: its own stretch, a body-less group's after it on its
        chain, and MORE_LINES."""
        (start, end), _, _, _ = self.table[group]
        found = [(start, end)]
        for (later_start, later_end), _, _, bodies in self.table.values():
            if not bodies and later_start == found[-1][1]:
                found.append((later_start, later_end))
        return found + list(MORE_LINES.get(group, ()))

    def scales(self, source):
        """Each body's scale: the group scales whose stretches at the default pose are SOMA's lengths, one bounded
        least squares (scipy's `least_squares`, a scale within SCALE_RANGE) on the source model posed at them
        (`posed_lengths`), as a group's end may sit on another group's body."""
        from scipy.optimize import least_squares
        groups_found = list(self.lengths)
        wanted = np.array([self.lengths[group] for group in groups_found])
        own = myo_lengths(source, body_scales(source, dict.fromkeys(groups_found, 1.0), self.table), self.table)

        def misses(logs):
            scales = body_scales(source, dict(zip(groups_found, np.exp(logs))), self.table)
            found = posed_lengths(source, scales, self.table)
            return np.array([found[group] for group in groups_found]) - wanted
        start = np.log(np.clip(wanted / [own[group] for group in groups_found], *SCALE_RANGE))
        solved = least_squares(misses, start, bounds=(np.log(SCALE_RANGE[0]), np.log(SCALE_RANGE[1])), xtol=1e-10)
        return body_scales(source, dict(zip(groups_found, np.exp(solved.x))), self.table)

    def weigh(self, spec, grown, scales, kg):
        """Each group's bodies given its mass, centre of mass and inertia's trace from SOMA's volumes (`kg` the
        groups' share of the person's mass); returns {group: inertia scale} (the factor on the bodies' own
        inertias, its floor INERTIA_FLOOR)."""
        data = default_pose(grown, Couplings(grown))
        inertials = volumes.weighed(self.names, self.found, kg)
        bodies = {body.name: body for body in spec.bodies[1:]}
        factors = {}
        for group, ((start, _), (myo_start, _), held) in stretches(self.table).items():
            mass, centre, trace = inertials[group]
            held = [name for name in held if grown.body_mass[_body_id(grown, name)] >= FRAME_KG]
            index = [_body_id(grown, name) for name in held]
            masses = grown.body_mass[index] * mass / max(grown.body_mass[index].sum(), 1e-12)
            names = [str(name) for name in self.rig["names"]]
            segment = np.asarray(self.rig["bind"])[names.index(group), :3, :3]
            frame = _body_id(grown, self.table[group][2])
            offset = self.turns[group].T @ segment.T @ (centre - soma_point(start, self.rig))
            target = myo_point(grown, data, myo_start, scales) + data.xmat[frame].reshape(3, 3) @ offset
            shift = target - masses @ data.xipos[index] / mass
            self.moved[group] = round(float(np.linalg.norm(shift)) * 100, 2)
            spread = sum(2.0 * part * np.sum((data.xipos[body] + shift - target) ** 2)
                         for part, body in zip(masses, index))
            own = sum(float(grown.body_inertia[body].sum()) * part / max(grown.body_mass[body], 1e-12)
                      for part, body in zip(masses, index))
            factors[group] = max((trace - spread) / max(own, 1e-12), INERTIA_FLOOR)
            for name, part, body in zip(held, masses, index):
                bodies[name].mass = float(part)
                bodies[name].ipos = grown.body_ipos[body] + data.xmat[body].reshape(3, 3).T @ shift
                bodies[name].inertia = (grown.body_inertia[body] * part / max(grown.body_mass[body], 1e-12)
                                        * factors[group])
        return factors

    def record(self, model, scales):
        """The sized model's lengths against SOMA's ({group: [SOMA m, sized m]})."""
        found = myo_lengths(model, scales, self.table)
        return {group: [round(self.lengths[group], 4), round(found[group], 4)] for group in self.lengths}


# A body under this mass is a frame, not a bone (MyoFullBody's phantoms and attachments, 1 g, some with inertias of
# several kg m2): `weigh` leaves it as sized.
FRAME_KG = 0.01
INERTIA_FLOOR = 0.1  # the least factor on a group's own inertias (a group whose bodies' spread alone passes SOMA's)


def ungrouped_kg(model, table=None):
    """The mass of the model's bodies `weigh` leaves as sized (kg): those in no bone group (the kneecaps, the
    abdominal wrapper) and the frames (under FRAME_KG)."""
    held = {body for _, _, bodies in stretches(table).values() for body in bodies}
    return float(sum(model.body_mass[body] for body in range(1, model.nbody)
                     if mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body) not in held
                     or model.body_mass[body] < FRAME_KG))


def assumed(model, scales, rig):
    """ASSUMED with the bone shape: each group scaled evenly by its length, its widths measured against SOMA's (the
    hip joints and the shoulder joints apart, SOMA's over the sized model's)."""
    data = default_pose(model, Couplings(model))
    widths = {}
    for label, (soma_pair, myo_pair) in {"hips": (("LeftLeg", "RightLeg"), ("hip_l", "hip_r")),
                                         "shoulders": (("LeftArm", "RightArm"),
                                                       ("glenohumeral_l", "glenohumeral_r"))}.items():
        soma = np.linalg.norm(soma_point(soma_pair[0], rig) - soma_point(soma_pair[1], rig))
        myo = np.linalg.norm(myo_point(model, data, myo_pair[0], scales) - myo_point(model, data, myo_pair[1], scales))
        widths[label] = round(float(soma / myo), 3)
    return {**ASSUMED, "bone shape": {
        "value": "MyoFullBody's own bones, each bone group scaled evenly by its stretch's length",
        "plausible": f"widths {min(widths.values())} to {max(widths.values())} times the sized ones (SOMA's joints "
                     f"apart over the sized body's: {widths})"}}


def path_lengths(model):
    """Each actuator's path length at the zero pose (metres)."""
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return data.actuator_length.copy()


def kept_bodies(table=None):
    """The bodies named in a scale record: each stretch's frame body."""
    table = table or groups()
    return {table[group][2] for group in stretches(table)}
