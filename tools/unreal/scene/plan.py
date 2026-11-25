"""A scene package's plan for Unreal (#221): everything the editor makes, worked out with no engine, so the editor
layer (editor.py) only carries it out. Plain Python with no numpy: Unreal's own Python imports it too.

    python3 tools/unreal/scene/plan.py <package> <into> [--path <place>/film/path.json]

writes <into>/plan.json and the textures to import under <into>/textures, and prints one line. The plan:
    format, version    "score.unreal", 1
    place, package     the place and the package's folder
    caps               the package's scene.json `textures` (a film's are scene_package.FILM_CAPS), or null
    draft              whether the package is a draft (its recipes never baked: no film is rendered from one)
    basis              frames' BASIS every point and turn below was made with (editor.py measures the import's own)
    textures           [{name, file, srgb, normal}]: looks.written_textures
    materials          [{name, surface, master, vectors, scalars, two_sided, textures}]: one a distinct look
    meshes             [{object, file, character, nanite, parts, slots {glTF material name: material}}]: parts the
                       glTF's mesh nodes, the most mesh assets its import may give (it may combine them)
    actors             [{name, object, kind, character, transform {location, rotation, scale}, plays}]
    lamps              [{name, location, lumens, radius, reach, colour}]: reach the attenuation radius (layout.reach)
    environment        {sun, moon, sky, exposure_bias, ambient, background, grade}: layout.environment, a night's sky its
                       ambient, the grade its tonemapper material's HLSL
    camera             camera.keys of the film path laid on the package's seat (seat_of), or null
                       (in_view then keeps only the lamps whose reach meets one of its frames' views)
    left_out           scene.json's
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import camera  # noqa: E402
import frames  # noqa: E402
import layout  # noqa: E402
import looks  # noqa: E402

ROOT = "/Game/Score"  # where editor.py makes every asset


def level_path(place):
    """The level editor.py makes for the place, as a map path."""
    return f"{ROOT}/{place}/L_{place}"


def sequence_path(place):
    """The place's film as a Level Sequence, as Movie Render Queue's object path."""
    return f"{ROOT}/{place}/LS_{place}_film.LS_{place}_film"


def object_slots(gltf, textures):
    """An object's material slots {glTF material name: instance name} and its instances, its pictures added to
    `textures`; None (nothing added) when two of its materials of one name are two looks: the editor finds a slot by
    its name, so it could not tell them apart."""
    slots, found, pictures = {}, {}, dict(textures)
    for slot, instance in looks.object_looks(gltf, pictures):
        if slots.get(slot, instance["name"]) != instance["name"]:
            return None
        slots[slot] = instance["name"]
        found.setdefault(instance["name"], instance)
    textures.update(pictures)
    return slots, found


def meshes_and_materials(package, scene, textures):
    """Each object's mesh {object, file, character, nanite, slots}, every distinct material instance by name (their
    pictures added to `textures`), and the objects left out [{name, why}]: one whose two glTF materials of one name
    are two looks (object_slots; square@4's fg_east4_0_ac and tower_left, #222 run 18) is left out, the rest laid."""
    meshes, materials, left_out = [], {}, []
    for name, about in sorted(scene["objects"].items()):
        gltf = package / about["file"]
        made = object_slots(gltf, textures)
        if made is None:
            left_out.append({"name": name, "why": "two of its looks share one material name: the editor finds a slot "
                                                  "by its name"})
            continue
        slots, found = made
        for look, instance in found.items():
            materials.setdefault(look, instance)
        character = about.get("kind") == "character"
        meshes.append({"object": name, "file": str(gltf), "character": character,
                       "nanite": not character and looks.solid(gltf), "parts": looks.mesh_nodes(gltf), "slots": slots})
    return meshes, materials, left_out


def seat_of(scene):
    """The package's seat (scene.json `seat`), which lays its place's own frame, the film path's, in the package's;
    None for a package in its place's own frame. Refused (ValueError) for a package in an area's frame that carries
    no seat: its film path cannot be laid on it."""
    if scene.get("seat") is None and str(scene.get("frame", "")).startswith("the area"):
        raise ValueError(f"{scene['place']}: the package is in an area's frame but carries no `seat` "
                         "(package it again): its film path is in the place's own frame")
    return scene.get("seat")


def planned(package, into, path=None, basis=frames.BASIS):
    """The plan for the package at <package> (its textures written under <into>), the camera from the film path at
    `path` when given, every point and turn through `basis`."""
    package, into = pathlib.Path(package), pathlib.Path(into)
    scene = json.loads((package / "scene.json").read_text())
    if scene.get("version") != 1:
        raise ValueError(f"{package}: not a score.scene version 1 package (a piece list has no baked looks)")
    textures = {}
    meshes, materials, refused = meshes_and_materials(package, scene, textures)
    unlaid = {out["name"] for out in refused}
    shots = camera.keys(path, basis, seat_of(scene)) if path else None
    return {"format": "score.unreal", "version": 1, "place": scene["place"], "package": str(package),
            "caps": scene.get("textures"), "draft": "draft" in scene, "basis": [list(row) for row in basis],
            "textures": looks.written_textures(textures, into),
            "materials": [materials[name] for name in sorted(materials)], "meshes": meshes,
            "actors": [actor for actor in layout.actors(scene, basis) if actor["object"] not in unlaid],
            "lamps": layout.lamps(scene, basis),
            "environment": layout.lit_by_ambient(layout.environment(scene, package, basis), into),
            "camera": shots, "left_out": scene.get("left_out", []) + refused}


def in_view(made, shots):
    """The plan with only the lamps whose reach meets the film's view (camera.lights_in_view, `shots` the film's
    keys: its own for the shot's place, the shot's for a neighbour laid beside it), the rest added to `left_out`;
    unchanged with no film."""
    if shots is None:
        return made
    kept, dropped = camera.lights_in_view(made["lamps"], shots)
    return dict(made, lamps=kept, left_out=made["left_out"] + [
        {"name": name, "why": "a lamp whose reach meets no frame's view"} for name in dropped])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("package")
    parser.add_argument("into")
    parser.add_argument("--path", help="the place's film/path.json, for the Level Sequence's camera")
    args = parser.parse_args()
    made = planned(args.package, args.into, args.path)
    made = in_view(made, made["camera"])
    (pathlib.Path(args.into) / "plan.json").write_text(json.dumps(made, indent=1) + "\n")
    print(f"{made['place']}: {len(made['meshes'])} meshes ({sum(mesh['nanite'] for mesh in made['meshes'])} Nanite), "
          f"{len(made['actors'])} actors, {len(made['materials'])} materials, {len(made['textures'])} textures, "
          f"camera {made['camera']['frames'] if made['camera'] else 'none'} frames; caps "
          f"{(made['caps'] or {}).get('use')}; {pathlib.Path(args.into) / 'plan.json'}")


if __name__ == "__main__":
    main()
