"""TRELLIS.2 on a cloud card (#128, 2026-11-19: GPU work goes to the cloud, never this PC's card): generate.py, as the
card queue runs it here, in the meshparts image's TRELLIS.2 (its SegviGen checkout's `trellis2`, whose pipelines are
TRELLIS.2's own, on its author's published cumesh, flex_gemm and o_voxel wheels; tools/cloud/images/meshparts/), its
weights from the node cache (images/meshparts/models.json: `trellis2-4b-make`, TRELLIS-image-large's structure
decoder, DINOv3), one job for any number of pictures, each in its own process as generate.py asks.

    made(pairs, who) -> {out.glb: its stats} for [(picture.png, out.glb[, faces[, seed]]), ...], run on the cluster
    (SCORE_CLOUD=k8s); a pair's faces (maker.faces_for its size) as the PC's make passes them, else generate.FACES
    remade(pairs, who, attempt[, sizes]) -> the same for a remake: generate.TAKES takes a picture at
    generate.seeds_for(attempt) (never the failed make's seed 42) in the one job, all kept under
    <out folder>/takes/seed<n>/, the take whose outline best overlaps its close-up's laid at out.glb (best_take)

Each model comes back as generate.py leaves it here: its .json and its decoded mesh beside it (brought_back).

The env folder generate.py reads (weights/, src/TRELLIS.2, ready.json) is laid in the pod from those (`ENV_LINES`);
pipeline_here.json is written in its own TRELLIS.2-4B folder there, never into the node cache.
"""
import json
import pathlib
import shlex
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
KIND = "meshparts"  # capacity.py's kind and the image: 24 GB cards first
MODELS = ["trellis2-4b-make", "trellis-image-large-ssdec", "dinov3-vitl16"]
PYTHON = "/opt/sv/venv/bin/python"
CHECKOUT = "/opt/sv/SegviGen"
ENV = "/work/env"
SETUP_MINUTES = 15  # the weights' first fetch onto a node (about 14 GB) and the pipeline's load
MINUTES_A_PICTURE = 8  # about two minutes a model on the PC's card; the rest is headroom
READY = {"by": "the meshparts image's TRELLIS.2 (SegviGen's checkout, its author's wheels)",
         "weights": "tools/cloud/images/meshparts/models.json: trellis2-4b-make, trellis-image-large-ssdec, "
                    "dinov3-vitl16"}
ENV_LINES = [
    f"mkdir -p {ENV}/weights/TRELLIS.2-4B {ENV}/weights/TRELLIS-image-large {ENV}/src",
    f'ln -sfn "$SCORE_MODEL_TRELLIS2_4B_MAKE/pipeline.json" {ENV}/weights/TRELLIS.2-4B/pipeline.json',
    f'ln -sfn "$SCORE_MODEL_TRELLIS2_4B_MAKE/ckpts" {ENV}/weights/TRELLIS.2-4B/ckpts',
    f'ln -sfn "$SCORE_MODEL_TRELLIS_IMAGE_LARGE_SSDEC/ckpts" {ENV}/weights/TRELLIS-image-large/ckpts',
    f'ln -sfn "$SCORE_MODEL_DINOV3_VITL16" {ENV}/weights/dinov3',
    f"ln -sfn {CHECKOUT} {ENV}/src/TRELLIS.2",
    f"echo {shlex.quote(json.dumps(READY))} > {ENV}/ready.json"]


def job_of(pairs):
    """The cluster job making each (picture, out.glb) of `pairs`: the pictures at /work/in/<n>.png, the models at
    /work/out/<n>/model.glb with their stats, each made in a process of its own."""
    lines = list(ENV_LINES)
    for number, pair in enumerate(pairs):
        faces = f" {int(pair[2])}" if len(pair) > 2 and pair[2] else ""
        if len(pair) > 3 and pair[3] is not None:  # a remake's take: its own seed, after its faces
            from score.stages.place_build.maker import generate
            faces = f" {int(pair[2]) if pair[2] else generate.FACES} {int(pair[3])}"
        lines.append(f"mkdir -p /work/out/{number} && {PYTHON} -I score/stages/place_build/maker/generate.py {ENV} "
                     f"/work/in/{number}.png /work/out/{number}/model.glb{faces}")
    return {"command": ["bash", "-c", "set -euo pipefail; " + " && ".join(lines)],
            "code": ["score/stages/place_build/maker/generate.py", "score/stages/place_build/maker/remesh.py",
                     "score/stages/place_build/maker/shim"],
            "models": MODELS,
            "env": {"MALLOC_ARENA_MAX": "2"},
            "inputs": [{"local": str(picture), "path": f"/work/in/{number}.png"}
                       for number, (picture, *_) in enumerate(pairs)],
            "outputs": [{"path": f"/work/out/{number}", "local": str(pathlib.Path(out).parent / f".cloud-{number}")}
                        for number, (_, out, *_) in enumerate(pairs)],
            "minutes": SETUP_MINUTES + MINUTES_A_PICTURE * len(pairs)}


