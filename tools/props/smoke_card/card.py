"""The billowing smoke flipbook (2099 prologue, the launch's smoke; the owner: "this smoke ... is shit"): one puff of
smoke simulated by Mantaflow and rendered six-way lit on the processor (billow.py), packed as the score_lib
surface `smoke_billow` that an effect's puff cards draw instead of a soft round card, so each card shows a lit,
rolling billow that grows over its life.

    .venv/bin/python tools/props/smoke_card/card.py render <work folder>     # Blender on the processor, ~2 minutes
    .venv/bin/python tools/props/smoke_card/card.py pack <work folder> <out folder>

`pack` writes <out>/smoke_a.png and smoke_b.png (FRAMES frames of the puff's life in a GRID x GRID atlas, read left to
right, top to bottom: smoke_a's red, green and blue the card lit from its right, top and back, smoke_b's from its left,
bottom and front, both alphas the smoke's cover; the six-way lighting a game blends by its own light's way),
material.usda (a UsdPreviewSurface showing the first frame lit from the top, its opacity the cover), preview.png (the
whole life lit from the top over a night sky's blue) and surface.json (the solver's settings and the atlas's layout).
"""
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
GRID = 4
FRAMES = GRID * GRID
ATLAS = {"smoke_a.png": ("right", "top", "back"), "smoke_b.png": ("left", "bottom", "front")}
PREVIEW_GROUND = (38, 52, 80)


def rendered(work):
    """billow.py run in a Blender batch on the processor into `work`; its return code."""
    command = ["python3", str(REPO / "tools/blender/session.py"), "batch", "--version",
               "5.2.2", str(HERE / "billow.py"), "--", str(work)]
    return subprocess.run(command, check=False).returncode


def frame(work, index, side):
    """One rendered frame lit from one side: (lit grey as 0..1, cover as 0..1), each PIXELS a side."""
    picture = np.asarray(Image.open(pathlib.Path(work) / "frames" / f"{index:02d}_{side}.png").convert("RGBA"),
                         dtype=np.float32) / 255.0
    return picture[..., :3].mean(axis=2), picture[..., 3]


def atlas(work, sides, pixels):
    """One RGBA atlas: its three channels the frames lit from `sides`, its alpha the cover, frames in reading order."""
    out = np.zeros((GRID * pixels, GRID * pixels, 4), dtype=np.float32)
    for index in range(FRAMES):
        row, column = divmod(index, GRID)
        lit = [frame(work, index, side) for side in sides]
        cell = np.stack([grey for grey, _ in lit] + [lit[0][1]], axis=2)
        out[row * pixels:(row + 1) * pixels, column * pixels:(column + 1) * pixels] = cell
    return out


def preview(work, pixels):
    """The puff's whole life lit from the top, laid over the night sky's blue, as one picture."""
    sheet = np.zeros((GRID * pixels, GRID * pixels, 3), dtype=np.float32)
    ground = np.asarray(PREVIEW_GROUND, dtype=np.float32) / 255.0
    for index in range(FRAMES):
        row, column = divmod(index, GRID)
        grey, cover = frame(work, index, "top")
        cell = grey[..., None] * cover[..., None] + ground * (1.0 - cover[..., None])
        sheet[row * pixels:(row + 1) * pixels, column * pixels:(column + 1) * pixels] = cell
    return sheet


def saved(array, path):
    """An array of 0..1 values saved as an 8-bit PNG."""
    Image.fromarray(np.clip(np.round(array * 255.0), 0, 255).astype(np.uint8)).save(path)


MATERIAL = """#usda 1.0
(
    defaultPrim = "smoke_billow"
    metersPerUnit = 1
    upAxis = "Y"
)

def Material "smoke_billow" (
    doc = "The billowing smoke flipbook's first frame lit from the top: its colour smoke_a's green, its opacity the cover. A game reads the atlases by surface.json's layout."
)
{
    token outputs:surface.connect = </smoke_billow/surface.outputs:surface>

    def Shader "surface"
    {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor.connect = </smoke_billow/top.outputs:rgb>
        float inputs:opacity.connect = </smoke_billow/atlas.outputs:a>
        float inputs:opacityThreshold = 0
        float inputs:roughness = 1
        token outputs:surface
    }

    def Shader "uv"
    {
        uniform token info:id = "UsdPrimvarReader_float2"
        string inputs:varname = "st"
        float2 outputs:result
    }

    def Shader "first"
    {
        uniform token info:id = "UsdTransform2d"
        float2 inputs:in.connect = </smoke_billow/uv.outputs:result>
        float2 inputs:scale = (0.25, 0.25)
        float2 inputs:translation = (0, 0.75)
        float2 outputs:result
    }

    def Shader "atlas"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @./smoke_a.png@
        float2 inputs:st.connect = </smoke_billow/first.outputs:result>
        token inputs:sourceColorSpace = "raw"
        float outputs:a
        float outputs:g
    }

    def Shader "top"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @./smoke_a.png@
        float2 inputs:st.connect = </smoke_billow/first.outputs:result>
        token inputs:sourceColorSpace = "raw"
        float4 inputs:scale = (1, 1, 1, 1)
        float3 outputs:rgb
    }
}
"""


def packed(work, out):
    """The atlases, material, preview and record written into `out` from the rendered frames in `work`; {name: path}."""
    work, out = pathlib.Path(work), pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    sim = json.loads((work / "sim.json").read_text())
    if len(sim["taken"]) != FRAMES:
        raise ValueError(f"{len(sim['taken'])} frames rendered, the atlas holds {FRAMES}")
    written = {}
    for name, sides in ATLAS.items():
        saved(atlas(work, sides, sim["pixels"]), out / name)
        written[name] = out / name
    saved(preview(work, sim["pixels"]), out / "preview.png")
    (out / "material.usda").write_text(MATERIAL)
    record = {"family": "flipbook", "look": "billowing smoke, lit six ways",
              "atlas": {"grid": [GRID, GRID], "frames": FRAMES, "order": "left to right, top to bottom",
                        "frame_pixels": sim["pixels"], "frame_metres": sim["domain_m"],
                        "channels": {name: {"rgb": list(sides), "a": "cover"} for name, sides in ATLAS.items()},
                        "colour_space": "raw (lit grey, linear in the renderer's Standard view)"},
              "made_by": "tools/props/smoke_card (Mantaflow gas, Cycles on the processor)", "sim": sim}
    (out / "surface.json").write_text(json.dumps(record, indent=1) + "\n")
    written.update({name: out / name for name in ("preview.png", "material.usda", "surface.json")})
    return written


if __name__ == "__main__":
    if sys.argv[1] == "render":
        raise SystemExit(rendered(sys.argv[2]))
    for name, path in packed(sys.argv[2], sys.argv[3]).items():
        print(name, path)
