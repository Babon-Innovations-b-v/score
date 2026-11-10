"""body-peel and place-peel: the film's peels (CONTEXT.md "layer peel", "place peel"), place nodes, paid (their
frames on rented cards through tools/cloud/blender_cloud.py inside the runner's clearance, drawn by
blender/body_peel.py from the jobs peel.py writes); the environment film cuts them (final.py).

    a locked film script's body-peel or place-peel   its `shows` {"place"}, its `seconds`, and for a body peel
                                                     optionally "close": the close-up following one walker

A place no locked script peels has no node (`applies_body`, `applies_place`), nor has a layer peel of a place whose
cast is a crowd alone (no sim body to peel); the row's key is the locked scripts
that peel the place (`script <name>`), so a lock moves only those places' peels.

    body-peel   reads cast, sim-body, people-clips-made (the clips rig), scene-clips (a climber's clip and the
                close-up's walker, optional), each person's look's people-dress (its dressed body, optional: a person
                whose dressed body is not taken refuses the row by name) and people-body (its build, optional, as
                sim-body reads it), and the place's finished stage (neighbours, else assembly) for the ground its sim
                bodies stood on (peel.ground_of: the solids the sim body record names, as that stage holds them).
                make   per shot the script asks (`wide`, and `close` where a segment names it), the longest segment's
                       seconds: peel.job_of (every person clothed, bare mesh, sim body, the push arrows), its frames
                       dealt over the cards the forecast sizes (peel.sliced), rendered once, joined by the wipes here
    place-peel  reads the place's finished stage (neighbours, else assembly, once complete passes or fails only on its
                accepted gaps, as demo-film), and its physics-layer where the place has one.
                make   one standing shot (`wide`) on the scene record's first camera, the longest segment's seconds:
                       peel.place_job (finished, bare clay, physics bodies), dealt, rendered and joined the same way
    out    <shot>/peel.mp4 (1280x720 at peel.RATE, silent: the environment film lays the script's bed under it) and
           peel.json (each shot's seconds, frames, passes, the walker it follows; the people, the ground's solids; the
           forecast it was made within)
    gate   peel    each shot: film_checks.video_checks at its planned size and seconds within LENGTH_SLACK and no black
                   stretch; a peel has no sound of its own, and a still stretch is none of its faults (a place peel
                   stands still by plan, a seated cast barely moves)

The forecast is from measured units: a peel frame is one render a pass, each priced as a measured demo film frame on
the same card class (demo.FRAME_MINUTES, demo_film.LIKELY_EUROS over its frames), high at FOG_FRAME_MINUTES for a
pass that draws a stage the scan finds fog, a volume or glass in (a place peel's finished and bare passes), else
FRAME_SPREAD times the likely; the runner clears the row at its high (graph.Stage.forecast) and the make refuses a
forecast past what it was cleared at, before anything is rented. Each card job's deadline is its frames at that high.
A job that dies or passes it is a gap, never run again inside the batch; a job made before at the same content is
kept (tools/cloud/kept.py: its outputs lie inside the make's folder).

Everything shown is the place's own rows' outputs: the dressed bodies, the clips rig at each build, the sim body
layer and record, the finished stage and its physics; the drawing's own colours (clay, edges, the push token) are the
renderer's diagram look (blender/body_peel.py), drawn over the place's ground, never a finish of the place.
"""
import json
import pathlib
import shutil
import subprocess

import numpy as np

from score import checks, contracts
from score.stages import demo_film
from score.stages.demo_film import final, lettering

REPO = pathlib.Path(__file__).resolve().parents[3]
BLENDER_SCRIPT = "score/stages/demo_film/blender/body_peel.py"
TOOLS = (BLENDER_SCRIPT, "tools/review/demo.py", "tools/review/film_checks.py", "tools/usd/colliders.py")
SAMPLES = 64  # peel.py's own
WIDE, CLOSE = "wide", "close"
SHOT_FILE, RECORD = "peel.mp4", "peel.json"
LENGTH_SLACK = 0.5
CARD = "L4-1-24G"  # the machine type demo_film.CLASSES (gpu-24gb) rents, as the saved bill prices it


