"""score_lib's README pictures, one of each kind, made again from the library's own entries (owner, 2026-11-22: "these
samples are so shit"): every 3D one rendered in the cloud by tools/blender/inside/library_demo.py, the concept, the
place and the sound from the pictures their entries hold.

    .venv/bin/python tools/library/demo/pictures.py --out <folder> [--who <session>] [--here] [--prepare]

writes <kind>.jpg into the folder (score_lib's docs/demo/ when its README takes them) and prints one line. `PICKS`
names each picture's entries and how it is staged; the reasons for each pick are on score #156.

How the entries are read so a plain USD reader shows them as score's places do:
- A kit piece's parts are GeomSubsets of one mesh, each bound to a placeholder material named after it (score #156;
  each part takes its own library surface when a place lays it): `split_parts` writes each part as its own Z-up PLY,
  and the picture gives each a surface. A decal part is left out (the library's pieces no longer hold one: its logo
  was a picture the library does not keep).
- A rigged character's body.glb holds two levels of detail and a helper sphere; only the near body (`work`) is drawn,
  posed at a frame of its own walking clip.
- An effect is the clip's particles at one clip time, placed at its model's spout by the effect's own rule (the
  mesh's farthest point from its middle above half its height), and drawn with score's puff look.
- The algorithm's picture is score's own dome_shell code run here, the same code the entry snapshots.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/library"))
import library_files  # noqa: E402

INSIDE = REPO / "tools/blender/inside/library_demo.py"
SIZE = (960, 720)
SAMPLES = 256
JPEG_WIDTH = 720  # the README shows three across
CLASSES = ["gpu-24gb"]
LOCAL_BLENDER = "5.2.2"  # the Blender tools/blender/setup.sh installs on this PC
STEAM_TIME = 62.0  # the clip time the effect's own preview shows
SPOT_COLOUR = "#f3f1ea"  # light/lamp@1's aimed lamp colour
SPOT_ANGLE = 46.0  # light/lamp@1's aimed lamp angle, degrees

SURFACE = {name: f"surface/{name}@1" for name in (
    "ambientcg_diamondplate008a", "ambientcg_plastic010", "ambientcg_rubber004", "ambientcg_concrete046")}
# The kit corner's finish per part name, every one a library surface.
KIT_FINISH = {"MI_Trim_01": "ambientcg_plastic010", "MI_Trim_02": "ambientcg_rubber004",
              "MI_PaddedWall": "ambientcg_rubber004", "MI_Trim_03": "ambientcg_plastic010",
              "MI_Trim_03_Dark": "ambientcg_rubber004", "MI_Trim_03_Cables_Blue": "ambientcg_rubber004"}
# The kit corner: two by two floor tiles of 2.2 m, a wall with its top piece along two sides, a column in the corner.
# (piece, tile centre, turn degrees, floor surface)
KIT_CORNER = [
    ("platform_metal", (0.0, 0.0), 0, "ambientcg_diamondplate008a"),
    ("platform_metal", (2.2, 0.0), 0, "ambientcg_diamondplate008a"),
    ("platform_squares", (0.0, 2.2), 0, "ambientcg_concrete046"),
    ("platform_squares", (2.2, 2.2), 0, "ambientcg_concrete046"),
    ("wall_window_straight", (0.0, 0.0), 0, None), ("top_cables_straight", (0.0, 0.0), 0, None),
    ("wall_band_straight", (0.0, 2.2), 0, None), ("top_cables_straight", (0.0, 2.2), 0, None),
    ("wall_astra_straight", (0.0, 2.2), -90, None), ("top_cables_straight", (0.0, 2.2), -90, None),
    ("wall_band_straight", (2.2, 2.2), -90, None), ("top_cables_straight", (2.2, 2.2), -90, None),
    ("column_pipes", (-1.1, 3.3), 0, None),
]
PICKS = {
    "model": "model/tracked_rover_1.garage@1",
    "surface": "surface/ambientcg_diamondplate008a@1",
    "kit": "kit/quaternius_scifi_*@1",
    "character": "character/person_stair_trellis@1",
    "effect": "effect/kettle_1_steam_jet@1",
    "light": "light/lamp@1",
    "algorithm": "algorithm/dome_shell@1",
    "concept": "concept/cockpit@2",
    "place": "place/cockpit@2",
    "take": "take/garage_rover_chassis_b26f85f9@1",
    "sound": "sound/hatch_open@2",
}


def entry_record(address):
    kind, rest = address.split("/", 1)
    name, version = rest.split("@")
    root = pathlib.Path(library_files.settings()["SCORE_LIB_ROOT"])
    return json.loads((root / "entries" / kind / name / version / "entry.json").read_text())


def entry_files(address, only=None):
    """Every file of an entry (or those whose names end with one of `only`) fetched into the library cache; the
    entry's folder there."""
    folder = None
    for file in entry_record(address)["files"]:
        if only and not file.endswith(tuple(only)):
            continue
        found = library_files.resolve(library_files.reference(address, file))
        if found is None:
            raise SystemExit(f"{address}/{file}: the library does not hold it")
        folder = pathlib.Path(str(found)[:-len(file)])
    if folder is None:
        raise SystemExit(f"{address}: no file of it is wanted ({only})")
    return folder


