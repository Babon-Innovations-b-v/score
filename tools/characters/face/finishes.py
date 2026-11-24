"""The face's own finishes (#226), written as score_lib surfaces to take in: skin, the mouth's inside, the iris, the
pupil, the lashes and the tear film. score_lib holds no live finish for any of them (its skin and hair surfaces were
withdrawn with the old library); the teeth and the eyes' whites wear its glossy white ceramic.

    python finishes.py <folder> <score commit>

Writes each finish's `material.usda` (one UsdPreviewSurface, its constants below) and `surface.json` (the same
constants, its family and why) under `<folder>/<id>/`, and `<folder>/take-in.json`, the listing `score-lib take-in`
reads. Colours are linear albedo: the skin the cockpit palette's skin token (world1), the rest measured ranges for
each tissue (an iris's dark brown, a pupil near black, a wet mucosa's red, the tear film clear with water's IOR).
No subsurface: UsdPreviewSurface has none, so the skin's light through it waits for a skin recipe (#223).
"""
import json
import pathlib
import sys

FINISHES = {
    "face_skin_light": {"title": "Face skin, light (constant)", "family": "skin",
                        "constants": {"diffuseColor": [0.76815116, 0.4507858, 0.28314874], "roughness": 0.5,
                                      "metallic": 0.0},
                        "why": "the cockpit palette's skin-light token (world1), the officer's place"},
    "face_mouth_inside": {"title": "Mouth inside, gums and tongue (constant)", "family": "skin",
                          "constants": {"diffuseColor": [0.35, 0.09, 0.08], "roughness": 0.3, "metallic": 0.0},
                          "why": "a wet mucosa's red, glossier than the skin"},
    "face_iris_brown": {"title": "Iris, dark brown (constant)", "family": "eye",
                        "constants": {"diffuseColor": [0.1, 0.05, 0.025], "roughness": 0.3, "metallic": 0.0},
                        "why": "a dark brown iris"},
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
                  "made_by": "score tools/characters/face/finishes.py"}
        (own / "surface.json").write_text(json.dumps(record, indent=2) + "\n")
        entries.append({"kind": "surface", "id": surface, "title": finish["title"],
                        "files": {name: {"path": str(own / name), "from": f"score tools/characters/face/finishes.py "
                                                                           f"({surface})"}
                                  for name in ("material.usda", "surface.json")},
                        "made_with": [{"what": "the finish's constants, set by score for the face (#226)",
                                       "source": "score"}],
                        "tags": {"family": [finish["family"]], "use": ["face"]}})
    listing = folder / "take-in.json"
    listing.write_text(json.dumps({"world": "world1", "commit": commit,
                                   "taken_from": "the face's finishes written by score's face tools (#226, PRD #223)",
                                   "entries": entries}, indent=1) + "\n")
    return listing


if __name__ == "__main__":
    print(written(sys.argv[1], sys.argv[2]))
