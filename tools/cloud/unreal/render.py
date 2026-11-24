"""Unreal Engine 5.8 renders of one shot on one card of the Kubernetes cluster (SCORE_CLOUD=k8s; #215, #222): the
project the placer made (#217) goes up as the job's input, the score-unreal image (tools/cloud/images/unreal/: Epic's
official Linux image with the job runtime, in the project's private registry only) runs on_card.py there, and the
frames, the render-twice check and the cost of a frame come back.

    .venv/bin/python tools/cloud/unreal/render.py <project folder> --map /Game/Place/Street \
        --sequence /Game/Place/Film.Film --frames 96 --class gpu-48gb --out <folder> --who "<session>" [--dry-run]
    .venv/bin/python tools/cloud/unreal/render.py --package <scene package> --film-path <place>/film/path.json \
        --frames 1 --class gpu-48gb --out <folder> --who "<session>" [--dry-run]

<project folder> holds one .uproject and its Config/DefaultEngine.ini, which must target Vulkan SM6 alone with
hardware ray tracing and Lumen on (`project_refusal`; refused before anything is sent). With `--package` instead
(a scene package made with `package --film`, #221) the project is made here (`project_made`: our own .uproject and
the settings REQUIRED names) and the level is made on the card first: tools/unreal/scene/editor.py carries the
package's plan into a new level and its film path into a Level Sequence (plan.level_path, plan.sequence_path) before
the passes render it. One shot is one card model (L40S frames come out slightly darker than other cards', #216):
`--class` names one class.

The shader cache (Unreal's Derived Data Cache) is kept in the store by the runtime's kernel cache
(tools/cloud/runtime/kernels.py): the job names `kernel_cache` = `ddc_name` (engine version, RHI and the project's
shader settings), the runtime adds the card's compute capability and driver, restores the cache before the command
and uploads it after a run that grew it. A cold first start compiles every shader (15 to 113 min measured by
Higgsfield on fresh machines), so a run that starts warm is the cheap one.

Back in <out>: full/ (every frame), check/ (the first CHECK_FRAMES rendered again by a second editor process),
record.json (on_card's passes and timings), twice.json (the check: a fault where a tile's brightness differs between
the two renders, the dark rectangles Higgsfield saw in 4 of 7 final renders) and cost.json (what a frame cost).
Spending: as every cluster run, only inside a cleared run (SCORE_SPEND_TICKET, or the owner's override); the
submitter holds the run to the batch cap.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "k8s"))
sys.path.insert(0, str(REPO / "tools/unreal/scene"))

import _cost  # noqa: E402
import _twice  # noqa: E402
import plan as scene_plan  # noqa: E402

KIND = "unreal"  # capacity.py's job kind, the ledger's
IMAGE = "unreal"  # the images.json kind
ENGINE = "5.8.4"
RHI = "vulkan-sm6"
CLASSES = ("gpu-48gb", "gpu-24gb")  # L40S and L4: RT cores; an H100 has none
EDITOR = "/home/ue4/UnrealEngine/Engine/Binaries/Linux/UnrealEditor-Cmd"  # Epic's image's layout
USER = "ue4"  # Unreal refuses to run as root; Epic's image's user
UP = pathlib.PurePosixPath("/work/unreal")
CHECK_FRAMES = 8
# The minutes a job may run: a cold shader compile (113 min was the worst Higgsfield measured on a fresh machine), the
# three editor starts (config, full, check) and the frames at SECONDS_A_FRAME (about 9 s on an L40S at 64 samples,
# Higgsfield; an L4 is slower, so the allowance is twice that).
COLD_MINUTES = 120
START_MINUTES = 3
SECONDS_A_FRAME = 20
# Movie Render Queue's settings, Higgsfield's recipe (#216): no anti-aliasing method, 64 temporal samples summed a
# frame (motion blur comes from their spread over the camera's shutter), engine warm-up frames, texture streaming off,
# the top LOD, no tiling. Exposure and the 180-degree shutter belong to the level's camera and post-process volume.
RECIPE = {"width": 1920, "height": 1080, "spatial_samples": 1, "temporal_samples": 64, "warm_up_frames": 32,
          "texture_streaming": False, "cinematic_quality": True,
          "console_variables": {"r.ForceLOD": 0, "foliage.ForceLOD": 0, "r.Lumen.HardwareRayTracing": 1}}
# What the project's DefaultEngine.ini must hold for hardware ray tracing and Lumen on Linux (#216: Vulkan SM6 only).
LINUX = "/Script/LinuxTargetPlatform.LinuxTargetSettings"
RENDERER = "/Script/Engine.RendererSettings"
REQUIRED = {(LINUX, "+TargetedRHIs"): "SF_VULKAN_SM6", (RENDERER, "r.RayTracing"): "True",
            (RENDERER, "r.SkinCache.CompileShaders"): "True", (RENDERER, "r.Lumen.HardwareRayTracing"): "True",
            (RENDERER, "r.DynamicGlobalIlluminationMethod"): "1", (RENDERER, "r.ReflectionMethod"): "1"}
REFUSED = {(LINUX, "+TargetedRHIs"): "SF_VULKAN_SM5"}
SHADER_SECTIONS = (LINUX, RENDERER)
# A made project's own settings beside REQUIRED: no static lighting (every light movable, nothing to build; Lumen's).
MADE_SETTINGS = {(RENDERER, "r.AllowStaticLighting"): "False", (RENDERER, "r.GenerateMeshDistanceFields"): "True"}
# The engine plugins a made project turns on: the editor's Python, Movie Render Queue, the editor's asset scripting.
# on_card.py keeps those the image holds and records any it dropped.
PLUGINS = ("PythonScriptPlugin", "MovieRenderPipeline", "EditorScriptingUtilities")
SCENE_SCRIPT = "tools/unreal/scene/editor.py"


def ini_lines(text):
    """An Unreal ini's settings as {section: [(key, value), ...]}, in order, comments and blank lines left out (a key
    may repeat: Unreal's `+Key` adds to an array)."""
    sections, current = {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], [])
        elif "=" in line and current is not None:
            key, value = line.split("=", 1)
            current.append((key.strip(), value.strip()))
    return sections


