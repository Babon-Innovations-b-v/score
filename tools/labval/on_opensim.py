"""LabValidation's reference joint moments made again with OpenSim from the lab's own files, run in an OpenSim
environment (the `opensim` module of OpenSim 4.x, or the pyopensim wheels of 4.5; never SCORE's own environment): the
lab's scaled model (OpenSimData/Mocap/Model/*_scaled.osim), its IK (ik/<trial>.mot), its force plates
(forces/<trial>.mot) and its ID setup (OpenSimData/Mocap/ID/<trial>_setup_id.xml: the time range and the cutoff of
the coordinates' low pass; its external loads file names which body each plate pushes).

- Inverse dynamics: OpenSim's InverseDynamicsTool with the lab's own settings (muscles excluded), so its generalized
  forces are the lab's; `reproduced` holds them against the dataset's own OpenSimData/Mocap/ID/<trial>.sto.
- The knee adduction moment, OpenCap's way (opencap-processing, OpenSimPipeline/JointReaction/computeJointLoading.py,
  `computeKAM`): every force but the plates removed, a coordinate actuator on every coordinate driven by the ID's
  generalized force (set each frame with Model.setControls), the knee's reaction on the tibia in the tibia's frame,
  KAM_r = -mx of walker_knee_r_on_tibia_r_in_tibia_r, KAM_l = +mx of the left's. The reaction is the call OpenSim's
  JointReaction analysis makes (Joint.calcReactionOnChildExpressedInGround, at the joint's child frame), turned into
  the tibia body's frame: the analysis itself recomputes the actuators' controls, and computeKAM's PrescribedController
  per actuator drove each actuator with its neighbour's function in OpenSim 4.5 (2026-11-07: the walking KAM came out
  a flat 16 N m through stance and swing). The coordinates are the IK low-passed at the ID setup's cutoff
  (4th-order Butterworth, zero lag), their speeds by finite difference as computeKAM takes them; the accelerations the
  actuators give match the coordinates' own to under 1 rad/s^2 on the hips, knees and lumbar (subject2 walking1).

    python on_opensim.py <subject folder> <trial> <out.npz> [<lab ID .sto>]

writes out.npz: time, the ID's column names and values (N m, N), kam_r and kam_l (N m, computeKAM's), external_kam_r
and external_kam_l (N m: `external_moment`, the plates' moment about the model's knee, the definition the sim body's
own KAM can be held to: MyoFullBody's knee has no adduction coordinate and no joint reaction of OpenSim's), and when the lab's ID .sto is
given, `reproduced`: the largest absolute difference (N m) of each shared column on the shared frames."""
import pathlib
import sys
import tempfile
import xml.etree.ElementTree as ElementTree

import numpy as np
from scipy import signal

try:
    import opensim
    Model, ID = opensim.Model, opensim.InverseDynamicsTool
except ImportError:  # the pyopensim wheels name their parts
    import pyopensim as opensim
    from pyopensim import simulation, tools
    opensim.Model, opensim.Storage = simulation.Model, opensim.common.Storage
    Model, ID = simulation.Model, tools.InverseDynamicsTool


def the_file(folder, pattern):
    """The one file matching `pattern` under `folder`; several or none raises."""
    found = sorted(pathlib.Path(folder).glob(pattern))
    if len(found) != 1:
        raise FileNotFoundError(f"{folder}: {len(found)} files match {pattern}, one expected")
    return found[0]


def setup_of(folder, trial):
    """(time range (start, end) s, the coordinates' cutoff Hz, the external loads' ExternalForce elements) of the
    lab's ID setup for `trial`."""
    setup = ElementTree.parse(the_file(folder, f"**/ID/{trial}_setup_id.xml")).getroot()
    start, end = (float(value) for value in setup.find(".//time_range").text.split())
    cutoff = float(setup.find(".//lowpass_cutoff_frequency_for_coordinates").text)
    loads = ElementTree.parse(the_file(folder, f"**/ID/{trial}_setup_externalLoads.xml")).getroot()
    return (start, end), cutoff, loads


def loads_file(loads, forces, folder):
    """The lab's external loads setup with its data file pointed at `forces` (the lab's own points at its PC)."""
    loads.find(".//datafile").text = str(forces)
    path = pathlib.Path(folder) / "external_loads.xml"
    ElementTree.ElementTree(loads).write(path)
    return path


def storage_columns(path):
    """(times, {column: values}) of an OpenSim storage file."""
    lines = pathlib.Path(path).read_text().splitlines()
    end = next(row for row, line in enumerate(lines) if line.strip().lower() == "endheader")
    labels = lines[end + 1].split()
    rows = np.array([[float(value) for value in line.split()] for line in lines[end + 2:] if line.strip()])
    return rows[:, 0], {label: rows[:, column] for column, label in enumerate(labels) if column}


