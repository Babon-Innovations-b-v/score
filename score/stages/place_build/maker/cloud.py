"""TRELLIS.2 on a cloud card (#128, 2026-11-19: GPU work goes to the cloud, never this PC's card): generate.py, as the
card queue runs it here, in the meshparts image's TRELLIS.2 (its SegviGen checkout's `trellis2`, whose pipelines are
TRELLIS.2's own, on its author's published cumesh, flex_gemm and o_voxel wheels; tools/cloud/images/meshparts/), its
weights from the node cache (images/meshparts/models.json: `trellis2-4b-make`, TRELLIS-image-large's structure
decoder, DINOv3), one job for any number of pictures, each in its own process as generate.py asks.

    made(pairs, who) -> {out.glb: its stats} for [(picture.png, out.glb[, faces]), ...], run on the cluster
    (SCORE_CLOUD=k8s); a pair's faces (maker.faces_for its size) as the PC's make passes them, else generate.FACES

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
