"""What the shared loop hands a layer adapter's after-steps (#41): the models it made with their finishes, or the gaps.

An after-step reads the loop's ends (`ENDS`, in its `after`) and calls `made(inputs, layer)`:

    {row: {"route": "prop", "model": <baked .gltf>, "take": <take>, "finishes": [<part rows of surfaces-parts>],
           "failures": {<step>: <the named failure the row's record gives for a step made outside the loop>}}
          | {"route": "code", "model": <the code build named by the row's failure>, "finishes": []}
          | {"gap": <why the loop made no model for the row>}}

for every row of the place's hand-in record (data/props/<place>.json) on `layer`. Import it by its full name
(`import score.stages.shapes_first.made as made`), never the package: the package is the table's wiring, and its
imports would move every after-step's key.
"""
import json
import pathlib

ENDS = {"props-inputs": ("props-inputs", 1), "surfaces-bake": ("surfaces-bake", 1),
        "surfaces-parts": ("surfaces-parts", 1), "likeness": ("props-likeness", 1)}


def read(folder, name):
    return json.loads((pathlib.Path(folder) / name).read_text())


def baked_models(bake):
    """{take: baked .gltf} of a surfaces-bake output (the first model baked of each take)."""
    found = {}
    for model, entry in sorted(read(bake, "baked.json").items()):
        found.setdefault(entry["parts"], pathlib.Path(bake) / "made" / f"{model}.gltf")
    return found


def made_row(row, entry, baked, parts):
    """One row's model and finishes, or its gap."""
    if entry is None:
        return {"gap": "no likeness record: the loop never reached its model"}
    if "missing" in entry:
        return {"gap": entry["missing"]}
    if entry["route"] == "code":
        return {"route": "code", "model": entry["model"], "finishes": []}
    model = baked.get(row["take"])
    if model is None:
        return {"gap": f"take {row['take']} has no baked model"}
    return {"route": "prop", "model": str(model), "take": row["take"],
            "finishes": parts.get(row["take"], {}).get("parts", []), "failures": row.get("failures", {})}


def made(inputs, layer):
    """{row: made model or gap} of every row the place handed the loop on `layer` (see the module's docstring)."""
    rows = [row for row in read(inputs["props-inputs"], "rows.json")["rows"] if row["layer"] == layer]
    objects = read(inputs["likeness"], "likeness.json")["objects"]
    baked = baked_models(inputs["surfaces-bake"]) if "surfaces-bake" in inputs else {}
    parts = read(inputs["surfaces-parts"], "parts.json")["takes"] if "surfaces-parts" in inputs else {}
    return {row["id"]: made_row(row, objects.get(row["id"]), baked, parts) for row in rows}
