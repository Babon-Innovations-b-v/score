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
                        "constants": {"diffuseColor": [0.807, 0.515, 0.412], "roughness": 0.42,
                                      "metallic": 0.0, "ior": 1.4},
                        "subsurface": {"weight": 1.0, "radius_mm": [1.1, 0.42, 0.22], "anisotropy": 0.8,
                                       "ior": 1.4, "method": "RANDOM_WALK_SKIN"},
                        "detail": {"scan": {"depth_m": 0.00018, "roughness_spread": 0.12, "body": 0.6},
                                   "mottle": {"spacing_m": 0.03, "share": 0.18,
                                              "towards": [0.66, 0.36, 0.3]},
                                   "spots": [{"spacing_m": 0.007, "radius": 0.16, "density": 0.08, "share": 0.3,
                                              "towards": [0.48, 0.25, 0.14], "where": "flush"},
                                             {"spacing_m": 0.06, "radius": 0.022, "density": 0.06, "share": 0.8,
                                              "towards": [0.2, 0.1, 0.07]}]},
                        "regions": {"flush": {"share": 0.75, "towards": [0.62, 0.19, 0.2]},
                                    "thin": {"share": 0.3, "towards": [0.42, 0.3, 0.38]},
                                    "veins": {"spacing_m": 0.02, "width": 0.1, "share": 0.18,
                                              "towards": [0.3, 0.3, 0.45]},
                                    "lids": {"share": 0.25, "towards": [0.5, 0.34, 0.33]},
                                    "lips": {"share": 0.85, "towards": [0.42, 0.1, 0.11], "roughness": -0.08},
                                    "wet": {"share": 0.8, "towards": [0.6, 0.24, 0.23], "roughness": -0.34},
                                    "sheen": {"roughness": -0.1}},
                        "crevices": {"reach_m": 0.004, "share": 0.25, "towards": [0.32, 0.2, 0.18], "own": True},
                        "coat": {"weight": 0.15, "roughness": 0.35, "ior": 1.45},
                        "why": "a light skin's albedo (sRGB #E8BEAC, linear 0.81, 0.52, 0.41): the cockpit palette's "
                               "skin-light token (world1) was more orange (red over blue 2.7, a light skin's is about "
                               "2) and every shadowed hollow, the eye sockets most, went orange-brown in a real sky "
                               "(red over blue 2.2 against the forehead's 1.2, round 2, 2026-11-26); the light under "
                               "it red-led, red reaching 1.1 mm (forward scattering 0.8, index 1.4): Jensen et al. "
                               "2001's measured paths (3.67, 1.37, 0.68 mm) washed every crease out and lit the "
                               "nostrils orange, wax (owner, 2026-11-25), and 2 mm still lit the thin lids and the "
                               "nostrils' rims orange in a real sky (photoreal round 1, 2026-11-26); its pores, fine creases, capillaries and speckle photographed: a 41 mm square of "
                               "a real forehead (skin_scan.py) repeated over the whole body, its colour multiplying "
                               "the base, its relief 0.18 mm from its lowest pit to its highest rise on the forehead "
                               "and varying by region as a face's does (the face's `relief` channel: deeper on the "
                               "nose and the cheeks, finer on the lids, under the eyes and on the lips; `body` 0.6 of "
                               "it on the neck, arms and hands): one 0.3 mm relief everywhere read as stucco (round "
                               "1); its pits rougher (procedural pores and noise "
                               "read as wax and plastic, owner 2026-11-25 and 2026-11-26: 'photorealism is the goal'), "
                               "blotches wider than the square as a faint noise, a few freckles on the cheeks and "
                               "nose and a few moles anywhere (`spots`); a flush, crimson rather than orange, on the "
                               "cheeks, nose, chin and ears, a bluish cast and veins where the skin is thin (under the "
                               "eyes), the lids a little darker and greyer, the waterline and the caruncle a wet "
                               "pink, the T-zone a little glossier, the lips a deeper rose with a defined border and a "
                               "little glossier (lips read colourless with a wet "
                               "blob of highlight, owner 2026-11-25), folds and nostrils a little darker by "
                               "the skin's own closeness only (`own`: the brows, lashes and hair over it toned the "
                               "lids and the parting orange, round 1), and a thin oily coat (#223, "
                               "2026-11-25: the skin read as wax)"},
    "face_skin_dark": {"title": "Skin, dark, photographed detail, light through it", "family": "skin",
                       "constants": {"diffuseColor": [0.20155625, 0.08228270, 0.04091520], "roughness": 0.4,
                                     "metallic": 0.0, "ior": 1.4},
                       "subsurface": {"weight": 1.0, "radius_mm": [0.9, 0.3, 0.15], "anisotropy": 0.8,
                                      "ior": 1.4, "method": "RANDOM_WALK_SKIN"},
                       "detail": {"scan": {"depth_m": 0.00018, "roughness_spread": 0.12, "body": 0.6},
                                  "mottle": {"spacing_m": 0.03, "share": 0.15,
                                             "towards": [0.15, 0.06, 0.03]},
                                  "spots": [{"spacing_m": 0.06, "radius": 0.022, "density": 0.05, "share": 0.7,
                                             "towards": [0.06, 0.03, 0.02]}]},
                       "regions": {"flush": {"share": 0.3, "towards": [0.22, 0.06, 0.05]},
                                   "thin": {"share": 0.25, "towards": [0.12, 0.08, 0.09]},
                                   "veins": {"spacing_m": 0.02, "width": 0.04, "share": 0.1,
                                             "towards": [0.1, 0.07, 0.09]},
                                   "lids": {"share": 0.35, "towards": [0.1, 0.045, 0.03]},
                                   "lips": {"share": 0.6, "towards": [0.11, 0.035, 0.035], "roughness": -0.08},
                                   "wet": {"share": 0.75, "towards": [0.4, 0.14, 0.13], "roughness": -0.32},
                                   "sheen": {"roughness": -0.1}},
                       "crevices": {"reach_m": 0.004, "share": 0.4, "towards": [0.06, 0.025, 0.018], "own": True},
                       "coat": {"weight": 0.18, "roughness": 0.33, "ior": 1.45},
                       "why": "the cockpit palette's skin-dark token (#7c5139, design/tokens/tokens.json) as the base, "
                              "for the people whose skin is dark (man_coat; his plain skin_dark had no detail, no "
                              "light through it and no regions, a flat body under a detailed face, 2026-11-26); the "
                              "same photographed detail and regional relief as face_skin_light (skin_scan.py's tiles "
                              "multiply the base); melanin takes most of the light under the skin, so the scatter is "
                              "shorter (0.9 mm red) and the flush, the thin skin's bluish cast and the veins show "
                              "less, the lids darker, the waterline a wet pink, a few dark moles and no freckles, "
                              "the lips a deeper brown-rose, folds darker by the skin's own closeness, a little more "
                              "sheen from the oil's coat and the T-zone's (#223)"},
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
                    "constants": {"diffuseColor": [0.68, 0.58, 0.5], "roughness": 0.3, "metallic": 0.0},
                    "veins": {"spacing_m": 0.004, "width": 0.05, "share": 0.5, "towards": [0.45, 0.08, 0.06],
                              "from_uv": 0.17, "to_uv": 0.32},
                    "why": "an eye's white is not white: a warm off-white, fine red vessels growing towards the "
                           "corners (ICT-FaceKit's eyeball UV, out from the iris), shaded by the lids' own shadow "
                           "(an ambient occlusion tone read the clear shell 0.1 mm over it as a crevice and drew the "
                           "white in grey rings, round 1 and 2, 2026-11-26) (#223, 2026-11-25: the eyes read glassy "
                           "and dead)"},
    "face_eye_film": {"title": "Tear film over the eye's white, thin", "family": "eye",
                      "constants": {"diffuseColor": [1.0, 1.0, 1.0], "roughness": 0.04, "metallic": 0.0, "ior": 1.336},
                      "transmission": {"weight": 1.0, "thin": True},
                      "why": "the tear film over the eye's white: a gloss at water's index, a little soft, too thin "
                             "to bend light, so the white shows through it unmoved (as the cornea's glass, its steep "
                             "edge at the limbus bent the white into bright streaks beside the iris, round 1, "
                             "2026-11-26) (#223)"},
    "face_cornea": {"title": "Cornea and tear film, clear", "family": "eye",
                    "constants": {"diffuseColor": [1.0, 1.0, 1.0], "roughness": 0.0, "metallic": 0.0, "ior": 1.376},
                    "transmission": 1.0,
                    "why": "the cornea's clear dome and the tear film over the eye's white: clear glass with the "
                           "cornea's index (1.376, Gullstrand's eye), smooth, so the sky shows in it as a highlight; "
                           "shadows pass through it as through the real eye's (#223)"},
    "face_pupil": {"title": "Pupil (constant)", "family": "eye",
                   "constants": {"diffuseColor": [0.005, 0.005, 0.005], "roughness": 0.15, "metallic": 0.0},
                   "why": "the pupil, near black under the cornea's gloss"},
    "face_brow_brown": {"title": "Brows, dark brown (constant)", "family": "hair",
                        "constants": {"diffuseColor": [0.06, 0.036, 0.022], "roughness": 0.45, "metallic": 0.0},
                        "hair": {"melanin": 0.8713, "redness": 0.0244, "roughness": 0.3, "radial_roughness": 0.3,
                                 "coat": 0.0, "ior": 1.55, "offset_deg": 2.0, "random_color": 0.15,
                                 "random_roughness": 0.15, "tip_lighter": 0.15},
                        "why": "brow hairs a shade lighter and warmer than the lashes, a dark brown as a brunette's "
                               "brows are (eumelanin 2.0 with pheomelanin 0.05 in the strand route's terms, "
                               "../hair/finish.py; a colour drawn by the direct-colour hair shader read pale grey "
                               "under the sky, round 2) (one near-black lash colour drew the brows as dark blocks, round 1, "
                               "2026-11-26) (#223)"},
    "face_lash_dark": {"title": "Lashes, near black", "family": "hair",
                       "constants": {"diffuseColor": [0.03, 0.02, 0.015], "roughness": 0.45, "metallic": 0.0},
                       "hair": {"melanin": 0.9997, "redness": 0.0062, "roughness": 0.25, "radial_roughness": 0.3,
                                "coat": 0.0, "ior": 1.55, "offset_deg": 2.0, "random_color": 0.05,
                                "random_roughness": 0.1, "tip_lighter": 0.1},
                       "why": "lashes near black: eumelanin 8 (pbrt's black) with a trace of pheomelanin in the "
                              "strand route's terms (../hair/finish.py), lighter towards the tips; a dark colour drawn "
                              "by the direct-colour hair shader read pale grey under the sky (round 2, 2026-11-26)"},
    "face_tear_film": {"title": "Tear film (constant)", "family": "eye",
                       "constants": {"diffuseColor": [1.0, 1.0, 1.0], "roughness": 0.02, "metallic": 0.0,
                                     "opacity": 0.03, "ior": 1.336},
                       "why": "the tear film along the lids: clear, with water's index of refraction"},
}


# A finish whose detail is the photographed skin carries skin_scan's tiles as its own files, under the scan's licence.
SCANNED = ("face_skin_light", "face_skin_dark")
READER_KEYS = ("subsurface", "detail", "regions", "crevices", "coat", "veins", "fibres", "transmission", "hair")


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
