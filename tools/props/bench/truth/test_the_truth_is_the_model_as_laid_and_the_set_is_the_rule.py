"""The truth of an adopted model is the model as NVIDIA stands it (metres, Z up, its instances flattened, each triangle's
material and library surface, each triangle's look on NVIDIA's material (#172), its rigid bodies' mass, each
payload's colliders as its simulator collides with them,
its physics material and friction), and the set is #162's rule.

The fixture is a tiny library (SCORE_LIB_ROOT for the records, SCORE_LIB_FILES for the files): one adopted model
authored Z-up in centimetres, and a dozen records for the rule. Its model, worked by hand:
- `Body1` is an instance (translated 300 cm along x) of `Part` in a second file: one mesh of two closed boxes, A
  [0, 100] x [0, 200] x [0, 50] cm and B [150, 200] x [0, 200] x [0, 50] cm (B's six quads a subset bound to `metal`,
  the rest to the mesh's `paint`), colliding by its convex hull, mass 2 on the mesh. `Body2` is a 10 cm cube at the
  origin, its own body mass 5 over its mesh's 1, drawn with `plain` (no library surface); its collider authors
  convexDecomposition under Newton (its variant) and no approximation under MuJoCo.
- Looks (#172): the shell's paint is a UsdPreviewSurface whose colour is a 2 x 2 sRGB map read at (0.25, 0.75), its
  top left texel (188, 0, 0): linear 0.5029 red, metal 0 (the fallback), roughness 0.6; its metal a constant grey 0.5,
  metal 1, roughness 0.2, of class metal by its name (m_opaque__metal__...); `plain` has no shader: NaN.
- In metres, Z up: x 0 to 5, y 0 to 2, z 0 to 0.5. Volume 1.0 + 0.5 + 0.001 = 1.501
  m^3 (positive: outward wound). Triangles: paint 12, metal 12, the cube's 12. Mass 2 + 5 = 7 (a body's own mass wins).
- Joints (#177): `hinge` joins Body1 (body0) and Body2 about its Z turned 90 degrees about x (the world's -y), at
  (0, 0, 50) cm in Body1's frame (translated 300 cm): pivot (3.0, 0, 0.5) m, limits -10 to 80 degrees. The shell's 24
  triangles are Body1's, the cube's 12 Body2's.
- Colliders: the shell's hull is [3, 5] x [0, 2] x [0, 0.5], 2.0 m^3 (its mesh is 1.5); under Newton the cube is
  its own mesh (not convex: the simulator cuts it at load), under MuJoCo its hull (MuJoCo hulls every mesh), both
  0.001 m^3. The rubber binds static friction 0.9; the shell (its instance's binding) touches with steel's 0.5, so the
  friction is (0.5 x 2.0 + 0.9 x 0.001) / 2.001 = 1.0009 / 2.001 = 0.5002 (unweighted it would be 0.7).
- The rule's box kind, in sha256("r162:" + id) order: box_tall_a01 (1b3b), box_blue_a01 (20b8), box_wide_a01 (27b3),
  box_red_a01 (3278), box_wide_b02 (3283, its stem taken: skipped), box_tiny_a01 (ba8f), box_flat_a01 (d865, a sixth);
  box_blue_a01 at its newest version 2; bigbox (no word start), carton (no word), box_old (withdrawn) and
  box_cls (first class crate) never match. The desk kind: desk_a01 is the overlap target (old_desk_1 withdrawn into
  it), so desk_a02 (11fb, its stem) is skipped and desk_oak_a01 (208f) picked.
- The named groups (#159), the fixture's own tables: the detailed machine kind names box_flat_a01 (no kind took it:
  tune) and box_blue_a01 (the box kind took it: not repeated); the pictured dial case keeps its id, its material, its
  2099 make and the palette's never-picks, with no address.

Breaks (each applied once, seen red, reverted), in `_read.py` and `_pick.py`: the stage's metersPerUnit ignored (box,
volume, colliders), `TraverseInstanceProxies` dropped (box, volume, materials: the shell is not read), the winding
never turned for a left-handed mesh (volume, colliders), material subsets ignored (materials), a body's own mass not
preferred (mass), the friction not weighted by collider volume (friction), the payload variants not set (colliders),
MuJoCo colliders not hulled (colliders), the drop's colliders taken from Newton (colliders), a joint's localRot0 or its body0's transform not applied, or its face's body not walked up its path
(joints), the salt changed (box
picks), the stem skip dropped (box picks), a surface's `painted_for` tag not read (one model), the newest version not taken (box picks), the overlap targets' stems
not taken first (desk picks), the detailed skip of an id the rule took dropped (detailed picks), the never-picks not
given a pictured case (pictured cases); in `_look.py` the sRGB map not made linear, v not turned up (the bottom row
read) and the class not read from the material's name (looks).
"""
import json
import pathlib

