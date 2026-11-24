"""A made model made sim-ready (#161's rules, PRD #159): its collision hulls (CoACD's approximate convex
decomposition), each hull's physics material its faces' material class's row, and a real-world mass for each part.

**The classes** are NVIDIA SimReady's per-class physics table (data/physics/surface_classes.json: density, static and
dynamic friction, restitution; its odd rows left out). A part's class is its finish's library surface's
(`surface_class`: a surface adopted from NVIDIA names it in its material's name, any other by its recipe); a model with
no finish yet (make, before the finish route) is all of the class it was given. A hull's class is the class of most of
the face area inside it; the model's friction and restitution are its hulls' rows weighted by hull volume, as the
benchmark reads NVIDIA's colliders.

**The mass** is a real-world figure for each part, never area x sheet x density nor volume x density (NVIDIA's masses
follow neither: 5 of 724 parts within 5% of volume x density): Claude is asked once what the object weighs and how
that splits over its parts (`weighed`, EUR 0 on the subscription, kept by the ask's hash). It is checked against
NVIDIA's mass over box volume for the size class (`bulk`, P10 to P90); a mass outside it is named in the record, not
refused: NVIDIA's own empty cardboard box lies under its small band.

    CLASSES, material(name), surface_class(record)   the classes
    hulls_of(vertices, faces) -> [(points, triangles)]
    weighed(words, size, parts, picture=None, ask=None) -> [kg per part]
    hull_classes(vertices, faces, face_class, hull_list) -> [class per hull]
    physical(hull_list, classes, parts, size) -> {"mass_kg", "parts", "bulk", "hull_m3", "hulls", "static", ...}
"""
import base64
import json
import pathlib

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[4]
CLASSES = REPO / "data/physics/surface_classes.json"
HULLS = 48  # CoACD's most hulls a model
CONCAVITY = 0.03  # CoACD's threshold, its default's middle
INSIDE = 1e-4  # metres: a face's middle this near a hull's planes is inside it
UNWEIGHED = 1e-4  # a part under this share of the surface is not asked and weighs 0 (finish_parts.NO_AREA's)


def table():
    return json.loads(CLASSES.read_text())


def material(name):
    """A class's physics material: {density, static, dynamic, restitution}."""
    found = table()["classes"]
    if name not in found:
        raise ValueError(f"no material class {name!r} (the classes: {', '.join(sorted(found))})")
    return found[name]


def surface_class(record):
    """A library surface record's material class: the class its NVIDIA material's name holds
    (m_<opacity>__<class>__...; metal whose record's base is aluminium, aluminium), else its recipe's; None when
    neither names one."""
    known = table()
    words = str(record.get("material") or "").split("__")
    if len(words) > 2 and words[1] in known["classes"]:
        base = str((record.get("nonvisual") or {}).get("base", ""))
        return "aluminium" if words[1] == "metal" and base.startswith("alumin") else words[1]
    recipe = record.get("recipe")
    recipe = recipe if isinstance(recipe, str) else (recipe or {}).get("recipe")
    return known["recipes"].get(recipe)


def hulls_of(vertices, faces):
    """CoACD's convex hulls of the mesh: [(points, triangles)]."""
    import coacd
    coacd.set_log_level("error")
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(vertices, float), np.asarray(faces, int)), threshold=CONCAVITY,
                            max_convex_hull=HULLS, seed=7)
    return [(np.asarray(points, float), np.asarray(triangles, int)) for points, triangles in parts]


def area_and_volume(points, triangles):
    """A closed hull's area (m^2) and volume (m^3, by the divergence theorem over its outward faces)."""
    corners = points[triangles]
    crossed = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    area = np.linalg.norm(crossed, axis=1).sum() / 2
    volume = abs(np.einsum("ij,ij->i", corners[:, 0], np.cross(corners[:, 1], corners[:, 2])).sum()) / 6
    return area, volume


def planes(points, triangles):
    """A convex hull's face planes as (unit outward normals, offsets): a point is inside where every n.p <= d."""
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    kept = lengths > 1e-12
    normals = normals[kept] / lengths[kept, None]
    offsets = np.einsum("ij,ij->i", normals, corners[kept, 0])
    middle = points.mean(0)
    flipped = normals @ middle > offsets  # faces wound inward
    normals[flipped], offsets[flipped] = -normals[flipped], -offsets[flipped]
    return normals, offsets


def size_class(size):
    """(name, its bulk_density row) of a model by its longest side: small, medium or large (#161)."""
    bands = table()["bulk_density"]
    longest = float(max(size))
    for name in ("small", "medium", "large"):
        if bands[name]["under_m"] is None or longest < bands[name]["under_m"]:
            return name, bands[name]
    raise AssertionError("the large band has no upper side")


def bulk(mass, size):
    """The mass over its box's volume held to NVIDIA's band for its size class: {"density", "size_class", "band",
    "in_band"}."""
    name, band = size_class(size)
    density = float(mass) / float(np.prod(np.asarray(size, float)))
    return {"density": round(density, 2), "size_class": name, "band": [band["low"], band["high"]],
            "in_band": bool(band["low"] <= density <= band["high"])}