def project_refusal(ini_text):
    """Why the project cannot render with hardware ray tracing on Linux (each missing or refused setting), or None."""
    sections = ini_lines(ini_text)
    faults = [f"[{section}] {key}={value} is missing" for (section, key), value in REQUIRED.items()
              if (key, value) not in sections.get(section, [])]
    faults += [f"[{section}] {key}={value} must go (SM6 alone)" for (section, key), value in REFUSED.items()
               if (key, value) in sections.get(section, [])]
    return "; ".join(faults) or None


def ddc_name(ini_text, engine=ENGINE, rhi=RHI):
    """The shader cache's name: the engine version, the RHI and a hash of the project's shader settings (its Linux
    target and renderer sections, in any order, comments aside). The runtime adds the card and its driver."""
    sections = ini_lines(ini_text)
    settings = sorted(f"[{section}]{key}={value}" for section in SHADER_SECTIONS
                      for key, value in sections.get(section, []))
    return f"unreal-{engine}-{rhi}-{hashlib.sha256(chr(10).join(settings).encode()).hexdigest()[:12]}"


def project_made(folder, name):
    """A content-only project at <folder>: <name>.uproject turning PLUGINS on and Config/DefaultEngine.ini holding
    REQUIRED and MADE_SETTINGS, section by section; the .uproject's path."""
    folder = pathlib.Path(folder)
    (folder / "Config").mkdir(parents=True, exist_ok=True)
    sections = {}
    for (section, key), value in {**REQUIRED, **MADE_SETTINGS}.items():
        sections.setdefault(section, []).append(f"{key}={value}")
    (folder / "Config/DefaultEngine.ini").write_text("".join(
        f"[{section}]\n" + "".join(line + "\n" for line in lines) + "\n" for section, lines in sections.items()))
    made = folder / f"{name}.uproject"
    made.write_text(json.dumps({"FileVersion": 3, "EngineAssociation": ENGINE.rsplit(".", 1)[0], "Category": "",
                                "Description": "SCORE's film render (made by tools/cloud/unreal/render.py)",
                                "Plugins": [{"Name": plugin, "Enabled": True} for plugin in PLUGINS]}, indent=1))
    return made