def made(pairs, who):
    """Each (picture, out.glb) of `pairs` made on one cloud card; {out: its stats}. A picture whose model did not come
    back raises, naming it."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs
    job = job_of(pairs)
    failed = cluster_jobs.run(KIND, [job], who)
    if failed:
        raise RuntimeError(f"TRELLIS.2's cloud job failed ({len(pairs)} pictures)")
    stats = {}
    for output, (picture, out, *_) in zip(job["outputs"], pairs):
        if not (pathlib.Path(output["local"]) / "model.glb").is_file():
            raise RuntimeError(f"{picture}: no model came back")
        stats[str(out)] = brought_back(pathlib.Path(output["local"]), pathlib.Path(out))
    return stats


def take_path(out, seed):
    """Where a remake's take at `seed` of the model `out` is kept: <out folder>/takes/seed<seed>/<out name>."""
    return pathlib.Path(out).parent / "takes" / f"seed{seed}" / pathlib.Path(out).name


def best_take(picture, takes, size=None):
    """Of `takes` ({seed: its glb}), the seed whose model's outline from the close-up's camera best overlaps the cut-out
    `picture`'s (fit.headed over its quarter turns; the row's `size`, else the take's own box, sets the camera) and each
    take's overlap {seed: overlap}."""
    import numpy as np
    from PIL import Image
    from score.stages.place_build import maker
    from score.stages.place_build.maker import fit
    cut = np.asarray(Image.open(picture).getchannel("A")) > 127
    overlaps = {}
    for seed, glb in takes.items():
        points = maker.surface_points(glb)[0]
        wide, tall, deep = np.ptp(points, axis=0)
        turn, down = maker.close_up_view(size or [float(wide), float(deep), float(tall)])
        overlaps[seed] = fit.headed(points, cut, turn, down)[1]["overlap"]
    return max(overlaps, key=lambda seed: (overlaps[seed], -seed)), overlaps


def laid_take(take, out, seed, overlaps):
    """The chosen take `take` (its glb, stats and decoded mesh) copied to `out`, its stats naming every take's seed and
    overlap and why it was kept; its stats."""
    import shutil
    from score.stages.place_build.maker import generate
    shutil.copyfile(take, out)
    decoded = generate.decoded_path(take)
    if decoded.is_file():
        shutil.copyfile(decoded, generate.decoded_path(out))
    stats = {**json.loads(take.with_suffix(".json").read_text()),
             "takes": [{"seed": seed_of, "overlap": overlap} for seed_of, overlap in sorted(overlaps.items())],
             "kept": f"seed {seed}: its outline best overlaps the close-up's (fit.headed), every take kept beside"}
    out.with_suffix(".json").write_text(json.dumps(stats, indent=1))
    return stats


def remade(pairs, who, attempt, sizes=None):
    """Each (picture, out.glb[, faces]) of `pairs` remade on one cloud card at remake `attempt`'s seeds
    (generate.seeds_for: TAKES takes a picture, never the failed make's seed), the take that best matches its close-up
    laid at out (best_take, laid_take), `sizes` each pair's row size or None; {out: its stats}."""
    from score.stages.place_build.maker import generate
    seeds = generate.seeds_for(attempt)
    takes = []
    for picture, out, *rest in pairs:
        for seed in seeds:
            path = take_path(out, seed)
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.is_file():
                takes.append((picture, path, rest[0] if rest else None, seed))
    if takes:
        made(takes, who)
    stats = {}
    for number, (picture, out, *_) in enumerate(pairs):
        kept, overlaps = best_take(picture, {seed: take_path(out, seed) for seed in seeds},
                                   sizes[number] if sizes else None)
        stats[str(out)] = laid_take(take_path(out, kept), pathlib.Path(out), kept, overlaps)
    return stats


def brought_back(back, out):
    """A model's cloud output folder `back` laid where generate.py writes it on this PC: its model at `out`, its
    stats at <out>.json and its decoded mesh beside it (generate.decoded_path, #159: the seams the place's bake and the
    bench's look shade from, #209) where it made one; the folder removed. Its stats."""
    from score.stages.place_build.maker import generate
    (back / "model.glb").replace(out)
    (back / "model.json").replace(out.with_suffix(".json"))
    decoded = generate.decoded_path(back / "model.glb")
    if decoded.is_file():
        decoded.replace(generate.decoded_path(out))
    back.rmdir()
    return json.loads(out.with_suffix(".json").read_text())
