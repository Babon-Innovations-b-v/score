"""The face's own finishes (#226), written as score_lib surfaces to take in: skin, the mouth's inside, the eye's white,
iris, pupil and cornea, the lashes and the tear film. score_lib holds no live finish for any of them (its skin and hair
surfaces were withdrawn with the old library); the teeth wear its glossy white ceramic.

    python finishes.py <folder> <score commit>

Writes each finish's `material.usda` (one UsdPreviewSurface, its constants below) and `surface.json` (the same
constants, its family and why) under `<folder>/<id>/`, and `<folder>/take-in.json`, the listing `score-lib take-in`
reads. Colours are linear albedo: the skin the cockpit palette's skin token (world1), the rest measured ranges for
each tissue (an iris's dark brown, a pupil near black, a wet mucosa's red, the tear film clear with water's IOR).
UsdPreviewSurface has no subsurface, tiled detail, clear coat or transmission, so a record carries them beside its
constants (`subsurface`: weight, mean free paths in mm, anisotropy, index, method; `detail`: the photographed
skin's tiles (`scan`, skin_scan.py: its files, its size, its relief's depth and the gloss's spread, the tiles the
entry's own files under the scan's CC BY 3.0) and blotches wider than a tile (`mottle`); `regions`: the tone each
of the skin's regions (face.tones: the flush, the thin bluish skin with its veins, the lips) is moved towards and by how
much; `crevices`: the darker, redder tone in folds and holes such as the nostrils, by how near other surfaces close
round a point; `coat`: the skin's oil; `veins`, `fibres`: the eye white's vessels and the iris's fibres and dark edge
on the eyeball's UV; `transmission`: the cornea's clear glass); a reader that knows them (blender_face.library_material)
lays them on the imported material, any other reads the constants (#223).
"""
import json
import pathlib
import sys

import skin_scan

FINISHES = {
    "face_skin_light": {"title": "Skin, light, photographed detail, light through it", "family": "skin",
                        "constants": {"diffuseColor": [0.76815116, 0.4507858, 0.28314874], "roughness": 0.42,
                                      "metallic": 0.0, "ior": 1.4},
                        "subsurface": {"weight": 1.0, "radius_mm": [2.0, 0.4, 0.2], "anisotropy": 0.8,
                                       "ior": 1.4, "method": "RANDOM_WALK_SKIN"},
                        "detail": {"scan": {"depth_m": 0.0003, "roughness_spread": 0.12},
                                   "mottle": {"spacing_m": 0.03, "share": 0.12,
                                              "towards": [0.62, 0.3, 0.2]}},
                        "regions": {"flush": {"share": 0.55, "towards": [0.6, 0.2, 0.15]},
                                    "thin": {"share": 0.3, "towards": [0.42, 0.32, 0.4]},
                                    "veins": {"spacing_m": 0.02, "width": 0.04, "share": 0.35,
                                              "towards": [0.3, 0.3, 0.45]},
                                    "lips": {"share": 0.85, "towards": [0.4, 0.09, 0.09], "roughness": -0.08}},
                        "crevices": {"reach_m": 0.006, "share": 0.6, "towards": [0.25, 0.07, 0.05]},
                        "coat": {"weight": 0.15, "roughness": 0.35, "ior": 1.45},
                        "why": "the cockpit palette's skin-light token (world1), the officer's place; the light under "
                               "it red-led as Blender's own skin default (red 1, green 0.2, blue 0.1), red reaching 2 "
                               "mm (forward scattering 0.8, index 1.4): Jensen et al. 2001's measured paths (3.67, "
                               "1.37, 0.68 mm) washed every crease out and lit the nostrils orange, wax (owner, "
                               "2026-11-25); its pores, fine creases, capillaries and speckle photographed: a 41 mm square of "
                               "a real forehead (skin_scan.py) repeated over the whole body, its colour multiplying "
                               "the base, its relief 0.3 mm from its lowest pit to its highest rise (a pore's wall as steep as a real one's; 0.12 mm left the skin smooth close up, 0.4 mm read as orange peel) and its pits rougher (procedural pores and noise "
                               "read as wax and plastic, owner 2026-11-25 and 2026-11-26: 'photorealism is the goal'), "
                               "blotches wider than the square as a faint noise; a flush on the "
                               "cheeks, nose, chin and ears, a bluish cast and veins where the skin is thin (under the "
                               "eyes), the lips a deeper rose and a little glossier (lips read colourless with a wet "
                               "blob of highlight, owner 2026-11-25), folds and nostrils darker and redder, and a thin oily coat (#223, "
                               "2026-11-25: the skin read as wax)"},
    "face_mouth_inside": {"title": "Mouth inside, gums and tongue (constant)", "family": "skin",
                          "constants": {"diffuseColor": [0.35, 0.09, 0.08], "roughness": 0.3, "metallic": 0.0},
                          "why": "a wet mucosa's red, glossier than the skin"},
    "face_iris_brown": {"title": "Iris, dark brown, with its fibres and dark edge", "family": "eye",
                        "constants": {"diffuseColor": [0.1, 0.05, 0.025], "roughness": 0.3, "metallic": 0.0},
                        "fibres": {"iris_uv": 0.125, "count": 70, "share": 0.45, "towards": [0.24, 0.14, 0.07],
                                   "edge_from": 0.82, "edge_share": 0.75, "edge_towards": [0.02, 0.012, 0.008]},
                        "why": "a dark brown iris, its radial fibres lighter amber and a darker ring at its edge (the "
                               "limbal ring); on ICT-FaceKit's eyeball UV, where the iris is the ring 0.125 out (#223, "
                               "2026-11-25: the eyes read glassy and dead)"},
    "face_sclera": {"title": "Eye white, with vessels", "family": "eye",
                    "constants": {"diffuseColor": [0.7, 0.62, 0.56], "roughness": 0.3, "metallic": 0.0},
                    "veins": {"spacing_m": 0.004, "width": 0.05, "share": 0.5, "towards": [0.45, 0.08, 0.06],
                              "from_uv": 0.17, "to_uv": 0.32},
                    "crevices": {"reach_m": 0.004, "share": 0.7, "towards": [0.12, 0.08, 0.07]},
                    "why": "an eye's white is not white: a warm off-white, fine red vessels growing towards the "
                           "corners (ICT-FaceKit's eyeball UV, out from the iris), darker where the lids close over "
                           "it (#223, 2026-11-25: the eyes read glassy and dead)"},
    "face_cornea": {"title": "Cornea and tear film, clear", "family": "eye",
                    "constants": {"diffuseColor": [1.0, 1.0, 1.0], "roughness": 0.0, "metallic": 0.0, "ior": 1.376},
                    "transmission": 1.0,
                    "why": "the cornea's clear dome and the tear film over the eye's white: clear glass with the "
                           "cornea's index (1.376, Gullstrand's eye), smooth, so the sky shows in it as a highlight; "
                           "shadows pass through it as through the real eye's (#223)"},
    "face_pupil": {"title": "Pupil (constant)", "family": "eye",
                   "constants": {"diffuseColor": [0.005, 0.005, 0.005], "roughness": 0.15, "metallic": 0.0},
                   "why": "the pupil, near black under the cornea's gloss"},
    "face_lash_dark": {"title": "Lashes, dark brown (constant)", "family": "hair",
                       "constants": {"diffuseColor": [0.03, 0.02, 0.015], "roughness": 0.45, "metallic": 0.0},
                       "why": "dark brown lashes"},
    "face_tear_film": {"title": "Tear film (constant)", "family": "eye",
                       "constants": {"diffuseColor": [1.0, 1.0, 1.0], "roughness": 0.02, "metallic": 0.0,
                                     "opacity": 0.03, "ior": 1.336},
                       "why": "the tear film along the lids: clear, with water's index of refraction"},
}


