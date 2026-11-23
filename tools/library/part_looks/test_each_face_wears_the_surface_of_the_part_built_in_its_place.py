"""part_looks: each face of a remade model wears the library surface of the part its old builder laid in that place,
the glowing parts' faces taken from the glow file, a face the old export cut into triangles otherwise than Blender
does now still told by its part, a printed plate printing its picture's library decal across its front as its
builder laid the picture, built as its room laid it (what the room's piece shows), and a model whose triangles lie off
its rebuild, cover its faces otherwise, or number other than it, or that prints a picture the library holds no decal
of, is refused, never guessed; a model whose old build cannot be recovered wears, face by face, the surface nearest
its atlas island's painted colour, an island on the atlas's unpainted black the surface of the nearest painted face.

Breaks (each applied once, seen red, reverted), in part_looks.py: parts_by_order without the glowing parts put after the
rest (the glow case's faces wear the wrong parts); TOLERANCE raised to 0.01 (the 1 mm case is made, not refused);
runs_of giving each triangle a run of its own, not its part's stretch (the square's triangles no longer have its border,
so the made cases are refused); faces_off without its edge_balance check (the square's one half twice is made);
SAME_CORNER set to 0 (the collapsed face whose corners are rounded apart is refused); refinished binding every subset to
the first look (a face wears another part's surface); refinished leaving the baked look and `st` on (the atlas is still
there); library_place returning the model's own place, not its surface data's `library` (the flat's models finished in a
place the old library does not hold); laid_of reading the piece's `laid` (empty in the kit rooms: the room's dome
gore built with no arc, every row red); content_coordinates taking the face's first corner for every corner (the
printed plate's st is not its builder's); looks_written without picture_wired (the printed look shows no picture);
undecalled returning without NoDecal (the plate with no decal is made in a blank look); island_colours keeping the
unpainted black (the far face wears the black rubber); regions_worn taking the first painted island for an unpainted
one, not the nearest face's (the far face wears red).
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from pxr import Sdf, Usd, UsdGeom, UsdShade

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import part_looks  # noqa: E402

SPECS = {name: {"recipe": recipe, "colour": colour, "hex": "#808080", "roughness": 0.4, "metal": 0.0, "wear": 0.4,
                "dirt": 0.4}
         for name, recipe, colour in (("dark_panel", "painted_metal", [0.02, 0.03, 0.03]),
                                      ("bare_steel", "bare_metal", [0.3, 0.3, 0.4]),
                                      ("led_amber", "glowing", [1.0, 0.4, 0.05]))}
SURFACES = {"painted_metal": "surface/painted_metal@1", "bare_metal": "surface/bare_metal@1",
            "glowing": "surface/glowing@1"}
PARTS = [["flange", "dark_panel"], ["dome", "led_amber"], ["body", "bare_steel"]]
PRINTED = {"recipe": "printed", "colour": [0.8, 0.8, 0.7], "hex": "#e0d8c0", "roughness": 0.6, "metal": 0.0,
           "wear": 0.4, "dirt": 0.4, "picture": "label_air_return"}
DECAL = "surface/label_air_return@2"
# The body's square as its builder laid the picture across it (shapes.content_plate's `content` map): one corner set
# per built face, None where the part has no picture.
CONTENTS = {"one face": [None, None, [[1.0, 0.0], [0.0, 0.0], [0.0, 1.0], [1.0, 1.0]], None],
            "a face collapsed": [None, None, [[1.0, 0.0], [0.0, 0.0], [0.0, 1.0], [1.0, 1.0]], None,
                                 [[0.0, 1.0], [0.0, 1.0], [1.0, 1.0]]]}
# A room as the kit wrote it at OLD_COMMIT: what each piece shows lies on the piece beside its place.
ROOM = {"room": "flat", "pieces": [
    {"kind": "flat_dome_gore", "model": "dome_gore_1", "at": [0, 0, 0], "size": [1, 1, 1], "layer": 1,
     "arc": {"half": 13.9}, "weather": 2, "near": True},
    {"kind": "hub_hatch_wall_surround", "model": "hatch_wall_surround_1", "at": [0, 0, 0], "size": [1, 1, 1],
     "z": [1.0, 0.0, 0.0], "taper": 1.0}]}
LAID = {"dome_gore_1": {"arc": {"half": 13.9}, "weather": 2},
        "hatch_wall_surround_1": {"taper": 1.0, "label": "label_west_hatch"}, "nowhere_1": None}


def baked(folder, name, triangles):
    """A baked model file as the old bake wrote it: one triangle mesh with st, bound to one atlas look."""
    stage = Usd.Stage.CreateNew(str(folder / f"{name}.usda"))
    root = UsdGeom.Xform.Define(stage, f"/{name}")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, f"/{name}/geo")
    mesh.CreatePointsAttr([tuple(corner) for triangle in triangles for corner in triangle])
    mesh.CreateFaceVertexCountsAttr([3] * len(triangles))
    mesh.CreateFaceVertexIndicesAttr(list(range(3 * len(triangles))))
    UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
    look = UsdShade.Material.Define(stage, f"/{name}/Looks/baked")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(look)
    return stage


def atlas_model(folder):
    """A baked model of three squares, each its own UV island: the first on the atlas's red, the second on its blue,
    the third on its unpainted black, laid beside the second."""
    stage = baked(folder, "regions", [])
    mesh = part_looks.mesh_of(stage)
    squares = [[[x, 0.0, 0.0], [x + 0.1, 0.0, 0.0], [x + 0.1, 0.1, 0.0], [x, 0.1, 0.0]] for x in (0.0, 1.0, 1.2)]
    mesh.CreatePointsAttr([tuple(corner) for square in squares for corner in square])
    mesh.CreateFaceVertexCountsAttr([4, 4, 4])
    mesh.CreateFaceVertexIndicesAttr(list(range(12)))
    islands = [[[u, v], [u + 0.2, v], [u + 0.2, v + 0.2], [u, v + 0.2]]
               for u, v in ((0.1, 0.7), (0.6, 0.7), (0.6, 0.1))]
    UsdGeom.PrimvarsAPI(mesh.GetPrim()).GetPrimvar("st").Set([tuple(corner) for island in islands for corner in island])
    atlas = np.zeros((64, 64, 3), dtype=np.uint8)
    atlas[:32, :32] = (200, 30, 30)  # the top left quarter red, the top right blue, the bottom unpainted
    atlas[:32, 32:] = (30, 40, 200)
    return stage, mesh, atlas


REGION_SURFACES = {"red_paint": {"colour": [0.6, 0.01, 0.01]}, "blue_paint": {"colour": [0.01, 0.02, 0.6]},
                   "black_rubber": {"colour": [0.01, 0.01, 0.01]}}


def triangle_at(x):
    return [[x, 0.0, 0.0], [x + 0.1, 0.0, 0.0], [x, 0.1, 0.0]]


QUAD = [[2.0, 0.0, 0.0], [2.1, 0.0, 0.0], [2.1, 0.1, 0.0], [2.0, 0.1, 0.0]]  # the body's one face, a square
# Built in the old join's order: flange, dome (glowing), body (its square in two triangles), flange again.
OUTLINES = [triangle_at(0.0), triangle_at(1.0), QUAD, triangle_at(3.0)]
# The square built with a face collapsed onto its edge (as a clamped bevel leaves one), its corners rounded a little
# apart from the square's; the model holds that face's triangle with the square's own corners.
COLLAPSED = [[QUAD[2][0] + 5e-8, QUAD[2][1], 0.0], [QUAD[2][0], QUAD[2][1] - 5e-8, 0.0], QUAD[3]]
BUILT = {"one face": ([0, 1, 2, 2, 0], [0, 1, 2, 2, 3], OUTLINES),
         "a face collapsed": ([0, 1, 2, 2, 2, 0], [0, 1, 2, 2, 4, 3], [*OUTLINES, COLLAPSED])}
# The body's square as the model may hold it: cut as built, cut along the other diagonal, or one half twice.
BODY = {"as built": [[QUAD[0], QUAD[1], QUAD[2]], [QUAD[0], QUAD[2], QUAD[3]]],
        "the other diagonal": [[QUAD[1], QUAD[3], QUAD[0]], [QUAD[1], QUAD[2], QUAD[3]]],
        "one half twice": [[QUAD[0], QUAD[1], QUAD[2]], [QUAD[0], QUAD[1], QUAD[2]]],
        "as built, the collapsed face too": [[QUAD[0], QUAD[1], QUAD[2]], [QUAD[0], QUAD[2], QUAD[3]],
                                             [QUAD[2], QUAD[2], QUAD[3]]]}


# The old surface data: the name the old library knew each place by.
LIBRARY_PLACES = {"flat": "prologue_flat", "airlock": "airlock"}


MADE = [["flange", "body", "body", "flange"], ["dome"]]


@pytest.mark.parametrize("case, place, built, body, shift, glow, printed, wanted", [
    ("exact", "flat", "one face", "as built", 0.0, True, None, MADE),
    ("off by 0.05 mm, within", "airlock", "one face", "as built", 5e-5, True, None, MADE),
    ("a square cut along its other diagonal", "flat", "one face", "the other diagonal", 0.0, True, None, MADE),
    ("a face collapsed, its corners rounded apart", "flat", "a face collapsed", "as built, the collapsed face too",
     0.0, True, None, [["flange", "body", "body", "body", "flange"], ["dome"]]),
    ("a printed plate wears its library decal", "flat", "one face", "the other diagonal", 0.0, True, DECAL, MADE),
    ("a printed plate the library holds no decal of", "flat", "one face", "as built", 0.0, True, "", "no decal"),
    ("off by 1 mm", "flat", "one face", "as built", 1e-3, True, None, "lie off"),
    ("a square's one half twice, the other uncovered", "airlock", "one face", "one half twice", 0.0, True, None,
     "not covered"),
    ("no glow file for a glowing part", "airlock", "one face", "as built", 0.0, False, None, "triangles"),
    ("a place the old surface data does not name", "nowhere", "one face", "as built", 0.0, True, None,
     "no surface data"),
    ("an unrecovered build worn by its atlas regions", "flat", "atlas", None, 0.0, True, None,
     ["red_paint", "blue_paint", "blue_paint"]),
])
def test_each_face_wears_the_surface_of_the_part_built_in_its_place(tmp_path, case, place, built, body, shift, glow,
                                                                    printed, wanted):
    (tmp_path / "data/kit").mkdir(parents=True)
    (tmp_path / "data/kit/flat.json").write_text(json.dumps(ROOM))
    assert {stem: part_looks.laid_of(tmp_path, "flat", stem) for stem in LAID} == LAID, case
    if built == "atlas":
        stage, mesh, atlas = atlas_model(tmp_path)
        islands, uvs, points = part_looks.face_islands(mesh)
        chosen = part_looks.nearest_variants(part_looks.island_colours(atlas, islands, uvs), REGION_SURFACES)
        assert part_looks.regions_worn(islands, points, chosen) == wanted, case
        return
    surfaces = tmp_path / "data/surfaces"
    surfaces.mkdir(parents=True)
    for name, library in LIBRARY_PLACES.items():
        (surfaces / f"{name}.json").write_text(json.dumps({"place": name, "library": library}))
    if place not in LIBRARY_PLACES:
        with pytest.raises(part_looks.Refused, match=wanted):
            part_looks.library_place(tmp_path, place)
        return
    assert part_looks.library_place(tmp_path, place) == LIBRARY_PLACES[place], case
    model = [[[value + (shift if axis == 1 else 0.0) for axis, value in enumerate(corner)] for corner in triangle]
             for triangle in [triangle_at(0.0), *BODY[body], triangle_at(3.0)]]
    stages = [baked(tmp_path, "model", model)] + ([baked(tmp_path, "model_glow", [triangle_at(1.0)])] if glow else [])
    counts = [len(part_looks.mesh_of(stage).GetFaceVertexCountsAttr().Get()) for stage in stages]
    triangles = np.vstack([part_looks.triangle_corners(part_looks.mesh_of(stage)) for stage in stages])
    order, polygons, outlines = BUILT[built]
    answer = {"parts": PARTS, "order": order, "polygons": polygons, "outlines": outlines}
    specs = dict(SPECS, bare_steel=dict(PRINTED, decal=printed)) if printed is not None else SPECS
    surfaces = dict(SURFACES, printed="surface/printed@1")
    try:
        by_file, _, lies = part_looks.parts_by_order(answer, counts, lambda surface: surface == "led_amber", triangles)
        coordinates = part_looks.content_coordinates(CONTENTS[built], lies)
        part_looks.undecalled([tuple(part) for part in PARTS], specs, np.concatenate(by_file), triangles,
                              coordinates)
    except part_looks.Refused as why:
        assert isinstance(wanted, str) and wanted in str(why), case
        return
    assert not isinstance(wanted, str), case
    worn, first = [], 0
    for stage, faces in zip(stages, by_file):
        part_looks.refinished(stage, [tuple(part) for part in PARTS], faces, specs, surfaces,
                              coordinates[first:first + len(faces)])
        first += len(faces)
        mesh = part_looks.mesh_of(stage)
        assert not stage.GetPrimAtPath(stage.GetDefaultPrim().GetPath().AppendPath("Looks/baked")), case
        st = UsdGeom.PrimvarsAPI(mesh.GetPrim()).GetPrimvar("st")
        body_faces = [index for index, part in enumerate(faces.tolist()) if PARTS[part][0] == "body"]
        if printed and body_faces:
            corners = np.array(st.Get()).reshape(-1, 3, 2)
            model_corners = part_looks.triangle_corners(mesh)
            for face in body_faces:  # the picture across the square: u from its right edge, v from its bottom
                for corner, uv in zip(model_corners[face], corners[face]):
                    assert np.allclose(uv, [(2.1 - corner[0]) / 0.1, corner[1] / 0.1], atol=1e-5), case
        else:
            assert not st, case
        shown = [None] * len(mesh.GetFaceVertexCountsAttr().Get())
        for subset in UsdShade.MaterialBindingAPI(mesh.GetPrim()).GetMaterialBindSubsets():
            look = UsdShade.MaterialBindingAPI(subset.GetPrim()).GetDirectBinding().GetMaterial()
            surface = look.GetPrim().GetAttribute("score:surface").Get()
            variant = look.GetPrim().GetAttribute("score:surface:variant").Get()
            assert surface == surfaces[specs[variant]["recipe"]], case
            assert json.loads(look.GetPrim().GetAttribute("score:recipe:spec").Get())["recipe"] == \
                specs[variant]["recipe"], case
            texture = stage.GetPrimAtPath(look.GetPath().AppendChild("print"))
            assert bool(texture) == bool(specs[variant].get("decal")), case
            if texture:
                assert look.GetPrim().GetAttribute("score:surface:decal").Get() == printed, case
                assert texture.GetAttribute("inputs:file").Get().path == "textures/bare_steel.png", case
            for face in subset.GetIndicesAttr().Get():
                shown[face] = (subset.GetPrim().GetName(), variant)
        worn.append([part for part, _ in shown])
        assert all(variant == dict(map(tuple, PARTS))[part] for part, variant in shown), case
    assert worn == wanted, case
