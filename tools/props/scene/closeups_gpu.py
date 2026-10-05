"""The card's half of closeups.py: render every planned camera from the world's splats and cut each item out of its
close-ups, resolved against its neighbours.

    python tools/props/scene/closeups_gpu.py <splats.ply> <cameras.json> <out folder>

Renders each camera with gsplat (colour and expected depth). For every item whose prompt points the camera sees, a
point counts only where nothing stands in front of it (its depth within the rendered depth there), and SAM 2.1 is
prompted with that item's visible points, its best of three masks kept with its predicted score. The masks are then
resolved into one label per pixel, the highest score winning (closeups.resolve), so no two items claim a pixel; the
camera's own item is cut out on transparency from its label alone. Writes <out>/<item>-<shot>.png (the render),
-labels.png (the partition, one colour per item), -cut.png (the item alone) and <out>/closeups.json.

SAM 2.1 is Meta's (Apache-2.0); gsplat is Nerfstudio's (Apache-2.0). Loads models: it runs on a rented card
(cloud/closeups_cloud.py), and on this PC it is refused.
"""
import colorsys
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from closeups import cut, resolve  # noqa: E402
from local_models import refuse_here  # noqa: E402

SAM_WEIGHTS = "facebook/sam2.1-hiera-large"
# A prompt point is seen when its depth is within this share (and this much) of the rendered depth there.
SEEN_SHARE = 1.08
SEEN_SLACK_M = 0.05
# A picture pixel counts as rendered when the splats cover it this much.
COVERED = 0.5


def splats(path, scale):
    """The PLY's Gaussians in metres: centres, rotations, scales, opacities and colours (degree 0)."""
    raw = pathlib.Path(path).read_bytes()
    header, _, body = raw.partition(b"end_header\n")
    names = [line.split()[-1].decode() for line in header.splitlines() if line.startswith(b"property")]
    data = np.frombuffer(body, dtype="<f4").reshape(-1, len(names))
    column = {name: index for index, name in enumerate(names)}
    pick = lambda *keys: data[:, [column[key] for key in keys]]  # noqa: E731
    return {"means": pick("x", "y", "z") * scale,
            "quats": pick("rot_0", "rot_1", "rot_2", "rot_3"),
            "scales": np.exp(pick("scale_0", "scale_1", "scale_2")) * scale,
            "opacities": 1 / (1 + np.exp(-data[:, column["opacity"]])),
            "colours": pick("f_dc_0", "f_dc_1", "f_dc_2")}


def render(gaussians, camera):
    """Colour (0-255), expected depth in metres and coverage of one camera."""
    import torch
    from gsplat import rasterization
    tensors = {key: torch.from_numpy(np.ascontiguousarray(value)).float().cuda() for key, value in gaussians.items()}
    quats = tensors["quats"] / tensors["quats"].norm(dim=-1, keepdim=True)
    size = camera["size"]
    view = torch.tensor(camera["view"], dtype=torch.float32, device="cuda")[None]
    intrinsics = torch.tensor(camera["intrinsics"], dtype=torch.float32, device="cuda")[None]
    with torch.no_grad():
        image, alpha, _ = rasterization(tensors["means"], quats, tensors["scales"], tensors["opacities"],
                                        tensors["colours"][:, None, :], view, intrinsics, size, size,
                                        sh_degree=0, near_plane=0.05, render_mode="RGB+ED", packed=False)
    colour = (image[0, ..., :3].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
    depth = image[0, ..., 3].cpu().numpy()
    return colour, depth, alpha[0, ..., 0].cpu().numpy()


def visible_points(camera, depth):
    """Each item's prompt points that nothing stands in front of."""
    size = camera["size"]
    found = {}
    for item, points in camera["prompts"].items():
        kept = []
        for point in points:
            column, row = (min(int(value), size - 1) for value in point["pixel"])
            surface = depth[row, column]
            if surface <= 0 or point["depth"] <= surface * SEEN_SHARE + SEEN_SLACK_M:
                kept.append(point["pixel"])
        if kept:
            found[item] = kept
    return found


def masks_for(model, processor, colour, prompted):
    """SAM 2.1's best mask and score for each item's visible points."""
    import torch
    items = list(prompted)
    most = max(len(points) for points in prompted.values())
    points = [[prompted[item][index % len(prompted[item])] for index in range(most)] for item in items]
    image = Image.fromarray(colour)
    inputs = processor(images=image, input_points=[points], input_labels=[[[1] * most for _ in items]],
                       return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model(**inputs, multimask_output=True)
    masks = processor.post_process_masks(outputs.pred_masks.cpu(), inputs["original_sizes"])[0]
    scores = outputs.iou_scores[0].cpu().numpy()
    best = scores.argmax(axis=1)
    return items, [masks[index, choice].numpy().astype(bool) for index, choice in enumerate(best)], \
        [float(scores[index, choice]) for index, choice in enumerate(best)]


def palette(names):
    colours = {}
    for index, name in enumerate(sorted(names)):
        red, green, blue = colorsys.hsv_to_rgb((index * 0.61803) % 1.0, 0.75, 0.95)
        colours[name] = (int(red * 255), int(green * 255), int(blue * 255))
    return colours


def main():
    refuse_here("splat rendering and SAM 2.1", "tools/props/cloud/closeups_cloud.py <world folder> --who <session>")
    splat_path, cameras_path, out = (pathlib.Path(argument) for argument in sys.argv[1:4])
    out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(cameras_path.read_text())
    gaussians = splats(splat_path, plan["metric_scale_factor"])
    from transformers import Sam2Model, Sam2Processor
    processor = Sam2Processor.from_pretrained(SAM_WEIGHTS)
    model = Sam2Model.from_pretrained(SAM_WEIGHTS).to("cuda").eval()
    colours = palette(item["id"] for item in plan["items"])
    report = []
    for camera in plan["cameras"]:
        key = f"{camera['item']}-{camera['shot']}"
        colour, depth, coverage = render(gaussians, camera)
        Image.fromarray(colour).save(out / f"{key}.png")
        prompted = visible_points(camera, depth)
        entry = {"key": key, "item": camera["item"], "shot": camera["shot"], "fov": camera["fov"],
                 "note": camera["note"], "rendered_share": round(float((coverage > COVERED).mean()), 4)}
        if camera["item"] not in prompted:
            entry["result"] = "hidden: something stands in front of every one of its points"
            report.append(entry)
            print(key, entry["result"], flush=True)
            continue
        items, masks, scores = masks_for(model, processor, colour, prompted)
        labels = resolve(masks, scores)
        picture = np.zeros_like(colour)
        for index, item in enumerate(items):
            picture[labels == index] = colours.get(item, (255, 255, 255))
        Image.fromarray((colour * 0.45 + picture * 0.55).astype(np.uint8)).save(out / f"{key}-labels.png")
        own = labels == items.index(camera["item"])
        cutout = cut(colour, own)
        if cutout is not None:
            Image.fromarray(cutout, "RGBA").save(out / f"{key}-cut.png")
        entry.update({"result": "cut" if cutout is not None else "lost to its neighbours",
                      "score": round(scores[items.index(camera["item"])], 3),
                      "own_share": round(float(own.mean()), 4),
                      "unassigned_share": round(float((labels < 0).mean()), 4),
                      "neighbours": {item: round(score, 3) for item, score in zip(items, scores) if item != camera["item"]}})
        report.append(entry)
        print(key, entry["result"], entry["score"], entry["own_share"], flush=True)
    (out / "closeups.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
