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


def meshes_and_materials(package, scene, textures):
    """Each object's mesh {object, file, character, nanite, slots} and every distinct material instance by name, its
    pictures added to `textures`. Refused (ValueError) when one object's two glTF materials of one name are two
    looks (the editor finds a slot by its name)."""
    meshes, materials = [], {}
    for name, about in sorted(scene["objects"].items()):
        gltf = package / about["file"]
        slots = {}
        for slot, instance in looks.object_looks(gltf, textures):
            if slots.get(slot, instance["name"]) != instance["name"]:
                raise ValueError(f"{name}: two looks share the material name {slot!r}")
            slots[slot] = instance["name"]
            materials.setdefault(instance["name"], instance)
        character = about.get("kind") == "character"
        meshes.append({"object": name, "file": str(gltf), "character": character,
                       "nanite": not character and looks.solid(gltf), "parts": looks.mesh_nodes(gltf), "slots": slots})
    return meshes, materials


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
    meshes, materials = meshes_and_materials(package, scene, textures)
    return {"format": "score.unreal", "version": 1, "place": scene["place"], "package": str(package),
            "caps": scene.get("textures"), "draft": "draft" in scene, "basis": [list(row) for row in basis],
            "textures": looks.written_textures(textures, into),
            "materials": [materials[name] for name in sorted(materials)], "meshes": meshes,
            "actors": layout.actors(scene, basis), "lamps": layout.lamps(scene, basis),
            "environment": layout.lit_by_ambient(layout.environment(scene, package, basis), into),
            "camera": camera.keys(path, basis, seat_of(scene)) if path else None, "left_out": scene.get("left_out", [])}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("package")
    parser.add_argument("into")
    parser.add_argument("--path", help="the place's film/path.json, for the Level Sequence's camera")
    args = parser.parse_args()
    made = planned(args.package, args.into, args.path)
    (pathlib.Path(args.into) / "plan.json").write_text(json.dumps(made, indent=1) + "\n")
    print(f"{made['place']}: {len(made['meshes'])} meshes ({sum(mesh['nanite'] for mesh in made['meshes'])} Nanite), "
          f"{len(made['actors'])} actors, {len(made['materials'])} materials, {len(made['textures'])} textures, "
          f"camera {made['camera']['frames'] if made['camera'] else 'none'} frames; caps "
          f"{(made['caps'] or {}).get('use')}; {pathlib.Path(args.into) / 'plan.json'}")


if __name__ == "__main__":
    main()
