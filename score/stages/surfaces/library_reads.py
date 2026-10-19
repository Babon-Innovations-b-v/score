"""What a paint or bake row reads of the shared library and place.json, as the text its key hashes (the runner's
(pattern, part) form of a world file), so a library addition its places do not take re-keys none of them.

The paint reads labels.allowed_materials(library place, kind): the place's materials resolved through the library and
the kind's list in details.json. The bake reads library.by_library and library.resolved of its own library place for
the painted names and its job's specs, which are every library variant (bake_job.specs_of, as both routes write a
job). So a row's key holds, of place.json, the materials and wear of its library places
(the surface data's `library` and every take's `library_places`), and of the library, the variants those entries
name and their material names (a bake row: every variant), with their recipes, families and pictures, the kinds' details
and the library's own settings (wear levels, dirt); a bake row's details.json and composites.json, of the entries
its job reads (bake_reads), with each model its job would stop on declared missing. Before 2026-10-13 the rows
hashed the whole library folder and place.json, and one surface added for one place re-keyed every place's paint and bake (the hub's assembly wanted
about EUR 60 of re-buys).
"""
import json
import pathlib

from score.store import file_hash

REPO = pathlib.Path(__file__).resolve().parents[3]


def library_places(record):
    """The place.json ids a row reads: its data's library and every take's library places."""
    takes = record.get("takes", {}).values()
    return sorted({record.get("library"), *(place for take in takes for place in take.get("library_places", []))}
                  - {None})


def kinds(record):
    return sorted({take["kind"] for take in record.get("takes", {}).values() if take.get("kind")})


def places_part(ids):
    """The part of place.json a row reads: its library places' materials and wear (library.resolved, wear_of and
    dirt_token_of read nothing else of an entry)."""
    def part(path):
        found = json.loads(pathlib.Path(path).read_text())
        return json.dumps({place: {key: found.get(place, {}).get(key) for key in ("materials", "wear")}
                           for place in ids}, sort_keys=True)
    return part


def job_specs(library, bakes):
    """The spec names of a bake job: every variant of the library (bake_job.specs_of) for a bake row, none for
    another."""
    return [name for entry in library["families"].values() for name in entry["variants"]] if bakes else []


def named_variants(library, names):
    """{variant: its entry with its family} of the library's variants among `names`."""
    found = {}
    for family, entry in library["families"].items():
        for name, variant in entry["variants"].items():
            if name in names:
                found[name] = dict(variant, family=family)
    return found


def library_text(folder, ids, kind_names, bakes):
    """The library a row reads (see the module's docstring), as sorted JSON; its pictures by their files' hashes."""
    folder = pathlib.Path(folder)
    places = json.loads((folder.parent / "definitions/place.json").read_text())
    library = json.loads((folder / "materials.json").read_text())
    details = json.loads((folder / "details.json").read_text())
    materials = {name: entry for place in ids for name, entry in places.get(place, {}).get("materials", {}).items()}
    names = {*materials, *(entry["library"] for entry in materials.values() if "library" in entry),
             *job_specs(library, bakes)}
    variants = named_variants(library, names)
    recipes = {variant["recipe"] for variant in variants.values() if "recipe" in variant}
    pictures = {spec["picture"] for spec in [*variants.values(), *(library["recipes"].get(name, {}) for name in recipes)]
                if "picture" in spec}
    picture_files = {name: file_hash(folder / "pictures" / f"{name}.png") if (folder / "pictures" / f"{name}.png").is_file()
                     else None for name in pictures}
    return json.dumps({"settings": {key: value for key, value in library.items()
                                    if key not in ("families", "recipes", "pictures")},
                       "variants": variants,
                       "families": {variant["family"]: {key: value for key, value in
                                                        library["families"][variant["family"]].items()
                                                        if key != "variants"} for variant in variants.values()},
                       "recipes": {name: library["recipes"].get(name) for name in recipes},
                       "pictures": {name: library.get("pictures", {}).get(name) for name in pictures},
                       "picture files": picture_files,
                       "details": {kind: details.get(kind) for kind in kind_names}}, sort_keys=True)


def library_part(ids, kind_names, bakes):
    def part(path):
        return library_text(path, ids, kind_names, bakes)
    return part


def entries_part(names):
    """The part of a {name: entry} file (details.json, composites.json) of the entries `names`."""
    def part(path):
        found = json.loads(pathlib.Path(path).read_text())
        return json.dumps({name: found.get(name) for name in names}, sort_keys=True)
    return part


def declared_record(wide, name):
    """The record a row declares as `name` under {data} (the repository's data, as the table reads it); {} when it
    declares none or it is not there."""
    pattern = wide.get(name)
    if not isinstance(pattern, str) or not pattern.startswith("{data}/"):
        return {}
    path = REPO / "data" / pattern[len("{data}/"):]
    return json.loads(path.read_text()) if path.is_file() else {}


def bake_reads(place, record, wide):
    """A bake row's details and composites keyed on the entries its job reads for the models its data writes no
    entry for (bake_job.reads), and each model bake_job would stop on whatever its take (bake_job.refusal) declared as
    a file that is never there, naming it (`bake entry <model>`), so the run refuses before anything is cleared."""
    import bake_job
    bake = record.get("bake") or {}
    kit, inventory = declared_record(wide, "kit"), declared_record(wide, "inventory")
    written = bake.get("entries", {})
    details, composites, refused = set(), set(), {}
    for model in bake.get("models", {}):
        why = bake_job.refusal(place, model, written.get(model), kit, inventory)
        if why:
            said = why.replace("{", "").replace("}", "")
            refused[f"bake entry {model}"] = f"{wide['surfaces']} gives no entry ({said})"
        elif not isinstance(written.get(model), dict):
            kinds_read, props_read = bake_job.reads(place, model, kit)
            details.update(kinds_read)
            composites.update(props_read)
    return {"details": (wide["details"], entries_part(sorted(details))),
            "composites": (wide["composites"], entries_part(sorted(composites))), **refused}


def narrowed(files, record_of):
    """A row's world files (`files`: a function of the place, or a dict) with its library and place.json keyed on
    what it reads (`record_of(place)`: the surface data the row paints from), and a bake row's details and composites
    (it declares `details`) on what its job reads (bake_reads). The wide map stays on it as `wide`."""
    def found(place):
        wide = files(place) if callable(files) else dict(files)
        record = record_of(place)
        ids = library_places(record)
        bakes = "details" in wide
        return {**wide, "library": (wide["library"], library_part(ids, kinds(record), bakes)),
                "places": (wide["places"], places_part(ids)), **(bake_reads(place, record, wide) if bakes else {})}
    found.wide = files
    return found