def uproject(folder):
    """The project folder's one .uproject."""
    found = sorted(pathlib.Path(folder).glob("*.uproject"))
    if len(found) != 1:
        raise SystemExit(f"{folder} holds {len(found)} .uproject files; one is needed")
    return found[0]


def scene_step(film_path):
    """What on_card.py's scene step reads (the package, its staging folder, the film path, the script up there)."""
    return {"script": SCENE_SCRIPT, "package": str(UP / "package"), "into": str(UP / "stage"),
            "path": str(UP / "path.json") if film_path else None}


def shot(project_file, level, sequence, frames, scene=None):
    """What on_card.py renders: the editor, the project up there, the level and sequence, the two passes (every frame
    and the first CHECK_FRAMES again, each its own config asset and folder), the recipe, and the scene step (the level
    made from a package on the card) when given."""
    out = UP / "out"
    return {"editor": EDITOR, "user": USER, "project": str(UP / "project" / project_file.name), "map": level,
            "sequence": sequence, "out": str(out), "recipe": RECIPE, "scene": scene,
            "passes": [{"name": "full", "config": "/Game/ScoreRender/Full", "start": 0, "end": frames,
                        "folder": str(out / "full")},
                       {"name": "check", "config": "/Game/ScoreRender/Check", "start": 0,
                        "end": min(CHECK_FRAMES, frames), "folder": str(out / "check")}]}


def job(project, frames, shot_file, out, package=None, film_path=None):
    """The cluster job (cluster_jobs.run's form) that renders the shot: on_card.py in the image, the project and
    shot.json up (and the scene package and film path the level is made from, when given), the out folder back, the
    shader cache named."""
    ini = (pathlib.Path(project) / "Config/DefaultEngine.ini").read_text()
    starts = 3 + bool(package)
    minutes = COLD_MINUTES + starts * START_MINUTES + (frames + min(CHECK_FRAMES, frames)) * SECONDS_A_FRAME / 60
    scene = [{"local": str(package), "path": str(UP / "package")}] if package else []
    scene += [{"local": str(film_path), "path": str(UP / "path.json")}] if package and film_path else []
    return {"command": ["/opt/score/venv/bin/python", "tools/cloud/unreal/on_card.py", str(UP / "shot.json")],
            "code": ["tools/cloud/unreal"] + (["tools/unreal/scene"] if package else []),
            "inputs": [{"local": str(project), "path": str(UP / "project")},
                       {"local": str(shot_file), "path": str(UP / "shot.json")}] + scene,
            "outputs": [{"path": str(UP / "out"), "local": str(out)}],
            "minutes": round(minutes), "cards": 1, "kernel_cache": ddc_name(ini), "attempt_limit": 1}


def ledger_rows(run_name):
    """The ledger's rows of the run (its nodes, booked by the submitter); none when it went through the box's queue."""
    import ledger
    return [row for row in ledger.entries() if row.get("batch") == run_name]


def list_price(card_class):
    """The class's cheapest offer's euros a minute."""
    import batch
    return min(offer.price for offer in batch.offers([card_class]))


def finish(out, run_name, card_class):
    """The render-twice check and the cost of a frame, from what came back, written beside the frames; the check."""
    out = pathlib.Path(out)
    record = json.loads((out / "record.json").read_text())
    twice = _twice.check(out / "full", out / "check", record["passes"]["check"]["frames"])
    (out / "twice.json").write_text(json.dumps(twice, indent=1))
    rows = ledger_rows(run_name)
    cost = _cost.frame_cost(record, rows, card_class, None if rows else list_price(card_class))
    (out / "cost.json").write_text(json.dumps(cost, indent=1))
    return twice


