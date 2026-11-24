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
    meshes             [{object, file, character, nanite, slots {glTF material name: material}}]
    actors             [{name, object, kind, character, transform {location, rotation, scale}, plays}]
    lamps              [{name, location, lumens, radius, colour}]
    environment        {sun, moon, sky, exposure_bias, ambient, grade}: layout.environment
    camera             camera.keys of the film path, or null
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
                       "nanite": not character and looks.solid(gltf), "slots": slots})
    return meshes, materials


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
            "environment": layout.environment(scene, package, basis),
            "camera": camera.keys(path, basis) if path else None, "left_out": scene.get("left_out", [])}


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