import numpy as np
import pytest
import trimesh

from tools.props.bench import truth

SHELL_POINTS = [(x, y, z) for x0, x1 in ((0, 100), (150, 200)) for x in (x0, x1) for y in (0, 200) for z in (0, 50)]
# A box's corners indexed 4x + 2y + z; its six quads outward when read left-handed (each right-handed one reversed).
BOX_QUADS = [2, 3, 1, 0, 5, 7, 6, 4, 1, 5, 4, 0, 6, 7, 3, 2, 4, 6, 2, 0, 3, 7, 5, 1]
CUBE = [(x, y, z) for x in (0, 10) for y in (0, 10) for z in (0, 10)]


def points(listed):
    return ", ".join(f"({x}, {y}, {z})" for x, y, z in listed)


GEOMETRY = f'''#usda 1.0
def Xform "Part"
{{
    def Mesh "shell" (prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI", "PhysicsMeshCollisionAPI",
                                            "PhysicsMassAPI"])
    {{
        uniform token orientation = "leftHanded"
        point3f[] points = [{points(SHELL_POINTS)}]
        int[] faceVertexCounts = [{", ".join(["4"] * 12)}]
        int[] faceVertexIndices = {BOX_QUADS + [index + 8 for index in BOX_QUADS]}
        texCoord2f[] primvars:st = [{", ".join(["(0.25, 0.75)"] * 24 + ["(0.75, 0.25)"] * 24)}] (
            interpolation = "faceVarying"
        )
        rel material:binding = </Part/Looks/paint>
        uniform token physics:approximation = "convexHull"
        float physics:mass = 2
        def GeomSubset "metal_faces" (prepend apiSchemas = ["MaterialBindingAPI"])
        {{
            uniform token elementType = "face"
            uniform token familyName = "materialBind"
            int[] indices = [6, 7, 8, 9, 10, 11]
            rel material:binding = </Part/Looks/m_opaque__metal__shell>
        }}
    }}
    def Scope "Looks"
    {{
        def Material "paint"
        {{
            custom uniform string score:surface = "surface/paint@1"
            token outputs:surface.connect = </Part/Looks/paint/surface.outputs:surface>
            def Shader "surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </Part/Looks/paint/map.outputs:rgb>
                float inputs:roughness = 0.6
                token outputs:surface
            }}
            def Shader "map"
            {{
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @./paint.png@
                token inputs:sourceColorSpace = "sRGB"
                float3 outputs:rgb
            }}
        }}
        def Material "m_opaque__metal__shell"
        {{
            custom uniform string score:surface = "surface/metal@1"
            token outputs:surface.connect = </Part/Looks/m_opaque__metal__shell/surface.outputs:surface>
            def Shader "surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.5, 0.5, 0.5)
                float inputs:metallic = 1
                float inputs:roughness = 0.2
                token outputs:surface
            }}
        }}
    }}
}}
'''

ROOT = f'''#usda 1.0
(
    defaultPrim = "RootNode"
    metersPerUnit = 0.01
    upAxis = "Z"
)
def Xform "RootNode" (
    variants = {{
        string MuJoCo = "Disabled"
        string Newton = "Disabled"
    }}
    prepend variantSets = ["MuJoCo", "Newton"]
)
{{
    def Xform "Body1" (
        instanceable = true
        prepend references = @./geometry.usda@</Part>
        prepend apiSchemas = ["PhysicsRigidBodyAPI", "MaterialBindingAPI"]
    )
    {{
        double3 xformOp:translate = (300, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding:physics = </RootNode/Physics/steel>
    }}
    def Xform "Body2" (prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"])
    {{
        float physics:mass = 5
        def Mesh "block" (prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI", "PhysicsMeshCollisionAPI",
                                                "PhysicsMassAPI"])
        {{
            uniform token orientation = "leftHanded"
            point3f[] points = [{points(CUBE)}]
            int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
            int[] faceVertexIndices = {BOX_QUADS}
            float physics:mass = 1
            rel material:binding = </RootNode/Looks/plain>
            rel material:binding:physics = </RootNode/Physics/rubber>
        }}
    }}
    def PhysicsRevoluteJoint "hinge"
    {{
        rel physics:body0 = </RootNode/Body1>
        rel physics:body1 = </RootNode/Body2>
        uniform token physics:axis = "Z"
        point3f physics:localPos0 = (0, 0, 50)
        quatf physics:localRot0 = (0.70710677, 0.70710677, 0, 0)
        float physics:lowerLimit = -10
        float physics:upperLimit = 80
    }}
    def Scope "Looks"
    {{
        def Material "plain"
        {{
        }}
    }}
    def Scope "Physics"
    {{
        def Material "rubber" (prepend apiSchemas = ["PhysicsMaterialAPI"])
        {{
            float physics:staticFriction = 0.9
            float physics:dynamicFriction = 0.8
            float physics:restitution = 0.1
            float physics:density = 1100
        }}
        def Material "steel" (prepend apiSchemas = ["PhysicsMaterialAPI"])
        {{
            float physics:staticFriction = 0.5
        }}
    }}
    variantSet "MuJoCo" = {{
        "Disabled" {{
        }}
        "Enabled" {{
        }}
    }}
    variantSet "Newton" = {{
        "Disabled" {{
        }}
        "Enabled" {{
            over "Body2"
            {{
                over "block"
                {{
                    uniform token physics:approximation = "convexDecomposition"
                }}
            }}
        }}
    }}
}}
'''