def scene_faults(out):
    """What the editor refused making the level on the card (record.json's scene step), none without one."""
    record = json.loads((pathlib.Path(out) / "record.json").read_text())
    return record["passes"].get("scene", {}).get("made", {}).get("faults", [])


def render(project, level, sequence, frames, card_class, out, who, dry_run=False, package=None, film_path=None):
    """Send the shot's job, bring its frames back and write the check and the cost; the run's name. With `package`
    (and no project) the project is made here and the level from the package on the card, its map and sequence
    plan.py's names for the package's place."""
    import cluster_jobs
    import provider

    if card_class not in CLASSES:
        raise SystemExit(f"{card_class} is not one of {', '.join(CLASSES)} (cards with ray-tracing cores)")
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="unreal-shot-"))
    try:
        if package:
            place = json.loads((pathlib.Path(package) / "scene.json").read_text())["place"]
            project = project or scratch / "project"
            if not list(pathlib.Path(project).glob("*.uproject")):
                project_made(project, "Score")
            level, sequence = scene_plan.level_path(place), scene_plan.sequence_path(place)
        ini = (pathlib.Path(project) / "Config/DefaultEngine.ini").read_text()
        refused = project_refusal(ini)
        if refused:
            raise SystemExit(f"the project cannot render with hardware ray tracing: {refused}")
        shot_file = scratch / "shot.json"
        shot_file.write_text(json.dumps(shot(uproject(project), level, sequence, frames,
                                             scene_step(film_path) if package else None), indent=1))
        described = job(project, frames, shot_file, out, package, film_path)
        if dry_run:
            print(json.dumps(described, indent=1))
            return None
        if not provider.on_cluster(KIND):
            raise SystemExit("Unreal renders run on the cluster only (SCORE_CLOUD=k8s): its GPU operator's driver "
                             "gives the containers Vulkan, the rented machines' compute driver does not")
        run_name = cluster_jobs.run_id(KIND)
        failed = cluster_jobs.run(KIND, [described], who, classes=[card_class], image=IMAGE, name=run_name)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if failed:
        raise SystemExit(f"run {run_name}: the render did not finish (its failure is said above)")
    twice = finish(out, run_name, card_class)
    faults = scene_faults(out)
    print(f"{run_name}: {frames} frames in {out}; render twice: {'same' if twice['same'] else 'DIFFERS'} "
          f"(largest tile difference {twice['largest']:.3f}); cost in {pathlib.Path(out) / 'cost.json'}"
          + (f"; NOT A RESULT: the level was made with {len(faults)} faults (record.json)" if faults else ""))
    return run_name


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", nargs="?", help="the Unreal project folder (one .uproject, "
                                                   "Config/DefaultEngine.ini); made here with --package")
    parser.add_argument("--map", help="the level, as /Game/... (not with --package)")
    parser.add_argument("--sequence", help="the level sequence, as /Game/....<name> (not with --package)")
    parser.add_argument("--package", help="a scene package (package --film) whose level is made on the card")
    parser.add_argument("--film-path", help="the place's film/path.json, the Level Sequence's camera (with --package)")
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--class", dest="card_class", required=True, choices=CLASSES, help="one card model a shot")
    parser.add_argument("--out", required=True)
    parser.add_argument("--who", required=True)
    parser.add_argument("--dry-run", action="store_true", help="print the job, send nothing")
    options = parser.parse_args()
    if not options.package and not (options.project and options.map and options.sequence):
        parser.error("give a project with --map and --sequence, or --package")
    if options.package and (options.map or options.sequence):
        parser.error("--package makes its own level and sequence: no --map or --sequence")
    render(options.project, options.map, options.sequence, options.frames, options.card_class, options.out,
           options.who, options.dry_run, options.package, options.film_path)


if __name__ == "__main__":
    main()
