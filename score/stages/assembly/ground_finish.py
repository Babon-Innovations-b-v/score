"""A place's made ground finished from the library (its own module, so the light rows lay the ground as the assembly
lays it without reading the assembly's package): the terrain writes each ground mesh of /<place>/Outside naming its
row and its finish missing; `finish_ground` binds it in the taken ground layer to the surface the surface library of a
scene holding its row gives it (`ground_surfaces`), the place's own library first, then each scene `ground_scenes`
names read beside (base's for the airlock). A mesh no library gives a surface keeps its finish named missing, never
painted another way.

    ground_scenes(place) -> [scene]                  the other scenes whose surface library finishes its ground
    ground_files(place) -> {name: path pattern}      the scene inventories `ground_surfaces` reads (its own and theirs)
    ground_surfaces(inputs, place) -> {row: (surface, materials.json)}
    finish_ground(inputs, root, place)               the ground layer of the stage at `root` bound to them
"""
import json
import pathlib

from score.stages import design_layers
from score.stages.assembly.record import GROUND_LAYER

INVENTORY = "{home}/design/inventory/"  # a scene's kept inventory, as design_layers.PATTERN names its folder


def ground_files(place):
    """{"inventory <scene>": its kept inventory's path pattern} for the place and each scene whose library finishes
    its ground (ground_scenes), where it has one: what ground_surfaces reads of a node that declares no whole folder."""
    return {f"inventory {scene}": f"{INVENTORY}{scene}.json" for scene in (place, *ground_scenes(place))
            if (design_layers.KEPT / f"{scene}.json").is_file()}


def inventory_of(inputs, scene):
    """A scene's inventory among a node's inputs: its own file (`inventory <scene>`, ground_files), else in the whole
    inventory folder (`inventories`, the assembly's); None when the node reads neither."""
    if f"inventory {scene}" in inputs:
        return pathlib.Path(inputs[f"inventory {scene}"])
    return pathlib.Path(inputs["inventories"]) / f"{scene}.json" if "inventories" in inputs else None


def ground_scenes(place):
    """The other scenes whose inventory holds a row of the place's made ground, read beside for their surface library
    (surface-library@<scene>): the terrain's ground row where the place's own inventory lacks it, at its ground's
    first top scene holding it (terrain.row_of: base's lunar_surface under the airlock, the square's plaza under the
    flat), and the first water row of the scenes on its ground where it has none of its own (terrain.sheet_of: the
    square's sea). [] for a place on no ground."""
    import score.stages.terrain.design as design  # the module alone: terrain's make stays out of a reader's code version
    folder = design_layers.KEPT.parent
    plans, skies = design.kept(folder / "plans"), design.kept(folder / "sky")
    ground = next((ground for ground in design.layout(plans, skies).values() if place in ground["places"]), None)
    if ground is None:
        return []
    rows = {name: [row for row in design.read(path)["rows"] if row.get("terrain")]
            for name in ground["places"] if (path := folder / "inventory" / f"{name}.json").is_file()}
    found = set()
    row = design.ground_row(ground, folder / "inventory", plans)
    if row and row not in {entry["id"] for entry in rows.get(place, [])}:
        found |= set(next(([top] for top in sorted(ground["tops"])
                           if row in {entry["id"] for entry in rows.get(top, [])}), []))
    if not any(design.water_row(entry) for entry in rows.get(place, [])):
        found |= set(next(([name] for name in sorted(rows) if any(design.water_row(entry) for entry in rows[name])),
                          []))
    return sorted(found - {place})




def ground_libraries(inputs, place):
    """[(scene, its surface library's materials.json)] the place's made ground may take a surface from: its own
    surface library first, then each other scene's read beside (surface-library@<scene>: ground_scenes)."""
    found = [(place, inputs["surface-library"])] if "surface-library" in inputs else []
    found += sorted((name.split("@", 1)[1], path) for name, path in inputs.items()
                    if name.startswith("surface-library@"))
    return [(scene, pathlib.Path(path) / "materials.json") for scene, path in found]


def ground_surface(row, library):
    """The surface a scene library (its materials.json content) gives a ground row: the first its kinds give the row's
    noun, as the library's ask names a natural ground's kind (scene_library.grounds_of); for a made ground the ask is
    given no kind of (natural_grounds.MADE: the square's plaza) its floor's (palette_library.shell_surface), the ground
    people walk on; else None."""
    from score.stages import natural_grounds
    import score.stages.surfaces.palette_library as palette_library  # the module alone, not the surface line
    kinds = library.get("kinds") or {}
    if kinds.get(row.get("noun")):
        return kinds[row["noun"]][0]
    made = natural_grounds.words_of(row) & set(natural_grounds.MADE)
    return palette_library.shell_surface("deck", library) if made else None


def ground_surfaces(inputs, place):
    """{a ground row's id: (the surface its scene's surface library gives it, that library's materials.json)}: each
    terrain row of a scene's inventory (ground_surface), the place's own library first (ground_libraries); {} with
    none."""
    found = {}
    for scene, library in ground_libraries(inputs, place):
        inventory = inventory_of(inputs, scene)
        if inventory is None or not inventory.is_file():
            continue
        content = json.loads(library.read_text())
        for row in json.loads(inventory.read_text())["rows"]:
            surface = ground_surface(row, content) if row.get("terrain") else None
            if surface:
                found.setdefault(row["id"], (surface, library))
    return found


def lay_surface(stage, place, surface, library):
    """A surface of a scene's library (`library`, its materials.json) laid under /<place>/Library as the earth seed
    lays the place's own (export.library_materials), where the place's library holds no surface of that name."""
    import export
    if not stage.GetPrimAtPath(f"/{place}/Library/{surface}"):
        export.library_materials(stage, place, f"/{place}",
                                 specs={surface: export.library.library_specs(library)[surface]})


def finish_ground(inputs, root, place):
    """Each mesh of the place's made ground (/<place>/Outside: its near and far patches and its water, which the
    terrain writes naming its row and its finish missing) bound in the taken ground layer to the surface the library
    of a scene holding its row gives it (ground_surfaces: hub's lunar_surface its own library's lunar_regolith, the
    airlock's base's), laid under /<place>/Library (the earth seed lays the place's own, lay_surface another
    scene's); one no library gives a surface keeps its finish named missing."""
    import scene
    from pxr import Sdf, Usd, UsdGeom
    surfaces = ground_surfaces(inputs, place)
    if not surfaces or not (root.parent / GROUND_LAYER).is_file():
        return
    (root.parent / GROUND_LAYER).chmod(0o644)  # the output's own copy, kept read-only from the store's by take_ground
    stage = Usd.Stage.Open(str(root))
    ground = Sdf.Layer.FindOrOpen(str(root.parent / GROUND_LAYER))
    stage.SetEditTarget(ground)
    outside = stage.GetPrimAtPath(f"/{place}/Outside")
    for prim in outside.GetChildren() if outside else []:
        row = prim.GetAttribute("score:row").Get() if prim.HasAttribute("score:row") else None
        if prim.IsA(UsdGeom.Mesh) and row in surfaces:
            surface, library = surfaces[row]
            lay_surface(stage, place, surface, library)
            prim.RemoveProperty("score:surface:missing")
            scene.bind_surface(stage, UsdGeom.Mesh(prim), place, surface)
    ground.Save()
