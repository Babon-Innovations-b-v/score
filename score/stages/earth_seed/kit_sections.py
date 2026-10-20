"""kit-sections@<place> (free): the Earth kit's after-step on the shared loop (#41; CONTEXT.md "shell section",
"layer adapter"), registered as shapes_first.KIT. It lays the place's shell by the sections its plan marks
(data/plans/<place>.json `sections`: each a stretch of walls, floor or ceiling as the concept shows it, its name the
concept element it was read from, its surface and the inventory rows of its pieces), one piece style and one finish a
section with its wear running across the seams:

    style    the section's rows, each a pipeline-made variant (made.made: the loop's baked model, or its gap)
    finish   one library surface for the whole section: the one over the most area of its rows' parts (each row's
             part rows from surfaces-parts, by share); none, a gap named, where the loop made none of its rows
    wear     the place's level, dirt and cause (data/definitions/place.json `wear` of the place's library) under one
             seed a section, read at each piece's place in the section (`wear_at`: metres from the section's origin,
             the least corner of its pieces' spots in the place's base stage), so it runs on across the seams instead
             of starting again on each piece

Output: sections.json ({"place", "sections": [{name, surface, rows, made, finish, shares, seed, wear, origin,
pieces, gap}]}) and layers/sections.usda, the assembly's layer of it (assembly.LAYERS): an over on each of the base
stage's objects of a section's rows (earth-seed's, read after it), carrying score:section, score:finish,
score:wear_seed and score:wear_at. Gate `sections`: every section's rows are laid in the base, no row in two sections;
a section the loop made nothing of is a gap, counted and named, not a stop (the batch rule).
"""
import json
import pathlib
import zlib

from score import checks, contracts
import score.stages.earth_seed as earth_seed
import score.stages.shapes_first.made as made

OUTPUT = "sections.json"
LAYER = "layers/sections.usda"
AFTER = {**made.ENDS, "earth-seed": (earth_seed.EARTH_SEED.schema, earth_seed.EARTH_SEED.version)}


def files(place):
    """The plan (its sections), the place definitions (its wear) and the surface data (its library's name)."""
    return {"plan": "{data}/plans/" + f"{place}.json", "places": "{data}/definitions/place.json",
            "surfaces": "{data}/surfaces/" + f"{place}.json"}


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def wear_of(inputs):
    """The place's wear (level, dirt, cause) from its library's place definition."""
    library = read(inputs["surfaces"])["library"]
    return read(inputs["places"]).get(library, {}).get("wear", {})


def laid_objects(seed):
    """{row: [(object path, its spot in the place's frame)]} of the base stage's objects (earth-seed's output)."""
    from pxr import Usd, UsdGeom
    place = earth_seed.place_in(seed)
    stage = Usd.Stage.Open(str(place / "layers/base.usda"), Usd.Stage.LoadNone)
    found = {}
    objects = stage.GetPrimAtPath(f"/{place.name}/Objects")
    for prim in objects.GetChildren() if objects else []:
        row = prim.GetAttribute("score:row").Get()
        spot = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        found.setdefault(row, []).append((str(prim.GetPath()), [round(float(value), 4) for value in spot]))
    return found


def finish_of(rows, made_rows):
    """The section's one finish and every library surface's share of its made rows' parts: (surface or None, shares)."""
    shares = {}
    for row in rows:
        for part in made_rows.get(row, {}).get("finishes", []):
            if part.get("judge"):
                shares[part["judge"]] = round(shares.get(part["judge"], 0.0) + float(part["share"]), 4)
    return (max(sorted(shares), key=shares.get) if shares else None), shares


def made_as(found):
    """How the loop made one of a section's rows: its take, its code route, or its gap."""
    if found is None:
        return "gap: not handed to the loop on the kit layer"
    return found.get("take") or (f"gap: {found['gap']}" if "gap" in found else found["route"])


def laid_section(section, objects, place, made_rows, wear):
    """One section's record and its objects with their places in it ([(path, wear_at)])."""
    laid = [entry for row in section["rows"] for entry in objects.get(row, [])]
    origin = [min(spot[axis] for _, spot in laid) for axis in range(3)] if laid else [0.0, 0.0, 0.0]
    finish, shares = finish_of(section["rows"], made_rows)
    record = {"name": section["name"], "surface": section["surface"], "rows": section["rows"],
              "made": {row: made_as(made_rows.get(row)) for row in section["rows"]},
              "finish": finish, "shares": shares, "seed": zlib.crc32(f"{place}/{section['name']}".encode()),
              "wear": wear, "origin": origin, "pieces": len(laid),
              "gap": None if finish else "the loop made no model of the section's rows: no finish to lay"}
    return record, [(path, [round(spot[axis] - origin[axis], 4) for axis in range(3)]) for path, spot in laid]


def write_layer(path, record, laid):
    """The sections layer: an over on each laid object of a section with its section, finish, seed and place in it."""
    from pxr import Gf, Sdf, Usd
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(path))
    for section, objects in zip(record, laid):
        for object_path, wear_at in objects:
            prim = stage.OverridePrim(object_path)
            for name, value in (("score:section", section["name"]), ("score:finish", section["finish"] or ""),
                                ("score:wear_seed", str(section["seed"]))):
                prim.CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
            prim.CreateAttribute("score:wear_at", Sdf.ValueTypeNames.Float3).Set(Gf.Vec3f(*wear_at))
    stage.GetRootLayer().Save()


def make(inputs, out, seed, params):
    """sections.json and the sections layer: each plan section laid with one style, one finish and its wear across
    the seams."""
    place = earth_seed.place_in(inputs["earth-seed"]).name
    made_rows = made.made(inputs, earth_seed.KIT_LAYER)
    objects, wear = laid_objects(inputs["earth-seed"]), wear_of(inputs)
    laid = [laid_section(section, objects, place, made_rows, wear)
            for section in read(inputs["plan"]).get("sections", [])]
    write_layer(out / LAYER, [record for record, _ in laid], [objects for _, objects in laid])
    (out / OUTPUT).write_text(json.dumps({"place": place, "sections": [record for record, _ in laid]}, indent=1))


def faults(folder):
    return [f"no {name}" for name in (OUTPUT, LAYER) if not (pathlib.Path(folder) / name).exists()]


def judge_sections(output, inputs, evidence):
    """Every section's rows are laid in the base and no row is in two sections; the sections the loop made nothing of
    are gaps, named."""
    found = read(pathlib.Path(output) / OUTPUT)["sections"]
    seen, failing = {}, []
    for section in found:
        if not section["pieces"]:
            failing.append(f"{section['name']}: the base lays none of its rows {section['rows']}")
        for row in section["rows"]:
            if row in seen:
                failing.append(f"{row}: in two sections, {seen[row]!r} and {section['name']!r}")
            seen.setdefault(row, section["name"])
    gaps = [f"gap: {section['name']}: {section['gap']}" for section in found if section["gap"]]
    reason = ("; ".join(failing[:3]) if failing else
              f"{len(found)} sections, each one style and one finish ({len(gaps)} gaps)" if found else
              "the plan marks no shell sections")
    return checks.Verdict("sections", checks.FAIL if failing else checks.PASS, reason,
                          {"sections": len(found), "faults": len(failing), "gaps": len(gaps)},
                          {"faults": "lower", "gaps": "lower"}, tuple(failing + gaps))


CONTRACT = contracts.Contract("kit-sections", 1, faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("sections", judge_sections),)
