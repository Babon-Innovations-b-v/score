"""The garments' own finishes (#225), written as score_lib surfaces to take in: a high-visibility jacket's fluorescent
yellow polyester and its retroreflective tape. score_lib held no high-visibility finish: its polyester_yellow is an
olive (diffuse 0.27, 0.26, 0.10), and nothing retroreflective.

    python finishes.py <folder> <score commit> <polyester entry folder>

The polyester entry folder is surface/simready_m_opaque_fabric_polyester_yellow_a01_811e628c@1 fetched (score-lib
fetch): the fluorescent yellow wears its woven polyester's normal and ORM maps (NVIDIA SimReady, CC BY 4.0, carried
with NVIDIA's credit and the change marked) under a colour of its own; the tape is constant, made by score (MIT).

Colours are linear albedo. The fluorescent yellow is EN ISO 20471's yellow (its chromaticity area's middle, x 0.387 y
0.610, luminance factor 0.76) in linear sRGB, the blue it lies past the sRGB gamut by mixed with the same luminance's
white until none is negative: (0.445, 0.931, 0.0). The tape is a retroreflective fabric's silver grey as it shows
under light not from the camera (about 45% reflectance), a little glossier than the cloth.

Writes each finish's `material.usda` and `surface.json` (its constants, family and why) under `<folder>/<id>/`, and
`<folder>/take-in.json`, the listing `score-lib take-in` reads.
"""
import json
import pathlib
import shutil
import sys

POLYESTER = "simready_m_opaque_fabric_polyester_yellow_a01_811e628c"
NVIDIA_LICENCE = {
    "credit": "consumable_air_filter_cylindrical_a01 by NVIDIA Corporation, from "
              "huggingface.co/datasets/nvidia/simready-assets at revision 99bb6c7c1247ff3a1f63e484996336e9e35b9cf8, "
              "CC BY 4.0; changed: its polyester's maps worn under a high-visibility fluorescent yellow of score's",
    "id": "CC-BY-4.0", "source": "nvidia_simready", "url": "https://creativecommons.org/licenses/by/4.0/"}
MAPS_FROM = {"normal.png": "consumable_air_filter_cylindrical_a01/simready_usd/Textures/"
                           "t_polyester_linePattern_gray_a01_tile_nor.png",
             "orm.png": "consumable_air_filter_cylindrical_a01/simready_usd/Textures/"
                        "t_polyester_linePattern_gray_a01_tile_orm.png"}
FINISHES = {
    "hivis_fluorescent_yellow": {
        "title": "High-visibility fluorescent yellow polyester", "family": "fabric", "maps": True,
        "constants": {"diffuseColor": [0.445, 0.931, 0.0], "metallic": 0.0},
        "why": "EN ISO 20471's fluorescent yellow (x 0.387, y 0.610, luminance factor 0.76) in linear sRGB, mixed "
               "with white to the gamut; the woven polyester's relief and roughness from NVIDIA's polyester maps"},
    "retroreflective_tape_silver": {
        "title": "Retroreflective tape, silver (constant)", "family": "fabric", "maps": False,
        "constants": {"diffuseColor": [0.45, 0.45, 0.45], "roughness": 0.35, "metallic": 0.0},
        "why": "a retroreflective fabric's silver grey as it shows under light from beside the camera (about 45% "
               "reflectance), glossier than the cloth it is sewn on"},
}


