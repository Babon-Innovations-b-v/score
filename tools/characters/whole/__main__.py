"""python -m tools.characters.whole <outfit.json> --dressed <garments run folder> --clip <clip> --face <face.npz>
--face-body <body.npz> --style <its hair style json> --frame <clip frame> --name <pose> --out
<folder>: the whole person (the package docstring) at one clip frame of a dressed run (`python -m
tools.characters.garments ... --face`), drawn from the front, the back, both sides and three quarters (render.py,
Blender through this PC's card queue); its measures and faults in <out>/<pose>-measures.json, the run failing on a
fault after its pictures."""
import argparse
import json
import os
import pathlib
import subprocess

import numpy as np
from scipy.spatial import cKDTree

from tools.characters import garments, whole
from tools.characters.whole import hair as strands
from tools.characters.whole import jewellery

VIEWS = {"front": 0.0, "three_quarter": 35.0, "left": 90.0, "back": 180.0, "right": 270.0}
FACE_PIECES = ("eyes", "teeth", "mouth", "tears", "brows", "lashes")
SETTING = {"floor": "simready_m_opaque_concrete_bare_c01_3a571927",  # the daylight setting's (render.py): NVIDIA
           "wall": "simready_m_opaque_concrete_plain_wall_a01_8c6d57b1"}  # SimReady concretes, CC BY 4.0
THICK_M = garments.THICKNESS_M
HEAD_ABOVE_M = 0.25  # the skin this far under the Head joint and up is what the hair is kept off
BROW_REACH_M = 0.012  # a hair point this near a brow hair keeps clear of the brows
CARD_GB = 6


def usd_pieces(usd, frame):
    """Every mesh of the dressed run's outfit.usda at `frame`, world (y up, lifted by its soles): {name: piece}."""
    from pxr import Usd, UsdGeom, UsdShade
    stage = Usd.Stage.Open(str(usd))
    cache = UsdGeom.XformCache(frame)
    found = {}
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        points = np.asarray(mesh.GetPointsAttr().Get(frame), dtype=float)
        matrix = np.asarray(cache.GetLocalToWorldTransform(prim), dtype=float)
        points = points @ matrix[:3, :3] + matrix[3, :3]
        faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3)
        material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
        piece = {"points": points, "triangles": faces, "surfaces": [material.GetPrim().GetName()],
                 "finish": np.zeros(len(faces), np.int64)}
        for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):  # a garment's bands: their triangles in their own finish
            bound = UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0]
            piece["finish"][np.asarray(subset.GetIndicesAttr().Get(), np.int64)] = len(piece["surfaces"])
            piece["surfaces"].append(bound.GetPrim().GetName())
        primvar = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
        if primvar and primvar.HasValue():
            st = np.asarray(primvar.Get(), dtype=float)
            piece["uv"] = st.reshape(-1, 3, 2) if primvar.GetInterpolation() == "faceVarying" else st[faces]
        name = prim.GetName() if prim.GetParent().GetName() in ("Garments", "Outfit", "Accessories") else \
            f"{prim.GetParent().GetName()}_{prim.GetName()}"
        found["skin" if name == "Body" else name] = piece
    return found


def lift_of(usd):
    """The run's lift (/Outfit's translate, m): the soles' depth under the bare feet."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(usd))
    return float(np.asarray(UsdGeom.XformCache(0).GetLocalToWorldTransform(stage.GetPrimAtPath("/Outfit")))[3, 1])


def face_pieces(face, skin, moves, lift):
    """The face's other pieces at the frame: carried from the face's frame onto the mean's (the skin's scale and
    shift), then by the head."""
    found = {}
    for name in FACE_PIECES:
        points = np.asarray(face[f"{name}.points"], float) * skin["scale"] + skin["shift"]
        piece = {"points": whole.head_carried(points, moves[None])[0] + [0.0, lift, 0.0],
                 "surfaces": [str(item) for item in face[f"{name}.surfaces"]]}
        for field in ("triangles", "finish", "uv", "counts", "radius"):
            if f"{name}.{field}" in face:
                piece[field] = np.asarray(face[f"{name}.{field}"])
        if "radius" in piece:
            piece["radius"] = piece["radius"] * skin["scale"]
        found[name] = piece
    return found


def head_region(body, skin_points, head_y):
    """The skin's triangles from HEAD_ABOVE_M under the Head joint up: what the hair is kept off."""
    faces = np.asarray(body["faces"])
    return faces[(skin_points[faces][..., 1] > head_y - HEAD_ABOVE_M).all(axis=1)]


