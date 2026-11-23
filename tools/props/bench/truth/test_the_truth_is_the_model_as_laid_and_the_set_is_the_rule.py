"""The truth of an adopted model is the model as NVIDIA stands it (metres, Z up, its instances flattened, each triangle's
material and library surface, its rigid bodies' mass, each payload's colliders as its simulator collides with them,
its physics material and friction), and the set is #162's rule.

The fixture is a tiny library (SCORE_LIB_ROOT for the records, SCORE_LIB_FILES for the files): one adopted model
authored Z-up in centimetres, and a dozen records for the rule. Its model, worked by hand:
- `Body1` is an instance (translated 300 cm along x) of `Part` in a second file: one mesh of two closed boxes, A
  [0, 100] x [0, 200] x [0, 50] cm and B [150, 200] x [0, 200] x [0, 50] cm (B's six quads a subset bound to `metal`,
  the rest to the mesh's `paint`), colliding by its convex hull, mass 2 on the mesh. `Body2` is a 10 cm cube at the
  origin, its own body mass 5 over its mesh's 1, drawn with `plain` (no library surface); its collider authors
  convexDecomposition under Newton (its variant) and no approximation under MuJoCo.
- In metres, Z up: x 0 to 5, y 0 to 2, z 0 to 0.5. Volume 1.0 + 0.5 + 0.001 = 1.501
  m^3 (positive: outward wound). Triangles: paint 12, metal 12, the cube's 12. Mass 2 + 5 = 7 (a body's own mass wins).
- Colliders: the shell's hull is [3, 5] x [0, 2] x [0, 0.5], 2.0 m^3 (its mesh is 1.5); under Newton the cube is
  its own mesh (not convex: the simulator cuts it at load), under MuJoCo its hull (MuJoCo hulls every mesh), both
  0.001 m^3. The rubber binds static friction 0.9; the shell (its instance's binding) touches with steel's 0.5, so the
  friction is (0.5 x 2.0 + 0.9 x 0.001) / 2.001 = 1.0009 / 2.001 = 0.5002 (unweighted it would be 0.7).
- The rule's box kind, in sha256("r162:" + id) order: box_tall_a01 (1b3b), box_blue_a01 (20b8), box_wide_a01 (27b3),
  box_red_a01 (3278), box_wide_b02 (3283, its stem taken: skipped), box_tiny_a01 (ba8f), box_flat_a01 (d865, a sixth);
  box_blue_a01 at its newest version 2; bigbox (no word start), carton (no word), box_old (withdrawn) and
  box_cls (first class crate) never match. The desk kind: desk_a01 is the overlap target (old_desk_1 withdrawn into
  it), so desk_a02 (11fb, its stem) is skipped and desk_oak_a01 (208f) picked.

Breaks (each applied once, seen red, reverted), in `_read.py` and `_pick.py`: the stage's metersPerUnit ignored (box,
volume, colliders), `TraverseInstanceProxies` dropped (box, volume, materials: the shell is not read), the winding
never turned for a left-handed mesh (volume, colliders), material subsets ignored (materials), a body's own mass not
preferred (mass), the friction not weighted by collider volume (friction), the payload variants not set (colliders),
MuJoCo colliders not hulled (colliders), the drop's colliders taken from Newton (colliders), the salt changed (box
picks), the stem skip dropped (box picks), the newest version not taken (box picks), the overlap targets' stems
not taken first (desk picks).
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
        rel material:binding = </Part/Looks/paint>
        uniform token physics:approximation = "convexHull"
        float physics:mass = 2
        def GeomSubset "metal_faces" (prepend apiSchemas = ["MaterialBindingAPI"])
        {{
            uniform token elementType = "face"
            uniform token familyName = "materialBind"
            int[] indices = [6, 7, 8, 9, 10, 11]
            rel material:binding = </Part/Looks/metal>
        }}
    }}
    def Scope "Looks"
    {{
        def Material "paint"
        {{
            custom uniform string score:surface = "surface/paint@1"
        }}
        def Material "metal"
        {{
            custom uniform string score:surface = "surface/metal@1"
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
                  files={"root.usda": {"role": "usd"}, "geometry.usda": {"role": "usd"}})]


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    root, files = tmp_path_factory.mktemp("score_lib"), tmp_path_factory.mktemp("files")
    for item in RECORDS:
        folder = root / "entries/model" / item["id"] / str(item["version"])
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps(item))
    model = files / "model/simready_shell_a01@1"
    model.mkdir(parents=True)
    (model / "root.usda").write_text(ROOT)
    (model / "geometry.usda").write_text(GEOMETRY)
    patch = pytest.MonkeyPatch()
    patch.setenv("SCORE_LIB_ROOT", str(root))
    patch.setenv("SCORE_LIB_FILES", str(files))
    found = truth.read("model/simready_shell_a01@1")
    picks = truth.picked(root, "abc")["objects"]
    patch.undo()
    return found, picks


def materials(found):
    return {found["materials"][index]["surface"] if index >= 0 else "unbound": int(count)
            for index, count in zip(*np.unique(found["face_material"], return_counts=True))}


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
    ("box picks", lambda found, picks: picks_of(picks, "box"),
     [("box_tall_a01@1", "tune", []), ("box_blue_a01@2", "tune", []), ("box_wide_a01@1", "tune", []),
      ("box_red_a01@1", "held-out", []), ("box_tiny_a01@1", "held-out", [])]),
    ("desk picks", lambda found, picks: picks_of(picks, "desk / table / bench") + picks_of(picks, "overlap"),
     [("desk_oak_a01@1", "tune", []), ("desk_a01@1", "tune", ["model/old_desk_1@1"])]),
]


@pytest.mark.parametrize("name, observed, expected", ROWS, ids=[row[0] for row in ROWS])
def test_the_truth_is_the_model_as_laid_and_the_set_is_the_rule(made, name, observed, expected):
    assert observed(*made) == expected, name