def write_ply(path, points, faces):
    """Points (n, 3) and faces (lists of point indices) as an ASCII PLY."""
    lines = ["ply", "format ascii 1.0", f"element vertex {len(points)}", "property float x", "property float y",
             "property float z", f"element face {len(faces)}", "property list uchar int vertex_indices", "end_header"]
    lines += [f"{x:.6f} {y:.6f} {z:.6f}" for x, y, z in points]
    lines += [" ".join(str(index) for index in [len(face), *face]) for face in faces]
    path.write_text("\n".join(lines) + "\n")


def z_up(points, y_up):
    """Points in metres of a Y-up stage turned Z-up, as Blender's USD reader turns them."""
    return numpy.c_[points[:, 0], -points[:, 2], points[:, 1]] if y_up else points


def split_parts(usd_path, out):
    """Each GeomSubset of the file's meshes as <part>.ply in `out`, Z-up in metres (a mesh with no parts as
    <mesh>.ply); the parts' names."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(usd_path))
    y_up, metres = UsdGeom.GetStageUpAxis(stage) == "Y", UsdGeom.GetStageMetersPerUnit(stage) or 1.0
    cache = UsdGeom.XformCache()
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        world = numpy.array(cache.GetLocalToWorldTransform(prim))
        points = numpy.array(mesh.GetPointsAttr().Get(), dtype=float)
        points = z_up((numpy.c_[points, numpy.ones(len(points))] @ world)[:, :3] * metres, y_up)
        counts = numpy.array(mesh.GetFaceVertexCountsAttr().Get())
        indices = numpy.array(mesh.GetFaceVertexIndicesAttr().Get())
        starts = numpy.concatenate([[0], numpy.cumsum(counts)[:-1]])
        subsets = UsdGeom.Subset.GetAllGeomSubsets(mesh)
        groups = [(subset.GetPrim().GetName(), list(subset.GetIndicesAttr().Get())) for subset in subsets] or [
            (prim.GetName(), list(range(len(counts))))]
        for name, faces in groups:
            corners = [indices[starts[face]:starts[face] + counts[face]] for face in faces]
            used = sorted({int(index) for face in corners for index in face})
            renumbered = {old: new for new, old in enumerate(used)}
            write_ply(out / f"{name}.ply", points[used], [[renumbered[int(index)] for index in face] for face in corners])
            names.append(name)
    return names


def stage_points(path):
    """Every mesh point of a model in metres, in its own up axis, and whether that axis is Y (glTF's always is)."""
    if pathlib.Path(path).suffix in (".gltf", ".glb"):
        import trimesh
        return numpy.asarray(trimesh.load(str(path), force="scene").to_geometry().vertices, dtype=float), True
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(path))
    cache = UsdGeom.XformCache()
    found = []
    for prim in stage.Traverse():
        if prim.IsA(UsdGeom.Mesh):
            points = numpy.array(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=float)
            world = numpy.array(cache.GetLocalToWorldTransform(prim))
            found.append((numpy.c_[points, numpy.ones(len(points))] @ world)[:, :3])
    return numpy.vstack(found) * (UsdGeom.GetStageMetersPerUnit(stage) or 1.0), UsdGeom.GetStageUpAxis(stage) == "Y"