def peeled(cut):
    """The places the locked scripts peel with `cut` (final.PEEL or final.PLACE_PEEL), sorted."""
    return sorted({(segment.get("shows") or {}).get("place") for script in final.scripts().values()
                   for segment in script.get("segments", []) if segment.get("cut") == cut} - {None})


def applies_body(place):
    """A place a locked script layer peels whose cast gives sim bodies: a crowd alone has none (final.crowd_only),
    so its layer peel is no node, never a paid node that cannot draw; the environment film names that script's fault
    (final.plan_faults: a place peel shows a crowd)."""
    return place in peeled(final.PEEL) and not final.crowd_only(place)


def applies_place(place):
    return place in peeled(final.PLACE_PEEL)


def peels_of(script, place, cut):
    """The script's `cut` segments showing `place`."""
    return [segment for segment in script.get("segments", [])
            if segment.get("cut") == cut and (segment.get("shows") or {}).get("place") == place]


def script_files(place, cut):
    """The locked scripts that peel the place with `cut`, keyed `script <name>`: a lock or its change moves them."""
    return {f"script {name}": "{dashboard}/" + f"{final.LOCKED}/{name}.json"
            for name, script in final.scripts().items() if peels_of(script, place, cut)}


def tool_files():
    """The renderer and the tools the make and gate read, and the film's colour tokens (the push arrows')."""
    return {**{f"tool {path}": "{repo}/" + path for path in TOOLS}, **lettering.FILES}


def body_files(place):
    return {**script_files(place, final.PEEL), **tool_files()}


def place_files(place):
    return {**script_files(place, final.PLACE_PEEL), **tool_files()}


def shots_of(inputs, place, cut):
    """{shot: seconds} the locked scripts among the node's inputs ask of the place's `cut`: `wide`, and for a body
    peel `close` where a segment names it, each its longest segment's seconds; refused with none."""
    shots = {}
    for script in final.named_scripts(inputs).values():
        for segment in peels_of(script, place, cut):
            shot = CLOSE if cut == final.PEEL and segment.get("close") else WIDE
            shots[shot] = max(shots.get(shot, 0.0), float(segment["seconds"]))
    if not shots:
        raise ValueError(f"no locked script among the inputs shows a {cut} of {place}")
    return dict(sorted(shots.items(), key=lambda item: item[0] != WIDE))


def forecast(shots, slow_passes, slow=None):
    """The peel's free forecast: its film frames (every shot's seconds at peel.RATE), the jobs they are dealt over
    (capacity.machines_for on the renders' likely minutes), each frame's likely and high card minutes (a render a pass:
    demo.FRAME_MINUTES each, high FOG_FRAME_MINUTES for a pass in `slow_passes` that is slow, else FRAME_SPREAD times
    the likely), the card minutes and the euros likely and high (a render priced as a measured demo film frame,
    demo_film.LIKELY_EUROS over its frames; the high never under the cards' own time at the saved bill's price, every
    job's set-up and lead and its frames at the high, as blender_cloud.py prices the call: dealt over many cards, a
    peel's set-up outweighs what a film frame's measure holds), and what the stage scan found (`slow`,
    demo_film.slow_parts' counts)."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    import sys
    demo, _ = demo_film.film_tools()
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import blender_cloud
    import capacity
    frames = sum(round(seconds * peel.RATE) for seconds in shots.values())
    likely = demo.FRAME_MINUTES
    high = sum(demo_film.FOG_FRAME_MINUTES if slowed else likely * demo_film.FRAME_SPREAD for slowed in slow_passes)
    renders = frames * len(slow_passes)
    per_render = demo_film.LIKELY_EUROS / round(demo_film.SHOTS * demo_film.SECONDS * demo.RATE)
    jobs = capacity.machines_for(renders, likely, blender_cloud.SETUP_MINUTES)
    card_high = jobs * (blender_cloud.SETUP_MINUTES + demo_film.JOB_LEAD_MINUTES) + frames * high
    return {"frames": frames, "renders": renders, "jobs": jobs,
            "frame_minutes": likely * len(slow_passes), "high_frame_minutes": high,
            "card_minutes": round(renders * likely), "high_card_minutes": round(frames * high),
            "euros": round(per_render * renders, 2),
            "high_euros": round(max(per_render * frames * high / likely, card_high * card_euros_a_minute()), 2),
            "slow": slow or {}}


def card_euros_a_minute():
    """The CLASSES card's euros a minute, the saved bill's (tools/costs/per_unit.hourly, the lowest zone)."""
    import sys
    sys.path.insert(0, str(REPO / "tools/costs"))
    import per_unit
    return per_unit.hourly(CARD) / 60.0


def body_forecast_of(inputs):
    """A body peel's forecast from the node's inputs: its shots, three passes drawn over the scene's ground only."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    place = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())["place"]
    return forecast(shots_of(inputs, place, final.PEEL), [False] * len(peel.PASSES))


