"""The card's half of closeups.py, in three steps, each in the Python its models need (cloud/closeups_setup.sh):

    python tools/props/scene/closeups_gpu.py render  <splats.ply> <cameras.json> <out>   # gsplat (torch 2.4)
    python tools/props/scene/closeups_gpu.py segment <cameras.json> <out>                # SAM 3 (torch 2.9)
    python tools/props/scene/closeups_gpu.py matte   <folder>                            # image-to-3dlab's remover

render: every camera from the world's splats: <key>.png (colour), <key>.depth.npy (expected depth in metres).
segment: for every item a camera sees, only the prompt points nothing stands in front of (the rendered depth) are kept;
SAM 3's point-and-box model (Sam3Tracker) is prompted with those points and the item's 3D box projected into the
picture, and SAM 3's text model is asked for the item's words; the point mask's score is weighted by how well the best
text mask agrees with it (0.5 + 0.5 x their overlap), so a mask that is not the named thing loses. Each mask's edge is
refined inside a band round its border: a band pixel goes to the item when its colour is nearer the item's inside than
the outside ring. The masks are then resolved into one label per pixel, the highest score winning
(closeups.resolve), and the camera's own item is cut out: <key>-labels.png, <key>-cut.png, closeups.json.
matte: every <name>.png in the folder cut out with image-to-3dlab's own remover (BiRefNet-lite through rembg, the
same cut the object maker makes) as <name>__matted.png.

SAM 3 is Meta's (SAM License, commercial use allowed), its weights from SAM3_WEIGHTS (a copy, as for cutout.py);
gsplat is Nerfstudio's (Apache-2.0); BiRefNet-lite (MIT) through rembg (MIT). Loads models: it runs on a rented card
(cloud/closeups_cloud.py), and on this PC it is refused.
"""
import colorsys
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from closeups import cut, resolve  # noqa: E402
from local_models import refuse_here  # noqa: E402

SAM3_WEIGHTS = os.environ.get("SAM3_WEIGHTS", "facebook/sam3")
# A prompt point is seen when its depth is within this share (and this much) of the rendered depth there.
SEEN_SHARE = 1.08
SEEN_SLACK_M = 0.05
# A picture pixel counts as rendered when the splats cover it this much.
COVERED = 0.5
# Text instances SAM 3 must be this sure of to count; the band round a mask's border that is refined, in pixels.
TEXT_SURENESS = 0.3
BAND = 6


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


def render_one(gaussians, camera):
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
    return colour, image[0, ..., 3].cpu().numpy(), alpha[0, ..., 0].cpu().numpy()


def key_of(camera):
    return f"{camera['item']}-{camera['shot']}"


def render(splat_path, plan, out):
    gaussians = splats(splat_path, plan["metric_scale_factor"])
    for camera in plan["cameras"]:
        colour, depth, coverage = render_one(gaussians, camera)
        Image.fromarray(colour).save(out / f"{key_of(camera)}.png")
        np.save(out / f"{key_of(camera)}.depth.npy", depth.astype(np.float32))
        np.save(out / f"{key_of(camera)}.cover.npy", (coverage > COVERED))
        print("rendered", key_of(camera), flush=True)


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


def refine(colour, mask):
    """A mask's border band given to whichever side its colour is nearer: the mask's eroded inside or its outside ring."""
    from scipy import ndimage
    inside = ndimage.binary_erosion(mask, iterations=BAND)
    grown = ndimage.binary_dilation(mask, iterations=BAND)
    ring = ndimage.binary_dilation(mask, iterations=2 * BAND) & ~grown
    if inside.sum() < 50 or ring.sum() < 50:
        return mask
    pixels = colour.astype(np.float32)
    near_in = np.linalg.norm(pixels - pixels[inside].mean(axis=0), axis=-1)
    near_out = np.linalg.norm(pixels - pixels[ring].mean(axis=0), axis=-1)
    band = grown & ~inside
    refined = mask.copy()
    refined[band] = near_in[band] < near_out[band]
    return ndimage.binary_opening(refined, iterations=1) | inside


class Segmenter:
    """SAM 3's point-and-box model and its text model, loaded once."""

    def __init__(self):
        import torch
        from transformers import Sam3Model, Sam3Processor, Sam3TrackerModel, Sam3TrackerProcessor
        self.torch = torch
        self.points_processor = Sam3TrackerProcessor.from_pretrained(SAM3_WEIGHTS)
        self.points_model = Sam3TrackerModel.from_pretrained(SAM3_WEIGHTS).to("cuda").eval()
        self.text_processor = Sam3Processor.from_pretrained(SAM3_WEIGHTS)
        self.text_model = Sam3Model.from_pretrained(SAM3_WEIGHTS).to("cuda").eval()

    def by_points(self, image, points, box):
        """The best of three masks for one item's points (and box), with its predicted score."""
        inputs = {"images": image, "input_points": [[points]], "input_labels": [[[1] * len(points)]], "return_tensors": "pt"}
        if box:
            inputs["input_boxes"] = [[box]]
        tensors = self.points_processor(**inputs).to("cuda")
        with self.torch.no_grad():
            outputs = self.points_model(**tensors, multimask_output=True)
        masks = self.points_processor.post_process_masks(outputs.pred_masks.cpu(), tensors["original_sizes"])[0]
        scores = outputs.iou_scores[0, 0].cpu().numpy()
        best = int(scores.argmax())
        return masks[0, best].numpy().astype(bool), float(scores[best])

    def by_text(self, image, words):
        """Every instance of the words SAM 3 is sure of, as masks."""
        tensors = self.text_processor(images=image, text=words, return_tensors="pt").to("cuda")
        with self.torch.no_grad():
            outputs = self.text_model(**tensors)
        result = self.text_processor.post_process_instance_segmentation(
            outputs, threshold=TEXT_SURENESS, mask_threshold=0.5, target_sizes=[image.size[::-1]])[0]
        return [mask.cpu().numpy().astype(bool) for mask in result["masks"]]


