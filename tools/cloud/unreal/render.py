"""Unreal Engine 5.8 renders of one shot on one card of the Kubernetes cluster (SCORE_CLOUD=k8s; #215, #222): the
project the placer made (#217) goes up as the job's input, the score-unreal image (tools/cloud/images/unreal/: Epic's
official Linux image with the job runtime, in the project's private registry only) runs on_card.py there, and the
frames, the render-twice check and the cost of a frame come back.

    .venv/bin/python tools/cloud/unreal/render.py <project folder> --map /Game/Place/Street \
        --sequence /Game/Place/Film.Film --frames 96 --class gpu-48gb --out <folder> --who "<session>" [--dry-run]

<project folder> holds one .uproject and its Config/DefaultEngine.ini, which must target Vulkan SM6 alone with
hardware ray tracing and Lumen on (`project_refusal`; refused before anything is sent). One shot is one card model
(L40S frames come out slightly darker than other cards', #216): `--class` names one class.

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

import _cost  # noqa: E402
import _twice  # noqa: E402

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


def uproject(folder):
    """The project folder's one .uproject."""
    found = sorted(pathlib.Path(folder).glob("*.uproject"))
    if len(found) != 1:
        raise SystemExit(f"{folder} holds {len(found)} .uproject files; one is needed")
    return found[0]


def shot(project_file, level, sequence, frames):
    """What on_card.py renders: the editor, the project up there, the level and sequence, the two passes (every frame
    and the first CHECK_FRAMES again, each its own config asset and folder) and the recipe."""
    out = UP / "out"
    return {"editor": EDITOR, "user": USER, "project": str(UP / "project" / project_file.name), "map": level,
            "sequence": sequence, "out": str(out), "recipe": RECIPE,
            "passes": [{"name": "full", "config": "/Game/ScoreRender/Full", "start": 0, "end": frames,
                        "folder": str(out / "full")},
                       {"name": "check", "config": "/Game/ScoreRender/Check", "start": 0,
                        "end": min(CHECK_FRAMES, frames), "folder": str(out / "check")}]}


def job(project, frames, shot_file, out):
    """The cluster job (cluster_jobs.run's form) that renders the shot: on_card.py in the image, the project and
    shot.json up, the out folder back, the shader cache named."""
    ini = (pathlib.Path(project) / "Config/DefaultEngine.ini").read_text()
    minutes = COLD_MINUTES + 3 * START_MINUTES + (frames + min(CHECK_FRAMES, frames)) * SECONDS_A_FRAME / 60
    return {"command": ["/opt/score/venv/bin/python", "tools/cloud/unreal/on_card.py", str(UP / "shot.json")],
            "code": ["tools/cloud/unreal"],
            "inputs": [{"local": str(project), "path": str(UP / "project")},
                       {"local": str(shot_file), "path": str(UP / "shot.json")}],
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


def render(project, level, sequence, frames, card_class, out, who, dry_run=False):
    """Send the shot's job, bring its frames back and write the check and the cost; the run's name."""
    import cluster_jobs
    import provider

    ini = (pathlib.Path(project) / "Config/DefaultEngine.ini").read_text()
    refused = project_refusal(ini)
    if refused:
        raise SystemExit(f"the project cannot render with hardware ray tracing: {refused}")
    if card_class not in CLASSES:
        raise SystemExit(f"{card_class} is not one of {', '.join(CLASSES)} (cards with ray-tracing cores)")
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="unreal-shot-"))
    try:
        shot_file = scratch / "shot.json"
        shot_file.write_text(json.dumps(shot(uproject(project), level, sequence, frames), indent=1))
        described = job(project, frames, shot_file, out)
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
    print(f"{run_name}: {frames} frames in {out}; render twice: {'same' if twice['same'] else 'DIFFERS'} "
          f"(largest tile difference {twice['largest']:.3f}); cost in {pathlib.Path(out) / 'cost.json'}")
    return run_name


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("project", help="the Unreal project folder (one .uproject, Config/DefaultEngine.ini)")
    parser.add_argument("--map", required=True, help="the level, as /Game/...")
    parser.add_argument("--sequence", required=True, help="the level sequence, as /Game/....<name>")
    parser.add_argument("--frames", type=int, required=True)
    parser.add_argument("--class", dest="card_class", required=True, choices=CLASSES, help="one card model a shot")
    parser.add_argument("--out", required=True)
    parser.add_argument("--who", required=True)
    parser.add_argument("--dry-run", action="store_true", help="print the job, send nothing")
    options = parser.parse_args()
    render(options.project, options.map, options.sequence, options.frames, options.card_class, options.out,
           options.who, options.dry_run)


if __name__ == "__main__":
    main()