def place_forecast_of(inputs):
    """A place peel's forecast from the node's inputs: its finished and bare passes draw the finished stage (slow
    where its scan finds fog, a volume or glass), its physics pass the bodies alone."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    stage_folder = demo_film.final_stage(inputs)
    place = demo_film.place_of(stage_folder)
    slow = demo_film.slow_parts(peel.stage_root(stage_folder))
    slowed = any(slow.values())
    return forecast(shots_of(inputs, place, final.PLACE_PEEL), [slowed, slowed, False],
                    {kind: len(paths) for kind, paths in slow.items()})


def body_forecast(inputs):
    """What a body peel's clearance reserves (graph.Stage.forecast): its forecast's high."""
    return demo_film.cleared_forecast([body_forecast_of(inputs)])


def place_forecast(inputs):
    """What a place peel's clearance reserves (graph.Stage.forecast): its forecast's high."""
    return demo_film.cleared_forecast([place_forecast_of(inputs)])


def within_clearance(node, planned):
    """The forecast said in the make's log and refused (Blocked) past what its run was cleared at."""
    print(f"{node}: {demo_film.forecast_line(planned)}", flush=True)
    demo_film.refuse_over_clearance(node, planned, demo_film.cleared_euros())


def people_of(inputs):
    """person_of(single, body) for peel.job_of: a cast person's rig at its own build as the sim body ran it
    (sim_body.person_rig; a climber's scene-made clip along its route, sim_body.route_clip), its look's dressed
    body (people-dress, refused by name when not taken) and the clip its sim body played."""
    from score.stages import sim_body
    from score.stages.cast import layer
    clips_rig = dict(np.load(pathlib.Path(inputs[sim_body.CLIPS_ROW]) / "rig.npz"))
    scene = sim_body.scene_clips_of(inputs)
    builds = {}

    def person_of(single, body):
        row = sim_body.body_row(single)
        if row not in builds:
            built = dict(np.load(pathlib.Path(inputs[row]) / "rig.npz")) if row in inputs else None
            builds[row] = (sim_body.person_rig(clips_rig, built)[0], built)
        rig, built = builds[row]
        clip = body.get("played", body["clip"])
        if clip != body["clip"]:
            if single["name"] not in scene:
                raise ValueError(f"{single['name']}: its sim body played {clip}, a scene-made clip not taken here")
            plan, scene_rig = scene[single["name"]]
            rig = dict(rig, **{f"clip_{clip}": sim_body.route_clip(clips_rig, built, scene_rig, plan)})
        dress = layer.body_row(single.get("look"), single.get("surface"), single.get("variant", 0))
        if dress not in inputs:
            raise ValueError(f"{single['name']}: no accepted dressed body ({dress}) to clothe it")
        return rig, pathlib.Path(inputs[dress]) / "body.glb", clip
    return person_of