# A finish whose detail is the photographed skin carries skin_scan's tiles as its own files, under the scan's licence.
SCANNED = ("face_skin_light",)
READER_KEYS = ("subsurface", "detail", "regions", "crevices", "coat", "veins", "fibres", "transmission")


def material_usda(surface, constants):
    """One UsdPreviewSurface material named `surface` with the constants."""
    lines = []
    for name, value in constants.items():
        if isinstance(value, list):
            lines.append(f"        color3f inputs:{name} = ({', '.join(f'{number:g}' for number in value)})")
        else:
            lines.append(f"        float inputs:{name} = {value:g}")
    inputs = "\n".join(lines)
    return (f'#usda 1.0\n(\n    defaultPrim = "{surface}"\n)\n\ndef Material "{surface}"\n{{\n'
            f'    token outputs:surface.connect = </{surface}/surface.outputs:surface>\n\n'
            f'    def Shader "surface"\n    {{\n        uniform token info:id = "UsdPreviewSurface"\n{inputs}\n'
            f'        token outputs:surface\n    }}\n}}\n')


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
                  "made_by": "score tools/characters/face/finishes.py"}
        files = {name: {"path": str(own / name), "from": f"score tools/characters/face/finishes.py ({surface})"}
                 for name in ("material.usda", "surface.json")}
        made_with = [{"what": "the finish's constants, set by score for the face (#226)", "source": "score"}]
        entry = {"kind": "surface", "id": surface, "title": finish["title"]}
        if surface in SCANNED:
            scan = skin_scan.tiles(own)
            record["detail"] = {**record["detail"], "scan": {**scan, **record["detail"]["scan"]}}
            for name in (scan["colour"], scan["height"]):
                files[name] = {"path": str(own / name), "from": f"score tools/characters/face/skin_scan.py from "
                                                                f"{skin_scan.SOURCE}"}
            made_with.append({"what": "the skin detail tiles, cut from the scan's albedo", "source":
                              skin_scan.SOURCE_ID, "carried": True})
            entry["licence"] = {"id": "CC-BY-3.0", "source": skin_scan.SOURCE_ID, "credit": skin_scan.CREDIT,
                                "url": skin_scan.LICENCE_URL}
        (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
        entries.append({**entry, "files": files, "made_with": made_with,
                        "tags": {"family": [finish["family"]], "use": ["face"]}})
    listing = folder / "take-in.json"
    listing.write_text(json.dumps({"world": "world1", "commit": commit,
                                   "taken_from": "the face's finishes written by score's face tools (#226, PRD #223)",
                                   "entries": entries}, indent=1) + "\n")
    return listing


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2]))