def agreement(mask, text_masks):
    """The best overlap (over the union) between a point mask and any text mask of the same words; 0 when none."""
    best = 0.0
    for other in text_masks:
        union = (mask | other).sum()
        if union:
            best = max(best, float((mask & other).sum()) / union)
    return best


def palette(names):
    colours = {}
    for index, name in enumerate(sorted(names)):
        red, green, blue = colorsys.hsv_to_rgb((index * 0.61803) % 1.0, 0.75, 0.95)
        colours[name] = (int(red * 255), int(green * 255), int(blue * 255))
    return colours


def segment(plan, out):
    segmenter = Segmenter()
    colours = palette(item["id"] for item in plan["items"])
    report = []
    for camera in plan["cameras"]:
        key = key_of(camera)
        colour = np.asarray(Image.open(out / f"{key}.png").convert("RGB"))
        depth = np.load(out / f"{key}.depth.npy")
        image = Image.fromarray(colour)
        prompted = visible_points(camera, depth)
        entry = {"key": key, "item": camera["item"], "shot": camera["shot"], "fov": camera["fov"], "note": camera["note"],
                 "rendered_share": round(float(np.load(out / f"{key}.cover.npy").mean()), 4)}
        if camera["item"] not in prompted:
            entry["result"] = "hidden: something stands in front of every one of its points"
            report.append(entry)
            print(key, entry["result"], flush=True)
            continue
        items, masks, scores, raw, agreed = [], [], [], [], []
        text_cache = {}
        for item, points in prompted.items():
            mask, score = segmenter.by_points(image, points, camera.get("boxes", {}).get(item))
            words = camera.get("labels", {}).get(item, item)
            if words not in text_cache:
                text_cache[words] = segmenter.by_text(image, words)
            overlap = agreement(mask, text_cache[words])
            items.append(item)
            masks.append(refine(colour, mask))
            raw.append(score)
            agreed.append(overlap)
            scores.append(score * (0.5 + 0.5 * overlap))
        labels = resolve(masks, scores)
        picture = np.zeros_like(colour)
        for index, item in enumerate(items):
            picture[labels == index] = colours.get(item, (255, 255, 255))
        Image.fromarray((colour * 0.45 + picture * 0.55).astype(np.uint8)).save(out / f"{key}-labels.png")
        mine = items.index(camera["item"])
        own = labels == mine
        cutout = cut(colour, own)
        if cutout is not None:
            Image.fromarray(cutout, "RGBA").save(out / f"{key}-cut.png")
        entry.update({"result": "cut" if cutout is not None else "lost to its neighbours",
                      "score": round(scores[mine], 3), "point_score": round(raw[mine], 3), "text_overlap": round(agreed[mine], 3),
                      "own_share": round(float(own.mean()), 4), "unassigned_share": round(float((labels < 0).mean()), 4),
                      "neighbours": {item: round(score, 3) for item, score in zip(items, scores) if item != camera["item"]}})
        report.append(entry)
        print(key, entry["result"], entry["score"], entry["point_score"], entry["text_overlap"], flush=True)
    (out / "closeups.json").write_text(json.dumps(report, indent=1))


def matte(folder):
    """Every picture in the folder cut out with image-to-3dlab's own remover."""
    sys.path.insert(0, os.environ.get("IMAGE_TO_3DLAB", "/root/closeups/lab"))
    from image_to_3dlab.matte import cut_out, new_session, matte_model
    session = new_session()
    for picture in sorted(pathlib.Path(folder).glob("*.png")):
        if picture.stem.endswith("__matted"):
            continue
        with Image.open(picture) as opened:
            cutout, _ = cut_out(opened.convert("RGB"), session)
        cutout.save(picture.with_name(f"{picture.stem}__matted.png"))
        print("matted", picture.name, matte_model(), flush=True)


def main():
    refuse_here("splat rendering, SAM 3 and the cut-out", "tools/props/cloud/closeups_cloud.py <folder> --who <session>")
    step = sys.argv[1]
    if step == "render":
        out = pathlib.Path(sys.argv[4])
        out.mkdir(parents=True, exist_ok=True)
        render(sys.argv[2], json.loads(pathlib.Path(sys.argv[3]).read_text()), out)
    elif step == "segment":
        segment(json.loads(pathlib.Path(sys.argv[2]).read_text()), pathlib.Path(sys.argv[3]))
    elif step == "matte":
        matte(sys.argv[2])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