def walker(inputs, cast):
    """The walker the close-up follows (peel.close_walker, by scene-clips' record where it is taken)."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    from score.stages import sim_body
    clips = pathlib.Path(inputs[sim_body.SCENE_CLIPS_ROW]) / sim_body.SCENE_CLIPS \
        if sim_body.SCENE_CLIPS_ROW in inputs else None
    return peel.close_walker(cast, json.loads(clips.read_text()) if clips else None)


def cloud_jobs(jobs, planned, sent):
    """Each shot's Blender job ({shot: job.json}) dealt over its share of the forecast's cards (peel.sliced), as
    blender_cloud.py's job files beside it: the renderer, the slice, the job's folder and `sent` (the rows' outputs it
    reads) up, the slice's drawn folder back, its deadline its frames at the forecast's high."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    import sys
    sys.path.insert(0, str(REPO / "tools/cloud"))
    import blender_cloud
    lengths = {shot: len(json.loads(path.read_text())["source"]) for shot, path in jobs.items()}
    written = []
    for shot, path in jobs.items():
        parts = max(1, round(planned["jobs"] * lengths[shot] / sum(lengths.values())))
        for piece in peel.sliced(path, parts, path.parent.parent / "drawn"):
            share = json.loads(piece.read_text())
            minutes = round(demo_film.JOB_LEAD_MINUTES + planned["high_frame_minutes"] * (share["frames"][1] -
                                                                                         share["frames"][0]))
            job = blender_cloud.job_of(REPO / BLENDER_SCRIPT, [piece], [path.parent, *sent], [share["out"]], minutes)
            (path.parent.parent / f"cloud-{piece.stem}.json").write_text(json.dumps(job, indent=1))
            written.append(path.parent.parent / f"cloud-{piece.stem}.json")
    return written


def render(cloud, node, out):
    """The jobs on rented cards in one call (the runner's clearance names them); the log kept in the output."""
    from score.adapters import engines
    runner = engines.machine_runner()
    done = subprocess.run([str(runner.cloud_python()), str(REPO / "tools/cloud/blender_cloud.py"), *map(str, cloud),
                           "--who", f"score runner, {node}", "--classes", demo_film.CLASSES], cwd=REPO,
                          capture_output=True, text=True)
    with (out / "frames.log").open("a") as log:
        log.write(done.stdout[-30000:] + "\n" + done.stderr[-30000:])
    if done.returncode:
        raise RuntimeError(f"blender_cloud.py failed: {done.stderr[-2000:]}")


def encoded(frames, out):
    """The joined frames (frames/<frame>.png) as a silent film at peel.RATE."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    demo, _ = demo_film.film_tools()
    out.parent.mkdir(parents=True, exist_ok=True)
    demo.ffmpeg("-framerate", str(peel.RATE), "-i", frames / "%04d.png", *demo.encode(out))


def finished(jobs, passes, out):
    """Each shot's passes joined by their wipes (peel.joined, from every slice's drawn folder) into <shot>/peel.mp4:
    {shot: {seconds, frames, passes, size, follows}}."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    shots = {}
    for shot, path in jobs.items():
        job = json.loads(path.read_text())
        count = len(job["source"])
        drawn = sorted((path.parent.parent / "drawn").iterdir())
        encoded(peel.joined(path.parent.parent, count, passes, drawn), out / shot / SHOT_FILE)
        shots[shot] = {"seconds": round(count / peel.RATE, 3), "frames": count, "passes": list(passes),
                       "size": job["size"],
                       **({"follows": job["people"][0]["name"]} if shot == CLOSE else {})}
    return shots


