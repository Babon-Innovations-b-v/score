"""The strand hair's own finish (#223), written as a score_lib surface to take in: a hair fibre's pigment, roughness,
cuticle tilt and index, as Cycles' Principled Hair BSDF (Chiang et al. 2016) reads them. score_lib's hair surfaces
(hair_brown, hair_black) are flat colours made for a shell, with nothing a strand's scattering needs: one colour on
every strand through the BSDF's direct colouring read orange where light came through it and as a smooth helmet
(owner, 2026-11-25: "no way that hair looked good", "orange parting").

    python -m tools.characters.hair.finish <folder> <score commit>

Writes `<folder>/<id>/material.usda` (one UsdPreviewSurface, the fibre's mean colour for a reader that knows no hair)
and `surface.json` (the same constants and the `hair` block: melanin and its redness in Blender's 0..1 terms, roughness,
radial roughness, coat, index, the cuticle's tilt, the spread strand to strand and the tips' lightening), and
`<folder>/take-in.json`, the listing `score-lib take-in` reads. A reader that knows the block
(`../face/blender_face.strands_material`) draws strands with it.

The numbers and where they come from:
- index 1.55, longitudinal and azimuthal roughness 0.3 and the cuticle scales' tilt 2 degrees: pbrt-v3's hair material
  (Pharr's implementation of Chiang et al. 2016, src/materials/hair.cpp: eta 1.55, beta_m 0.3, beta_n 0.3, alpha 2),
  the values Marschner et al. 2003 measured on human hair fibres;
- the pigment: eumelanin 1.3, pbrt's brown (its notes: about 8 black, 1.3 brown, 0.3 blonde), and a little
  pheomelanin (0.05) for an ash, not a red, brown. Blender takes melanin m in 0..1 as the concentration -ln(1 - m) and
  splits it by its redness r (eumelanin (1 - r), pheomelanin r; Cycles kernel/svm/closure.h), so m = 1 - exp(-1.35),
  r = 0.05 / 1.35;
- coat 0: Blender's coat is a fur's (a shiny first bounce over the medulla); a human hair has none;
- the spread: each strand's melanin within 12 % either way (Blender's Random Color) and its roughness 15 % (Random
  Roughness), and the tips 12 % lighter than the roots (worn cuticle and sun), chosen by looking, not measured.
"""
import json
import math
import pathlib
import sys

EUMELANIN = 1.3
PHEOMELANIN = 0.05
FINISHES = {
    "hair_strands_ash_brown": {
        "title": "Hair strands, mid ash brown (Principled Hair)", "family": "hair",
        "constants": {"diffuseColor": [0.085, 0.056, 0.038], "roughness": 0.35, "metallic": 0.0, "ior": 1.55},
        "hair": {"melanin": round(1.0 - math.exp(-(EUMELANIN + PHEOMELANIN)), 4),
                 "redness": round(PHEOMELANIN / (EUMELANIN + PHEOMELANIN), 4),
                 "roughness": 0.3, "radial_roughness": 0.3, "coat": 0.0, "ior": 1.55, "offset_deg": 2.0,
                 "random_color": 0.12, "random_roughness": 0.15, "tip_lighter": 0.12},
        "why": "a human hair fibre for Cycles' Principled Hair BSDF: pbrt-v3's hair material (index 1.55, roughness "
               "0.3 both ways, cuticle tilt 2 degrees; Marschner et al. 2003's measured fibres) and its brown "
               "eumelanin (1.3) with a little pheomelanin (0.05) for an ash brown; no coat (that is a fur's); each "
               "strand's melanin and roughness varied and the tips lighter (#223, 2026-11-26: the hair read as a "
               "helmet with an orange parting)"},
}
READER_KEYS = ("hair",)


def material_usda(surface, constants):
    """One UsdPreviewSurface material named `surface` with the constants (the fibre's mean colour for a reader that
    knows no hair; the face's finishes write theirs the same way)."""
    lines = [f"        color3f inputs:{name} = ({', '.join(f'{number:g}' for number in value)})"
             if isinstance(value, list) else f"        float inputs:{name} = {value:g}"
             for name, value in constants.items()]
    return (f'#usda 1.0\n(\n    defaultPrim = "{surface}"\n)\n\ndef Material "{surface}"\n{{\n'
            f'    token outputs:surface.connect = </{surface}/surface.outputs:surface>\n\n'
            f'    def Shader "surface"\n    {{\n        uniform token info:id = "UsdPreviewSurface"\n'
            + "\n".join(lines) + '\n        token outputs:surface\n    }\n}\n')


def written(folder, commit):
    """Every finish's files and the take-in listing under `folder`; the listing's path."""
    folder = pathlib.Path(folder)
    entries = []
    for surface, finish in FINISHES.items():
        own = folder / surface
        own.mkdir(parents=True, exist_ok=True)
        (own / "material.usda").write_text(material_usda(surface, finish["constants"]))
        record = {"family": finish["family"], "constants": finish["constants"], "why": finish["why"],
                  **{key: finish[key] for key in READER_KEYS if key in finish},
                  "made_by": "score tools/characters/hair/finish.py"}
        (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
        entries.append({"kind": "surface", "id": surface, "title": finish["title"],
                        "files": {name: {"path": str(own / name), "from": f"score tools/characters/hair/finish.py "
                                                                           f"({surface})"}
                                  for name in ("material.usda", "surface.json")},
                        "made_with": [{"what": "the fibre's constants, set by score from pbrt-v3's hair material "
                                               "(Chiang et al. 2016) for strand hair (#223)", "source": "score"}],
                        "tags": {"family": [finish["family"]], "use": ["hair"]}})
    listing = folder / "take-in.json"
    listing.write_text(json.dumps({"world": "world1", "commit": commit,
                                   "taken_from": "the strand hair's finish written by score's hair tools (#223)",
                                   "entries": entries}, indent=1) + "\n")
    return listing


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2]))