def spout(points):
    """The effect's own rule for a steam jet's source (Y-up): the mesh's farthest point from its middle across, among
    the points above half its height."""
    low, high = points.min(0), points.max(0)
    middle = (low + high) / 2
    upper = points[points[:, 1] > low[1] + 0.5 * (high[1] - low[1])]
    across = numpy.linalg.norm((upper - middle)[:, [0, 2]], axis=1)
    return upper[numpy.argmax(across)]


def steam_points(clip_path, model_path, out, time=STEAM_TIME):
    """The clip's particles at `time` set at the model's spout, the jet's +z turned toward the spout, Z-up; written as
    npz (points, widths, opacity) for library_demo.py."""
    from pxr import Usd, UsdGeom
    clip = Usd.Stage.Open(str(clip_path))
    cloud = next(UsdGeom.Points(prim) for prim in clip.Traverse() if prim.IsA(UsdGeom.Points))
    jet = numpy.array(cloud.GetPointsAttr().Get(time), dtype=float)
    points, y_up = stage_points(model_path)
    source = spout(points)
    outward = numpy.array([source[0], 0.0, source[2]]) - (points.min(0) + points.max(0)) / 2 * [1, 0, 1]
    heading = numpy.arctan2(outward[0], outward[2])  # the turn about up that takes +z onto the spout's direction
    turn = numpy.array([[numpy.cos(heading), 0, numpy.sin(heading)], [0, 1, 0],
                        [-numpy.sin(heading), 0, numpy.cos(heading)]])
    placed = z_up(jet @ turn.T + source, y_up)
    widths = numpy.asarray(cloud.GetWidthsAttr().Get(time), dtype=numpy.float32)
    numpy.savez(out, points=placed.astype(numpy.float32), widths=widths,
                opacity=numpy.asarray(UsdGeom.PrimvarsAPI(cloud).GetPrimvar("displayOpacity").Get(time),
                                      dtype=numpy.float32))
    points_file(pathlib.Path(out).with_suffix(".usda"), placed, widths)
    return out


def points_file(path, points, widths):
    """The particles as a Z-up USD Points file in metres, which library_demo.py imports to get its point cloud."""
    from pxr import Gf, Usd, UsdGeom, Vt
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    cloud = UsdGeom.Points.Define(stage, "/effect")
    cloud.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, point)) for point in points]))
    cloud.CreateWidthsAttr(Vt.FloatArray([float(width) for width in widths]))
    stage.Save()
    return path


def finish(name):
    """A library surface's maps as library_demo.py lays them, at the surface's own tile size."""
    folder = entry_files(SURFACE[name])
    record = json.loads((folder / "surface.json").read_text())
    given = {"colour": str(folder / "colour.jpg"), "metre": record["tile_metres"]}
    for key in ("roughness", "normal", "metalness"):
        if (folder / f"{key}.jpg").is_file():
            given[key] = str(folder / f"{key}.jpg")
    return given


def sphere(path, radius=0.5, rings=64):
    """A UV sphere as PLY: the surface's swatch."""
    points = [(radius * numpy.sin(numpy.pi * ring / rings) * numpy.cos(numpy.pi * step / rings),
               radius * numpy.sin(numpy.pi * ring / rings) * numpy.sin(numpy.pi * step / rings),
               radius * numpy.cos(numpy.pi * ring / rings)) for ring in range(rings + 1) for step in range(2 * rings)]
    around = 2 * rings
    faces = [[ring * around + step, ring * around + (step + 1) % around, (ring + 1) * around + (step + 1) % around,
              (ring + 1) * around + step] for ring in range(rings) for step in range(around)]
    write_ply(path, numpy.array(points), faces)
    return path


