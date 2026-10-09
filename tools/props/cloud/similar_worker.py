"""Runs on a rented machine: DINOv2's likeness of pairs of pictures.

    /root/venv/bin/python similar_worker.py <weights repo> <pairs.json> <in folder> <out.json>

pairs.json: {name: [first picture, second picture]}, the file names in <in folder>. Each picture is shown to DINOv2
whole (on white where it is clear), and the pair's likeness is the cosine of the two class tokens; out.json is
{name: likeness}.
"""
import json
import pathlib
import sys

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


def picture(path):
    """The picture as RGB, clear parts on white."""
    cut = Image.open(path).convert("RGBA")
    return Image.alpha_composite(Image.new("RGBA", cut.size, (255, 255, 255, 255)), cut).convert("RGB")


def main():
    weights, pairs, source, out = sys.argv[1], json.loads(pathlib.Path(sys.argv[2]).read_text()), \
        pathlib.Path(sys.argv[3]), pathlib.Path(sys.argv[4])
    processor = AutoImageProcessor.from_pretrained(weights)
    model = AutoModel.from_pretrained(weights).to("cuda").eval()
    found = {}
    for name, (first, second) in sorted(pairs.items()):
        inputs = processor(images=[picture(source / first), picture(source / second)], return_tensors="pt").to("cuda")
        with torch.inference_mode():
            tokens = model(**inputs).last_hidden_state[:, 0]
        found[name] = float(torch.nn.functional.cosine_similarity(tokens[0:1], tokens[1:2]).item())
        print(name, round(found[name], 3), flush=True)
    out.write_text(json.dumps(found, indent=1))


if __name__ == "__main__":
    main()