def hair_laid(groom, body, frame, skin_points, brows, head_y):
    """The hair combed at the build's bind (`hair.combed`) at `frame` (an index of the body's `worlds`): carried by
    the head, every point kept HAIR_OFF_M out of the skin and those near a brow hair BROW_CLEAR_M past the brows;
    (points, the most a point was short of its clearance then, m)."""
    points = groom[1]
    head = [str(name) for name in body["names"]].index("Head")
    move = np.asarray(body["worlds"])[frame, head] @ np.linalg.inv(np.asarray(body["joints"])[head])
    points = points @ move[:3, :3].T + move[:3, 3]
    region = head_region(body, skin_points, head_y)
    clear = np.full(len(points), whole.HAIR_OFF_M)
    brow_points = brows["points"]
    distance, nearest = cKDTree(brow_points).query(points, distance_upper_bound=BROW_REACH_M)
    near = np.isfinite(distance)
    brow_tree = cKDTree(skin_points)
    brow_off = brow_tree.query(brow_points)[0]
    clear[near] = brow_off[nearest[near]] + whole.BROW_CLEAR_M
    close = cKDTree(skin_points).query(points, distance_upper_bound=0.03)[0] < 0.03
    moved, short = whole.pushed_out(points[close], skin_points, region, clear[close])
    points = points.copy()
    points[close] = moved
    return points, short


def joint_at(body, name):
    """A joint's place at the build's bind."""
    return np.asarray(body["joints"])[[str(item) for item in body["names"]].index(name), :3, 3]


def eyes_at(face, skin, body):
    """The two eyeballs' middles at the build's bind (left first): the face's eyes laid as its other pieces are."""
    points = np.asarray(face["eyes.points"], float) * skin["scale"] + skin["shift"]
    head = [str(item) for item in body["names"]].index("Head")
    move = np.asarray(body["joints"])[head] @ np.linalg.inv(whole.clips_bind()[head])
    points = points @ move[:3, :3].T + move[:3, 3]
    middle = points[:, 0].mean()
    return np.array([points[points[:, 0] > middle].mean(axis=0), points[points[:, 0] <= middle].mean(axis=0)])