def inverse_dynamics(model_path, coordinates, loads_path, time_range, cutoff, folder):
    """(times, {generalized force column: values}) of OpenSim's ID tool on the lab's settings, muscles excluded."""
    tool = ID()
    tool.setModelFileName(str(model_path))
    tool.setCoordinatesFileName(str(coordinates))
    tool.setExternalLoadsFileName(str(loads_path))
    tool.setLowpassCutoffFrequency(cutoff)
    tool.setStartTime(time_range[0])
    tool.setEndTime(time_range[1])
    excluded = opensim.common.ArrayStr() if hasattr(opensim, "common") else opensim.ArrayStr()
    excluded.append("Muscles")
    tool.setExcludedForces(excluded)
    tool.setResultsDir(str(folder))
    tool.setOutputGenForceFileName("id.sto")
    if not tool.run():
        raise RuntimeError(f"OpenSim's ID tool failed on {coordinates}")
    return storage_columns(pathlib.Path(folder) / "id.sto")


def low_passed(times, values, cutoff):
    """`values` (frames x n) low-passed at `cutoff` Hz, 4th-order Butterworth, zero lag."""
    rate = 1.0 / float(np.median(np.diff(times)))
    numerator, denominator = signal.butter(4, cutoff / (rate / 2.0))
    return signal.filtfilt(numerator, denominator, values, axis=0)


def actuated(model):
    """The model with every force removed and an unbounded coordinate actuator of optimal force 1 on every
    coordinate, its control set each frame (`Model.setControls`, as computeKAM sets them; a PrescribedController per
    actuator in OpenSim 4.5 drove each actuator with its neighbour's function): {coordinate: (coordinate, the
    actuator's index among the model's actuators)}."""
    forces = model.getForceSet()
    while forces.getSize():
        forces.remove(0)
    CoordinateActuator = opensim.CoordinateActuator if hasattr(opensim, "CoordinateActuator") \
        else opensim.actuators.CoordinateActuator
    held = {}
    coordinates = model.getCoordinateSet()
    for index in range(coordinates.getSize()):
        coordinate = coordinates.get(index)
        actuator = CoordinateActuator(coordinate.getName())
        actuator.setName(f"{coordinate.getName()}_actuator")
        actuator.set_min_control(-np.inf)
        actuator.set_max_control(np.inf)
        actuator.set_optimal_force(1)
        model.addForce(actuator)
        held[coordinate.getName()] = (coordinate, index)
    return held


def plates_on(model, loads, forces):
    """Each of the lab's ExternalForce elements added to the model, reading `forces`."""
    source = opensim.Storage(str(forces)) if hasattr(opensim, "Storage") else opensim.common.Storage(str(forces))
    ExternalForce = opensim.ExternalForce if hasattr(opensim, "ExternalForce") else opensim.simulation.ExternalForce
    for element in loads.iter("ExternalForce"):
        plate = ExternalForce()
        plate.setName(element.get("name"))
        plate.set_applied_to_body(element.find("applied_to_body").text.strip())
        plate.set_force_expressed_in_body(element.find("force_expressed_in_body").text.strip())
        plate.set_point_expressed_in_body(element.find("point_expressed_in_body").text.strip())
        plate.set_force_identifier(element.find("force_identifier").text.strip())
        plate.set_point_identifier(element.find("point_identifier").text.strip())
        plate.set_torque_identifier(element.find("torque_identifier").text.strip())
        plate.setDataSource(source)
        model.addForce(plate)
    return source


def knee_adduction(model_path, coordinates, loads, forces, id_times, id_columns, cutoff):
    """(KAM_r, KAM_l, external KAM_r, external KAM_l) N m on the ID's frames, computeKAM's way and the plates'
    (module docstring)."""
    model = Model(str(model_path))
    held = actuated(model)
    source = plates_on(model, loads, forces)
    state = model.initSystem()
    ik_times, ik_columns = storage_columns(coordinates)
    plate_rows = storage_columns(forces)
    external, reacted = {"r": [], "l": []}, {"r": [], "l": []}
    names = [name for name in held if name in ik_columns and "_beta" not in name]  # computeKAM leaves them at 0
    values = np.stack([ik_columns[name] for name in names], axis=1)
    radians = np.array([held[name][0].getMotionType() == 1 for name in names])
    values[:, radians] = np.radians(values[:, radians])
    values = low_passed(ik_times, values, cutoff)
    speeds = np.gradient(values, ik_times, axis=0)
    Vector = opensim.simbody.Vector if hasattr(opensim, "simbody") else opensim.Vector
    controls = Vector(len(held), 0.0)
    for step, time in enumerate(id_times):
        row = int(np.argmin(np.abs(ik_times - time)))
        state.setTime(float(time))
        for column, name in enumerate(names):
            coordinate = held[name][0]
            coordinate.setValue(state, float(values[row, column]), False)
            coordinate.setSpeedValue(state, float(speeds[row, column]))
        for name, (coordinate, index) in held.items():
            label = f"{name}{'_moment' if coordinate.getMotionType() == 1 else '_force'}"
            controls.set(index, float(id_columns[label][step]) if label in id_columns else 0.0)
        model.realizeVelocity(state)
        model.setControls(state, controls)
        model.realizeAcceleration(state)
        for side in external:
            external[side].append(external_moment(model, state, plate_rows, side, time))
            reacted[side].append(reaction_moment(model, state, side)[0])
    del source
    return (-np.array(reacted["r"]), np.array(reacted["l"]), np.array(external["r"]), np.array(external["l"]))