def kit_corner(work):
    """The kit corner's files: every piece split into its parts, each part finished, decals left out."""
    files = []
    for piece, (x, y), turn, floor in KIT_CORNER:
        address = f"kit/quaternius_scifi_{piece}@1"
        parts = work / "kit" / piece
        if not parts.is_dir():
            split_parts(entry_files(address) / "piece.usdc", parts)
        for part in sorted(parts.glob("*.ply")):
            if "Decal" in part.stem:
                continue
            given = {"path": str(part), "at": [x, y, 0.0], "turn": turn}
            if part.stem == "M_Glass":
                given["glass"] = True
            else:
                given["finish"] = finish(floor or KIT_FINISH[part.stem])
            files.append(given)
    return files


def linear(hex_colour):
    channels = [int(hex_colour[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    return [((value + 0.055) / 1.055) ** 2.4 if value > 0.04045 else value / 12.92 for value in channels]


def dome_files(work):
    """score's dome_shell run here (one opening, 6 m), split into its parts and finished."""
    from score.stages.place_build import dome_shell
    usd = work / "dome.usda"
    dome_shell.shell(usd, 6.0, openings=((0.0, 1.6, 1.6),))
    split_parts(usd, work / "dome")
    looks = {"shell": {"glass": True}, "ribs": {"finish": finish("ambientcg_diamondplate008a")},
             "base": {"finish": finish("ambientcg_concrete046")}, "deck": {"finish": finish("ambientcg_concrete046")}}
    return [{"path": str(work / "dome" / f"{part}.ply"), **look} for part, look in looks.items()]


def staged_items(work):
    """Every 3D picture's item for library_demo.py."""
    rover = entry_files(PICKS["model"])
    person = entry_files(PICKS["character"], only=("body.glb", ".png"))
    kettle = entry_files("model/kettle_1.flat@2")
    steam = steam_points(entry_files(PICKS["effect"]) / "clip.usdc", kettle / "kettle_1.gltf", work / "steam.npz")
    lamp = entry_files("model/polyhaven_caged_hanging_light@1")
    take = entry_files(PICKS["take"], only=("-final.glb",))
    corner = kit_corner(work)
    return [
        {"name": "model", "files": [str(rover / "tracked_rover_1.gltf")], "heading": 40, "elevation": 16},
        {"name": "surface", "files": [{"path": str(sphere(work / "sphere.ply")),
                                       "finish": finish("ambientcg_diamondplate008a")}],
         "heading": 30, "elevation": 15, "margin": 1.1},
        {"name": "kit", "files": corner, "heading": 35, "elevation": 16, "margin": 0.85},
        {"name": "character", "files": [str(person / "body.glb")], "hide": ["far", "Icosphere"],
         "action": "walking", "frame": 6, "heading": 200, "elevation": 6, "lens": 85, "margin": 0.95},
        {"name": "effect", "files": [str(kettle / "kettle_1.gltf")],
         "points": [{"npz": str(steam), "usd": str(steam.with_suffix(".usda")), "look": "puff"}],
         "ground": "dark", "heading": -30, "elevation": 10, "margin": 1.2},
        {"name": "light", "ground": "dark", "studio": 0.06, "heading": 35, "elevation": 16, "margin": 0.85,
         "files": corner + [{"path": str(lamp / "model.usdc"), "at": [0.9, 1.6, 2.75],
                             "finish": finish("ambientcg_rubber004")}],
         "lamps": [{"type": "POINT", "at": [0.9, 1.6, 2.3], "watts": 400, "colour": [1.0, 0.85, 0.62], "size": 0.08},
                   {"type": "SPOT", "at": [3.6, -2.2, 3.4], "aim": [-0.4, 3.2, 1.2], "watts": 3000,
                    "cone": SPOT_ANGLE, "blend": 0.2, "colour": linear(SPOT_COLOUR), "size": 0.04}]},
        {"name": "algorithm", "ground": "dark", "heading": 30, "elevation": 14, "files": dome_files(work)},
        {"name": "take", "files": [str(next(take.glob("*-final.glb")))], "heading": 40, "elevation": 16},
    ]


def flat_pictures(out):
    """The concept, the place and the sound from the pictures their entries hold, in the README's 4:3."""
    held = {"concept": entry_files(PICKS["concept"], only=("concept.png",)) / "concept.png",
            "place": entry_files(PICKS["place"], only=("render.png",)) / "render.png",
            "sound": entry_files(PICKS["sound"], only=("preview.png",)) / "preview.png"}
    for kind, path in held.items():
        to_jpeg(path, out / f"{kind}.jpg", whole=kind == "sound")


def to_jpeg(path, target, whole=False):
    """A picture in the README's 4:3 at its width: cut round its middle, or `whole` (a sound's wave, whose ends
    matter) fitted inside and padded with its own corner colour."""
    if whole:
        shape = (f"scale={JPEG_WIDTH}:{JPEG_WIDTH * 3 // 4}:force_original_aspect_ratio=decrease,"
                 f"pad={JPEG_WIDTH}:{JPEG_WIDTH * 3 // 4}:(ow-iw)/2:(oh-ih)/2:color={corner_colour(path)}")
    else:
        shape = f"crop='min(iw,ih*4/3)':'min(ih,iw*3/4)',scale={JPEG_WIDTH}:-2"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vf", shape, "-q:v", "3", str(target)],
                   check=True)


def corner_colour(path):
    """The colour of a picture's top-left pixel as ffmpeg's 0xRRGGBB."""
    done = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf", "crop=1:1:0:0", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    return "0x" + done.stdout[:3].hex()


def all_inputs(items):
    """Every file and folder the render reads, for the cloud machine."""
    found = set()
    for item in items:
        for given in item["files"]:
            path = pathlib.Path(given["path"] if isinstance(given, dict) else given)
            found.add(path.parent)
            look = given.get("finish") if isinstance(given, dict) else None
            found.update(pathlib.Path(value).parent for key, value in (look or {}).items() if key != "metre")
        found.update(pathlib.Path(spec["npz"]).parent for spec in item.get("points", []))
    return sorted(found)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--work", type=pathlib.Path, help="a scratch folder (default: <out>/../demo-work)")
    parser.add_argument("--who", default="library demo pictures")
    parser.add_argument("--here", action="store_true",
                        help="render on this PC's processor through session.py batch, not in the cloud")
    parser.add_argument("--prepare", action="store_true", help="fetch and prepare the job only, render nothing")
    given = parser.parse_args()
    out = given.out.resolve()
    work = (given.work or out.parent / "demo-work").resolve()
    renders = work / "renders"
    for folder in (out, work, renders):
        folder.mkdir(parents=True, exist_ok=True)
    items = staged_items(work)
    job = work / "job.json"
    job.write_text(json.dumps({"size": list(SIZE), "samples": SAMPLES, "items": items}, indent=1))
    if given.prepare:
        print(f"demo pictures: job for {len(items)} renders at {job}")
        return
    outputs = [renders / f"{item['name']}.png" for item in items]
    if given.here:
        subprocess.run([sys.executable, str(REPO / "tools/blender/session.py"), "batch", "--version", LOCAL_BLENDER, "--wait", "1800",
                        str(INSIDE), "--", str(job), str(renders)], check=True)
    else:
        sys.path.insert(0, str(REPO / "tools/cloud"))
        import blender_cloud
        blender_cloud.run_elsewhere(INSIDE, [job, renders], [job, *all_inputs(items)], outputs, CLASSES, given.who,
                                    minutes=20)
    missing = [path.name for path in outputs if not path.is_file()]
    if missing:
        raise SystemExit(f"the render made no {missing}")
    for path in outputs:
        to_jpeg(path, out / f"{path.stem}.jpg")
    flat_pictures(out)
    print(f"demo pictures: {len(outputs) + 3} written to {out}")


if __name__ == "__main__":
    main()