def weighing_body(words, size, parts, picture=None):
    """The ask (a Gemini generateContent body, as claude_code reads one): the object's picture (a PNG's bytes, when
    given), its words, its box and its parts (each its words, its class and its share of the surface), answered as kg
    a part."""
    listed = "\n".join(f"{number}. {part['words']} ({part['class']}, {part['share']:.1%} of the surface)"
                        for number, part in enumerate(parts))
    text = (f"You give real-world masses for a physics simulator, as a maker's specification sheet gives them. The "
            f"object: {words}. Its bounding box is {' x '.join(f'{side:.3f}' for side in size)} m. Its visible "
            f"parts, each a finish of its surface:\n{listed}\n\nWork out what a real one of this size weighs as it "
            "stands (empty unless its words say it is filled) from how it is built: what each part is made of, its "
            "wall, sheet or frame thickness, and what it holds inside (a motor, a compressor, a mechanism, a "
            "frame), which weighs with the part that encloses it. Answer each part's mass in kg, by its number, and "
            "the whole.")
    schema = {"type": "OBJECT", "properties": {
        "whole_kg": {"type": "NUMBER"}, "reason": {"type": "STRING"},
        "parts": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "part": {"type": "INTEGER"}, "kg": {"type": "NUMBER"}}, "required": ["part", "kg"]}}},
        "required": ["whole_kg", "reason", "parts"]}
    shown = [{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(picture).decode()}},
             {"text": "The object as it was made from:"}] if picture else []
    return {"contents": [{"role": "user", "parts": [*shown, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def claude_ask(body):
    """The ask sent to Claude on the subscription (EUR 0), its answer's JSON text."""
    from score.adapters.models import claude_code
    answer = claude_code.asked({"weigh": body}, caller="make-weigh")["weigh"]
    if isinstance(answer, Exception):
        raise ValueError(f"no mass: {answer}")
    return answer


def weighed(words, size, parts, picture=None, ask=None):
    """Each part's real-world mass in kg (module docstring), seen in its `picture` (a PNG's path) when given; `ask`
    takes the body and gives the answer's JSON text (a test's), else Claude's. A part under UNWEIGHED of the surface
    is not asked and weighs 0 (#159 r11d: the toaster's one-face ink, share 0.0, was answered 0 kg and refused). An
    answer missing a part, or with a mass that is not above zero, is refused."""
    shown = pathlib.Path(picture).read_bytes() if picture else None
    asked = [number for number, part in enumerate(parts) if part["share"] >= UNWEIGHED]
    if not asked:
        raise ValueError(f"no part to weigh: each of the {len(parts)} parts holds under {UNWEIGHED} of the surface")
    answer = json.loads((ask or claude_ask)(weighing_body(words, size, [parts[number] for number in asked], shown)))
    masses = {int(row["part"]): float(row["kg"]) for row in answer["parts"]}
    if sorted(masses) != list(range(len(asked))) or min(masses.values()) <= 0:
        raise ValueError(f"the mass answer does not weigh each of the {len(asked)} parts: {answer['parts']}")
    found = [0.0] * len(parts)
    for index, number in enumerate(asked):
        found[number] = masses[index]
    return found


def hull_classes(vertices, faces, face_class, hull_list):
    """Each hull's class: the class of most of the face area whose faces' middles lie inside it, else (a hull with
    no face's middle inside) the class of the face whose middle is nearest its own."""
    corners = np.asarray(vertices, float)[np.asarray(faces, int)]
    middles = corners.mean(1)
    areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1) / 2
    face_class = np.asarray(face_class, dtype=object)
    found = []
    for points, triangles in hull_list:
        normals, offsets = planes(points, triangles)
        inside = ((middles @ normals.T) <= offsets + INSIDE).all(1)
        if not inside.any():
            found.append(face_class[int(np.argmin(np.linalg.norm(middles - points.mean(0), axis=1)))])
            continue
        held = {}
        for name, area in zip(face_class[inside], areas[inside]):
            held[name] = held.get(name, 0.0) + float(area)
        found.append(max(held, key=held.get))
    return found


def physical(hull_list, classes, parts, size):
    """The model's physics record: its parts ({words, class, share, kg}) and their sum, the mass's bulk density held to
    its band, and the contact numbers its hulls' classes give, weighted by hull volume."""
    volumes = np.array([area_and_volume(points, triangles)[1] for points, triangles in hull_list])
    weights = volumes / volumes.sum()
    rows = [material(name) for name in classes]
    mass = sum(part["kg"] for part in parts)
    held = {}
    for name, weight in zip(classes, weights):
        held[name] = held.get(name, 0.0) + float(weight)
    return {"material": max(held, key=held.get), "hull_classes": {name: round(share, 4) for name, share in held.items()},
            "mass_kg": round(float(mass), 3), "parts": parts, "bulk": bulk(mass, size),
            "measure": "a real-world mass a part (Claude's answer), held to NVIDIA's bulk density band",
            "hull_m3": round(float(volumes.sum()), 5), "hulls": len(hull_list),
            **{key: round(float(sum(weight * row[key] for weight, row in zip(weights, rows))), 4)
               for key in ("static", "dynamic", "restitution")}}
