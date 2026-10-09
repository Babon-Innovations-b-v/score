"""Runs on a rented machine: SAM 3 asked, by text, for each finish of each close-up in a folder.

    /root/venv/bin/python finish_masks_worker.py <weights> <in folder> <out folder>

Each <take>.png (the clean close-up on white) comes with <take>.json, {"phrases": {code: phrase}}; each comes back
as <out>/<take>.npz: per code the union of the instances SAM 3 finds over THRESHOLD (`mask_<code>`, packed bits,
n x height x ceil(width / 8) with n 1) and their best score (`score_<code>`), and `shape`.
"""
import json
import pathlib
import sys

import numpy as np
import torch
from PIL import Image
from transformers import Sam3Model, Sam3Processor

THRESHOLD = 0.2
MASK_THRESHOLD = 0.5


def main():
    weights, source, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    processor = Sam3Processor.from_pretrained(weights)
    model = Sam3Model.from_pretrained(weights, torch_dtype=torch.float32).to("cuda").eval()
    for path in sorted(source.glob("*.png")):
        image = Image.open(path).convert("RGB")
        phrases = json.loads(path.with_suffix(".json").read_text())["phrases"]
        found = {"shape": np.array(image.size[::-1])}
        for code, phrase in phrases.items():
            inputs = processor(images=image, text=phrase, return_tensors="pt").to("cuda")
            with torch.no_grad():
                outputs = model(**inputs)
            result = processor.post_process_instance_segmentation(
                outputs, threshold=THRESHOLD, mask_threshold=MASK_THRESHOLD, target_sizes=[image.size[::-1]])[0]
            masks = [mask.cpu().numpy().astype(bool) for mask in result["masks"]]
            union = np.any(masks, axis=0) if masks else np.zeros(image.size[::-1], dtype=bool)
            found[f"mask_{code}"] = np.packbits(union[None], axis=-1)
            found[f"score_{code}"] = np.array(max([float(score) for score in result["scores"]], default=0.0))
            print(path.stem, code, phrase, len(masks), flush=True)
        np.savez_compressed(out / f"{path.stem}.npz", **found)


if __name__ == "__main__":
    main()