def tibia_turn(model, state, side):
    """The tibia body's frame in the lab (3 x 3, its columns x forward, y up, z to the right)."""
    turn = model.getBodySet().get(f"tibia_{side}").getTransformInGround(state).R()
    return np.array([[turn.get(row, column) for column in range(3)] for row in range(3)])


def reaction_moment(model, state, side):
    """The walker knee's reaction moment on the tibia (N m) at the joint's child frame, in the tibia body's frame."""
    reaction = model.getJointSet().get(f"walker_knee_{side}").calcReactionOnChildExpressedInGround(state)
    moment = np.array([reaction.get(0).get(axis) for axis in range(3)])
    return tibia_turn(model, state, side).T @ moment


def external_moment(model, state, plate_rows, side, time):
    """The external knee adduction moment (N m) of one side's plate about the knee: ((centre of pressure - the
    walker knee's child frame's origin) x force + the plate's free torque) about the tibia body's x (forward) axis
    (its child offset frame is turned off the body's: about it a swing moment came out -22 N m), positive
    adduction on both sides (the right's about x, the left's against it), the plate's row nearest `time`."""
    plate_times, plate_columns = plate_rows
    row = int(np.argmin(np.abs(plate_times - time)))
    prefix = side.upper()
    force, centre, torque = (np.array([plate_columns[f"{prefix}_ground_{kind}{axis}"][row] for axis in "xyz"])
                             for kind in ("force_v", "force_p", "torque_"))
    frame = model.getJointSet().get(f"walker_knee_{side}").getChildFrame()
    origin = frame.getPositionInGround(state)
    knee = np.array([origin.get(axis) for axis in range(3)])
    forward = tibia_turn(model, state, side)[:, 0]
    moment = float((np.cross(centre - knee, force) + torque) @ forward)
    return moment if side == "r" else -moment


def reproduced(times, columns, lab_id):
    """{column: largest absolute difference} of the remade ID against the lab's own .sto on their shared frames."""
    lab_times, lab_columns = storage_columns(lab_id)
    shared = np.isin(np.round(times, 4), np.round(lab_times, 4))
    lab_rows = np.isin(np.round(lab_times, 4), np.round(times, 4))
    return {name: float(np.max(np.abs(values[shared] - lab_columns[name][lab_rows])))
            for name, values in columns.items() if name in lab_columns and shared.any()}


def main(subject_folder, trial, out, lab_id=None):
    """Remake one trial's ID and KAM and write them to `out` (module docstring)."""
    folder = pathlib.Path(subject_folder)
    model_path = the_file(folder, "**/Mocap/Model/*_scaled.osim")
    coordinates, forces = the_file(folder, f"ik/{trial}.mot"), the_file(folder, f"forces/{trial}.mot")
    time_range, cutoff, loads = setup_of(folder, trial)
    with tempfile.TemporaryDirectory() as work:
        loads_path = loads_file(loads, forces, work)
        times, columns = inverse_dynamics(model_path, coordinates, loads_path, time_range, cutoff, work)
    kam_r, kam_l, external_r, external_l = knee_adduction(model_path, coordinates, loads, forces, times, columns,
                                                          cutoff)
    names = sorted(columns)
    found = {"time": times, "names": np.array(names), "values": np.stack([columns[name] for name in names], axis=1),
             "kam_r": kam_r, "kam_l": kam_l,
             "external_kam_r": external_r, "external_kam_l": external_l, "cutoff": cutoff}
    if lab_id:
        differences = reproduced(times, columns, lab_id)
        found["reproduced names"] = np.array(sorted(differences))
        found["reproduced"] = np.array([differences[name] for name in sorted(differences)])
    np.savez(out, **found)


if __name__ == "__main__":
    main(*sys.argv[1:])