def make_body(inputs, out, seed, params):
    """The place's layer peels, a folder a shot (module docstring)."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    place, node = cast["place"], f"body-peel@{cast['place']}"
    shots = shots_of(inputs, place, final.PEEL)
    planned = body_forecast_of(inputs)
    within_clearance(node, planned)
    sim = pathlib.Path(inputs["sim-body"])
    record = json.loads((sim / "sim_bodies.json").read_text())
    ground = peel.ground_of(demo_film.final_stage(inputs), record)
    person_of, work, jobs, glbs = people_of(inputs), pathlib.Path(out) / ".work", {}, set()
    for shot, seconds in shots.items():
        folder = work / shot / "job"
        folder.mkdir(parents=True)
        close = walker(inputs, cast) if shot == CLOSE else None
        jobs[shot] = peel.job_of(folder, cast, sim, person_of, seconds, demo_film.SIZE, SAMPLES, close, ground)
        glbs |= {person["glb"] for person in json.loads(jobs[shot].read_text())["people"]}
    render(cloud_jobs(jobs, planned, [sim, *sorted(glbs)]), node, pathlib.Path(out))
    made = finished(jobs, peel.PASSES, pathlib.Path(out))
    (pathlib.Path(out) / RECORD).write_text(json.dumps({
        "place": place, "cut": final.PEEL, "shots": made, "people": sorted(record["bodies"]),
        "ground": sorted({solid for body in record["bodies"].values() for solid in body["ground"]["solids"]}),
        "forecast": planned}, indent=1))
    shutil.rmtree(work)


def make_place(inputs, out, seed, params):
    """The place's place peel, in folder `wide` (module docstring)."""
    from score.stages.demo_film import peel  # pxr and trimesh, only when a peel is made
    stage_folder = demo_film.final_stage(inputs)
    place = demo_film.place_of(stage_folder)
    node = f"place-peel@{place}"
    seconds = shots_of(inputs, place, final.PLACE_PEEL)[WIDE]
    planned = place_forecast_of(inputs)
    within_clearance(node, planned)
    physics = inputs.get("physics-layer")
    folder = pathlib.Path(out) / ".work" / WIDE / "job"
    folder.mkdir(parents=True)
    jobs = {WIDE: peel.place_job(folder, stage_folder, physics, seconds, demo_film.SIZE, SAMPLES)}
    render(cloud_jobs(jobs, planned, [stage_folder, *([physics] if physics else [])]), node, pathlib.Path(out))
    made = finished(jobs, peel.PLACE_PASSES, pathlib.Path(out))
    unshaped = json.loads(jobs[WIDE].read_text())["unshaped"]
    (pathlib.Path(out) / RECORD).write_text(json.dumps({
        "place": place, "cut": final.PLACE_PEEL, "shots": made, "stage": f"{place}/{place}.usda",
        "physics": "physics-layer" if physics else "the finished stage's own colliders", "unshaped": unshaped,
        "forecast": planned}, indent=1))
    shutil.rmtree(pathlib.Path(out) / ".work")


def output_faults(folder):
    """A peel's missing files: its record and every shot's film it names."""
    record = pathlib.Path(folder) / RECORD
    if not record.exists():
        return [f"no {RECORD}"]
    return [f"no {shot}/{SHOT_FILE}" for shot in json.loads(record.read_text())["shots"]
            if not (pathlib.Path(folder) / shot / SHOT_FILE).exists()]


BODY_CONTRACT = contracts.Contract("body-peel", 1, output_faults, {"time": "second"})
PLACE_CONTRACT = contracts.Contract("place-peel", 1, output_faults, {"time": "second"})


def shot_faults(video, shot):
    """One shot's faults: video_checks at its planned size and seconds and no black stretch; a peel carries no sound
    of its own, and a still stretch is no fault (a place peel stands still by plan, a seated cast barely moves)."""
    _, film_checks = demo_film.film_tools()
    found = film_checks.video_checks(video, shot["seconds"] - LENGTH_SLACK, shot["seconds"] + LENGTH_SLACK, 0.0,
                                     tuple(shot["size"]))
    return [fault for fault in found["failures"]
            if fault != "no sound track" and not fault.startswith(("silent", "frozen "))]


def judge(output, inputs, evidence):
    """The `peel` verdict over the output's shots."""
    record = json.loads((pathlib.Path(output) / RECORD).read_text())
    faults = [f"{name}: {fault}" for name, shot in record["shots"].items()
              for fault in shot_faults(pathlib.Path(output) / name / SHOT_FILE, shot)]
    return checks.Verdict("peel", checks.FAIL if faults else checks.PASS, "; ".join(faults[:3]) if faults else
                          "; ".join(f"{name} {shot['seconds']} s at {shot['size'][0]}x{shot['size'][1]}"
                                    for name, shot in record["shots"].items()),
                          {"shots": len(record["shots"]), "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("peel", judge),)