def jewels(outfit, body, face, skin, start, count, frame):
    """The outfit's jewellery (its `jewellery`, each a surface) made at the build's bind and carried over the clip:
    {name: piece at `frame`} and the measures."""
    chosen = outfit.get("jewellery", {})
    if not chosen:
        return {}, {}
    bind, faces = np.asarray(body["bind"]), np.asarray(body["faces"])
    names = [str(item) for item in body["names"]]
    made = {}
    if "earrings" in chosen:
        for side, (points, triangles, st, lobe) in jewellery.earrings(bind, eyes_at(face, skin, body)).items():
            made[f"{side}_earring"] = ("Head", points, triangles, st, chosen["earrings"], lobe)
    if "necklace" in chosen:
        made["necklace"] = ("skin", *jewellery.necklace(bind, faces, joint_at(body, "Neck1"),
                                                         joint_at(body, "Chest")), chosen["necklace"], None)
    if "watch" in chosen:
        lateral = np.array([1.0, 0.0, 0.0])
        for part, (points, triangles, st) in jewellery.watch(bind, joint_at(body, "LeftForeArm"),
                                                              joint_at(body, "LeftHand"), lateral).items():
            made[f"watch_{part}"] = ("LeftForeArm", points, triangles, st, chosen["watch"][part], None)
    if "rings" in chosen:
        for hand, finger in jewellery.RINGS:
            carrier = f"{hand}Hand"
            hand_points = bind[np.asarray(body["weights"])[:, names.index(carrier)] > whole.SEGMENT_WEIGHT]
            made[f"{hand.lower()}_ring"] = (carrier, *jewellery.ring(bind, faces, hand_points,
                                                                     joint_at(body, carrier), finger),
                                            chosen["rings"], None)
    frames = np.arange(start, start + count)
    skin_frames = np.asarray(body["frames"])[start:start + count]
    found = {"into the skin mm": {}, "hoop top off the lobe mm": {}}
    pieces = {}
    for name, (joint, points, triangles, st, surface, lobe) in made.items():
        if joint == "skin":  # lying on the skin over several joints (the neck, the shoulders): carried by it
            carried = whole.skin_carried(whole.skin_bound(points, bind, faces), skin_frames, faces)
        else:
            carried = jewellery.carried(points, joint, body, frames)
        if lobe is None:
            found["into the skin mm"][name] = round(jewellery.deepest(carried[::5], skin_frames[::5], faces)
                                                    * 1000.0, 2)
        else:
            top = carried[:, carried[0][:, 1].argmax()]
            lobe_at = np.asarray(body["frames"])[start:start + count][:, np.linalg.norm(bind - lobe, axis=1).argmin()]
            found["hoop top off the lobe mm"][name] = round(float(np.linalg.norm(top - lobe_at, axis=1).max()
                                                                  - jewellery.EARRING["wire"]) * 1000.0, 2)
        pieces[name] = {"points": carried[frame - start], "triangles": triangles, "uv": st[triangles],
                        "surfaces": [surface["name"]], "finish": np.zeros(len(triangles), np.int64)}
    found["faults"] = jewellery.faults(found)
    return pieces, found


def scene_file(pieces, name, path, cloth):
    """The pieces in blender_face's format, with the views, the pose's name and the pieces that are `cloth`."""
    arrays = {"pieces": np.array(list(pieces)), "views": np.array(json.dumps(VIEWS)), "name": np.array(name),
              "subdivided": np.array(True), "thick": np.array(THICK_M), "cloth": np.array(cloth),
              "setting": np.array(json.dumps(SETTING))}
    for piece_name, piece in pieces.items():
        arrays[f"{piece_name}.surfaces"] = np.array(piece["surfaces"])
        for field in ("points", "triangles", "finish", "uv", "counts", "radius"):
            if field in piece:
                arrays[f"{piece_name}.{field}"] = np.asarray(piece[field])
    np.savez_compressed(path, **arrays)
    return path


def fetched(pieces, out):
    """Every library surface the pieces wear, and the setting's, fetched from score_lib into `out`/library."""
    from tools.characters.garments.__main__ import SCORE_LIB
    names = sorted({surface for piece in pieces.values() for surface in piece["surfaces"]}
                   | set(SETTING.values()))
    folder = out / "library"
    subprocess.run([str(SCORE_LIB / ".venv/bin/score-lib"), "--root", str(SCORE_LIB), "fetch",
                    *[f"surface/{name}@1" for name in names],
                    "--into", str(folder)], check=True, cwd=SCORE_LIB, stdout=subprocess.DEVNULL)
    return folder / "score_lib"