def record(entry_id, version=1, classes=("box",), state="draft", replaced_by=None, files=None):
    found = {"schema": "score-lib-entry/1", "kind": "model", "id": entry_id, "version": version,
             "address": f"model/{entry_id}@{version}", "state": state, "title": entry_id,
             "tags": {"wikidata_class": list(classes), "description": [f"a {entry_id}"]},
             "files": files or {}, "usd": {"root": "root.usda", "up_axis": "Z", "meters_per_unit": 0.01}}
    if replaced_by:
        found["replaced_by"] = replaced_by
    return found


RECORDS = [record("simready_box_tall_a01"), record("simready_box_blue_a01"), record("simready_box_blue_a01", 2),
           record("simready_box_wide_a01"), record("simready_box_red_a01"), record("simready_box_wide_b02"),
           record("simready_box_tiny_a01"), record("simready_box_flat_a01"), record("simready_bigbox_a01"),
           record("simready_carton_a01"), record("simready_box_old_a01", state="withdrawn"),
           record("simready_box_cls_a01", classes=("crate", "box")), record("simready_desk_a01", classes=("desk",)),
           record("simready_desk_a02", classes=("desk",)), record("simready_desk_oak_a01", classes=("desk",)),
           record("old_desk_1", state="withdrawn", replaced_by="model/simready_desk_a01@1"),
           record("simready_shell_a01", classes=("thing",),
                  files={"root.usda": {"role": "usd"}, "geometry.usda": {"role": "usd"},
                         "paint.png": {"role": "texture"}})]
# The paint's map, 2 x 2 texels, sRGB: its top row (v 0.5 to 1) dark red then blue, its bottom row green then white.
# The shell's paint quads read it at (0.25, 0.75): the top left, sRGB 188 red, linear 0.5029.
PAINT_TEXELS = [[(188, 0, 0), (0, 0, 255)], [(0, 255, 0), (255, 255, 255)]]


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root, files = tmp_path_factory.mktemp("score_lib"), tmp_path_factory.mktemp("files")
    for item in RECORDS:
        folder = root / "entries/model" / item["id"] / str(item["version"])
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps(item))
    (root / "index").mkdir()
    (root / "index/surface.json").write_text(json.dumps({"schema": "score-lib-index/1", "kind": "surface", "entries": [
        {"address": "surface/paint@1", "tags": {}},
        {"address": "surface/metal@1", "tags": {"painted_for": ["shell_a01"]}}]}))
    model = files / "model/simready_shell_a01@1"
    model.mkdir(parents=True)
    (model / "root.usda").write_text(ROOT)
    (model / "geometry.usda").write_text(GEOMETRY)
    from PIL import Image
    Image.fromarray(np.array(PAINT_TEXELS, dtype=np.uint8)).save(model / "paint.png")
    patch = pytest.MonkeyPatch()
    patch.setenv("SCORE_LIB_ROOT", str(root))
    patch.setenv("SCORE_LIB_FILES", str(files))
    found = truth.read("model/simready_shell_a01@1")
    from tools.props.bench.truth import _pick
    patch.setattr(_pick, "DETAILED", {"simready_box_flat_a01": "machine", "simready_box_blue_a01": "machine"})
    patch.setattr(_pick, "PICTURED", {"dial": ("metal", ["model/dial_1@1"], {
        "closeup": "c0ffee", "size": [0.05, 0.02, 0.05], "size_from": "a test", "words": "a dial", "labels": ["ON"],
        "classes": ["metal"]})})
    picks = truth.picked(root, "abc")["objects"]
    patch.undo()
    return found, picks


def materials(found):
    return {found["materials"][index]["surface"] if index >= 0 else "unbound": int(count)
            for index, count in zip(*np.unique(found["face_material"], return_counts=True))}