def material_usda(surface, constants, maps):
    """One UsdPreviewSurface material named `surface` with the constants; with `maps`, the polyester's normal and
    ORM maps (as its own entry lays them, tiled three times over its texture coordinates)."""
    lines = []
    for name, value in constants.items():
        if isinstance(value, list):
            lines.append(f"        color3f inputs:{name} = ({', '.join(f'{number:g}' for number in value)})")
        else:
            lines.append(f"        float inputs:{name} = {value:g}")
    shaders = ""
    if maps:
        lines += [f"        normal3f inputs:normal.connect = </{surface}/normal.outputs:rgb>",
                  f"        float inputs:occlusion.connect = </{surface}/orm.outputs:r>",
                  f"        float inputs:roughness.connect = </{surface}/orm.outputs:g>"]
        shaders = (f'\n    def Shader "st"\n    {{\n        uniform token info:id = "UsdPrimvarReader_float2"\n'
                   f'        string inputs:varname = "st"\n        float2 outputs:result\n    }}\n\n'
                   f'    def Shader "mapping"\n    {{\n        uniform token info:id = "UsdTransform2d"\n'
                   f'        float2 inputs:in.connect = </{surface}/st.outputs:result>\n'
                   f'        float2 inputs:scale = (3, 3)\n        float2 outputs:result\n    }}\n\n'
                   f'    def Shader "normal"\n    {{\n        uniform token info:id = "UsdUVTexture"\n'
                   f'        float4 inputs:bias = (-1, -1, -1, 0)\n        asset inputs:file = @./normal.png@\n'
                   f'        float4 inputs:scale = (2, 2, 2, 1)\n        token inputs:sourceColorSpace = "raw"\n'
                   f'        float2 inputs:st.connect = </{surface}/mapping.outputs:result>\n'
                   f'        float3 outputs:rgb\n    }}\n\n'
                   f'    def Shader "orm"\n    {{\n        uniform token info:id = "UsdUVTexture"\n'
                   f'        asset inputs:file = @./orm.png@\n        token inputs:sourceColorSpace = "raw"\n'
                   f'        float2 inputs:st.connect = </{surface}/mapping.outputs:result>\n'
                   f'        float outputs:g\n        float outputs:r\n    }}\n')
    inputs = "\n".join(lines)
    return (f'#usda 1.0\n(\n    defaultPrim = "{surface}"\n)\n\ndef Material "{surface}"\n{{\n'
            f'    token outputs:surface.connect = </{surface}/surface.outputs:surface>\n\n'
            f'    def Shader "surface"\n    {{\n        uniform token info:id = "UsdPreviewSurface"\n{inputs}\n'
            f'        token outputs:surface\n    }}\n{shaders}}}\n')


def listed(surface, finish, own, polyester):
    """One finish's row of the take-in listing, its maps copied beside it from the fetched polyester entry."""
    files = {name: {"path": str(own / name), "from": f"score tools/characters/garments/finishes.py ({surface})"}
             for name in ("material.usda", "surface.json")}
    made_with = [{"what": "the finish's colour and settings, set by score for the garments (#225)", "source": "score"}]
    row = {"kind": "surface", "id": surface, "title": finish["title"], "files": files, "made_with": made_with,
           "tags": {"family": [finish["family"]], "use": ["garment"]}}
    if finish["maps"]:
        for name, source in MAPS_FROM.items():
            shutil.copyfile(pathlib.Path(polyester) / name, own / name)
            files[name] = {"path": str(own / name), "from": source}
        made_with.append({"what": "the m_opaque__fabric__polyester_yellow_a01 maps of "
                                  "consumable_air_filter_cylindrical_a01", "source": "nvidia_simready",
                          "carried": True})
        row["licence"] = NVIDIA_LICENCE
    return row


def written(folder, commit, polyester):
    """Every finish's files and the take-in listing under `folder`; the listing's path."""
    folder = pathlib.Path(folder)
    entries = []
    for surface, finish in FINISHES.items():
        own = folder / surface
        own.mkdir(parents=True, exist_ok=True)
        (own / "material.usda").write_text(material_usda(surface, finish["constants"], finish["maps"]))
        record = {"family": finish["family"], "constants": finish["constants"], "why": finish["why"],
                  "made_by": "score tools/characters/garments/finishes.py"}
        if finish["maps"]:
            record["maps"] = {"normal": "normal.png", "orm": "orm.png"}
        (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
        entries.append(listed(surface, finish, own, polyester))
    listing = folder / "take-in.json"
    listing.write_text(json.dumps({"world": "world1", "commit": commit,
                                   "taken_from": "the garments' finishes written by score's garment tools (#225, PRD "
                                                 "#223)", "entries": entries}, indent=1) + "\n")
    return listing


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2], sys.argv[3]))