def drawn(scene, library, out):
    """The views drawn by Blender on this PC's card through the card queue."""
    from tools.characters.garments.__main__ import BLENDER, BLENDER_LIBS
    command = ["python3", str(garments.CARD_QUEUE), "run", "--job", "whole-person", "--card-gb", str(CARD_GB),
               "--priority", "other", "--", str(BLENDER), "-b", "--factory-startup", "-P",
               str(pathlib.Path(__file__).with_name("render.py")), "--", str(scene), str(library), str(out)]
    subprocess.run(command, check=True, env={**os.environ, "LD_LIBRARY_PATH": str(BLENDER_LIBS),
                                             "FARM_CYCLES_GPU": "1"})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("outfit")
    parser.add_argument("--dressed", required=True)
    parser.add_argument("--clip", default="walking")
    parser.add_argument("--face", required=True)
    parser.add_argument("--face-body", required=True)
    parser.add_argument("--style", required=True, help="the hair's style (data/people/hair/<look>.json)")
    parser.add_argument("--frame", type=int, default=0, help="the clip frame drawn")
    parser.add_argument("--name", required=True)
    parser.add_argument("--out", required=True)
    given = parser.parse_args()
    outfit = json.loads(pathlib.Path(given.outfit).read_text())
    out = pathlib.Path(given.out)
    out.mkdir(parents=True, exist_ok=True)
    face, face_body = dict(np.load(given.face)), dict(np.load(given.face_body))
    body = garments.built_body(outfit["look"], given.clip, outfit.get("body"),
                               {"face": given.face, "body": given.face_body})
    skin = whole.carried_skin(face, face_body, dict(np.load(garments.CLIPS)), np.asarray(body["joints"]))
    usd = pathlib.Path(given.dressed) / "outfit.usda"
    lift = lift_of(usd)
    start = int(body["clip_start"])
    garment_names = [garment["name"] for garment in outfit["garments"]]
    count = len(np.load(pathlib.Path(given.dressed) / "drape.npz")[garment_names[0]])
    at = start + given.frame
    pieces = usd_pieces(usd, given.frame)
    pieces["skin"]["triangles"] = np.asarray(face["skin.triangles"], np.int64)
    pieces["skin"]["surfaces"] = [outfit["body surface"]["name"]]
    names = [str(name) for name in body["names"]]
    head = names.index("Head")
    moves = np.asarray(body["worlds"])[at, head] @ np.linalg.inv(np.asarray(whole.clips_bind())[head])
    pieces.update(face_pieces(face, skin, moves, lift))
    skin_points = np.asarray(body["frames"])[at]
    style = json.loads(pathlib.Path(given.style).read_text())
    eyes = eyes_at(face, skin, body)
    groom = strands.combed(np.asarray(body["bind"]), np.asarray(body["faces"]), eyes, style)
    hair_found = strands.measured(*groom[:2], np.asarray(body["bind"]), np.asarray(body["faces"]), eyes)
    brows = {"points": pieces["brows"]["points"] - [0.0, lift, 0.0]}
    hair, short = hair_laid(groom, body, at, skin_points, brows, float(np.asarray(body["worlds"])[at, head, 1, 3]))
    pieces["hair"] = {"counts": groom[0], "points": hair + [0.0, lift, 0.0], "radius": groom[2],
                      "surfaces": [style["library"]]}
    worn, found = jewels(outfit, body, face, skin, start, count, at)
    for name, piece in worn.items():
        piece["points"] = piece["points"] + [0.0, lift, 0.0]
    pieces.update(worn)
    measures = {"skin off its low body mm": {"most": round(float(skin["off"].max()) * 1000.0, 1),
                                              "99th": round(float(np.percentile(skin["off"], 99)) * 1000.0, 1)},
                "scale": round(skin["scale"], 5), "hair moved out most mm": round(short * 1000.0, 2),
                "hair": hair_found, "jewellery": found}
    faults = whole.faults(skin) + strands.faults(hair_found) + found.get("faults", [])
    measures["faults"] = faults
    (out / f"{given.name}-measures.json").write_text(json.dumps(measures, indent=1))
    scene = scene_file(pieces, given.name, out / f"{given.name}-scene.npz", garment_names)
    drawn(scene, fetched(pieces, out), out)
    print(json.dumps(measures, indent=1))
    if faults:
        raise SystemExit("the whole person has faults:\n" + "\n".join(faults))


if __name__ == "__main__":  # imported by tests and tools for its pieces, never run then
    main()