def looks(found):
    """{surface: (its faces' albedo, metal, roughness, as read; its class)}, NaN read as None."""
    look = found["face_look"]
    held = {}
    for index, item in enumerate(found["materials"] + [None]):
        faces = np.asarray(found["face_material"]) == (index if item else -1)
        if not faces.any():
            continue
        values = [sorted({None if np.isnan(value) else round(float(value), 4) for value in look[key][faces].ravel()})
                  for key in ("albedo", "metal", "roughness")]
        held[item["surface"] if item else "unbound"] = (*values, sorted({str(name) for name in look["class"][faces]}))
    return held


def colliders(found):
    return {key: [(shape["approximation"], shape["convex"],
                   round(float(trimesh.Trimesh(shape["vertices"], shape["faces"]).volume), 4)) for shape in shapes]
            for key, shapes in {**found["payloads"], "drop": found["colliders"]}.items()}


def picks_of(picks, kind):
    return [(item["address"].split("/")[1].replace("simready_", ""), item["split"], item["withdrawn"])
            for item in picks if item["kind"] == kind]


ROWS = [
    ("box", lambda found, picks: [[round(value, 4) + 0.0 for value in side] for side in found["box"]],
     [[0.0, 0.0, 0.0], [5.0, 2.0, 0.5]]),
    ("volume", lambda found, picks: round(float(trimesh.Trimesh(found["vertices"], found["faces"]).volume), 4), 1.501),
    ("materials", lambda found, picks: materials(found), {"surface/paint@1": 12, "surface/metal@1": 12, None: 12}),
    ("one model", lambda found, picks: {item["surface"]: item["one_model"] for item in found["materials"]},
     {"surface/paint@1": False, "surface/metal@1": True, None: False}),
    ("looks", lambda found, picks: looks(found),
     {"surface/paint@1": ([0.0, 0.5029], [0.0], [0.6], ["None"]),
      "surface/metal@1": ([0.5], [1.0], [0.2], ["metal"]), None: ([None], [None], [None], ["None"])}),
    ("mass", lambda found, picks: (found["mass"], [body["mass"] for body in found["bodies"]]), (7.0, [2.0, 5.0])),
    ("colliders", lambda found, picks: colliders(found),
     {"newton": [("convexHull", True, 2.0), ("convexDecomposition", False, 0.001)],
      "mujoco": [("convexHull", True, 2.0), ("none", True, 0.001)],
      "drop": [("convexHull", True, 2.0), ("none", True, 0.001)]}),
    ("physics material", lambda found, picks: {key: {name: round(value["static_friction"], 3) for name, value in
                                                      held.items()} for key, held in
                                                found["physics_materials"].items()},
     {key: {"/RootNode/Physics/rubber": 0.9, "/RootNode/Physics/steel": 0.5} for key in ("newton", "mujoco")}),
    ("friction", lambda found, picks: round(found["friction"], 4), 0.5002),
    ("joints", lambda found, picks: ([{key: (np.round(value, 4) + 0.0).tolist() if key in ("pivot", "axis") else value
                                        for key, value in joint.items()} for joint in found["joints"]],
                                      dict(zip(*(values.tolist() for values in np.unique(found["face_body"],
                                                                                         return_counts=True))))),
     ([{"prim": "/RootNode/hinge", "type": "PhysicsRevoluteJoint", "body0": 0, "body1": 1, "pivot": [3.0, 0.0, 0.5],
        "axis": [0.0, -1.0, 0.0], "limits": [-10.0, 80.0]}], {0: 24, 1: 12})),
    ("box picks", lambda found, picks: picks_of(picks, "box"),
     [("box_tall_a01@1", "tune", []), ("box_blue_a01@2", "tune", []), ("box_wide_a01@1", "tune", []),
      ("box_red_a01@1", "held-out", []), ("box_tiny_a01@1", "held-out", [])]),
    ("desk picks", lambda found, picks: picks_of(picks, "desk / table / bench") + picks_of(picks, "overlap"),
     [("desk_oak_a01@1", "tune", []), ("desk_a01@1", "tune", ["model/old_desk_1@1"])]),
    ("detailed picks", lambda found, picks: picks_of(picks, "machine"), [("box_flat_a01@1", "tune", [])]),
    ("pictured cases", lambda found, picks: [(item["id"], "address" in item, item["split"], item["material"],
                                              item["made_before"], item["picture"]["never"])
                                             for item in picks if item["kind"] == "cockpit"],
     [("cockpit_dial", False, "tune", "metal", ["model/dial_1@1"], ["cloth", "beta_cloth", "rusted_metal"])]),
]


@pytest.mark.parametrize("name, observed, expected", ROWS, ids=[row[0] for row in ROWS])
def test_the_truth_is_the_model_as_laid_and_the_set_is_the_rule(made, name, observed, expected):
    assert observed(*made) == expected, name
