"""The USD correctness check (score/stages/complete/usd): SCORE's rule set passes a good stage, fails a bad one by
rule, its own triangle-collider rule fires only on a dynamic body, and a place's findings.json is written from a
store of the test's own."""
import json

from score.stages.complete.gaps.gaps_test import made, verdict
from score.stages.complete.usd import __main__ as check
from score.stages.complete.usd import judged, rules
from score.store import Store

CUBE = """
        point3f[] points = [(0,0,0), (1,0,0), (1,1,0), (0,1,0), (0,0,1), (1,0,1), (1,1,1), (0,1,1)]
        int[] faceVertexCounts = [4, 4, 4, 4, 4, 4]
        int[] faceVertexIndices = [0, 3, 2, 1, 4, 5, 6, 7, 0, 1, 5, 4, 2, 3, 7, 6, 1, 2, 6, 5, 0, 4, 7, 3]
"""
GOOD_MESH = CUBE + """
        float3[] extent = [(0, 0, 0), (1, 1, 1)]
        uniform token subdivisionScheme = "none"
        normal3f[] normals = [(0,0,-1), (0,0,-1), (0,0,-1), (0,0,-1), (0,0,1), (0,0,1), (0,0,1), (0,0,1)] (
            interpolation = "vertex"
        )
"""
GOOD = """#usda 1.0
(
    defaultPrim = "place"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "place"
{
    def Xform "crate" (
        prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]
    )
    {
        float physics:mass = 12
        def Mesh "geo" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"]
        )
        {""" + GOOD_MESH + """
            uniform token physics:approximation = "convexHull"
            rel material:binding = </place/Looks/paint>
        }
    }
    def Mesh "floor" (
        prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI"]
    )
    {""" + GOOD_MESH + """
        rel material:binding = </place/Looks/paint>
    }
    def Scope "Looks"
    {
        def Material "paint"
        {
            token outputs:surface.connect = </place/Looks/paint/surface.outputs:surface>
            def Shader "surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.5, 0.4, 0.3)
                token outputs:surface
            }
        }
    }
}
"""
BAD = """#usda 1.0

def Xform "place"
{
    def Xform "crate" (
        prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsMassAPI"]
        prepend references = @./missing.usda@
    )
    {
        float physics:mass = -3
        def Mesh "geo" (
            prepend apiSchemas = ["PhysicsCollisionAPI"]
        )
        {""" + CUBE + """
        }
    }
}

over "gone"
{
}
"""


def stage_of(tmp_path, text, name="place"):
    path = tmp_path / f"{name}.usda"
    path.write_text(text)
    return judged.opened(path)


def rules_hit(found, severity="error"):
    return {issue["rule"] for issue in found if issue["severity"] == severity}


def test_the_good_stage_has_no_error(tmp_path):
    found = judged.issues(stage_of(tmp_path, GOOD))
    assert rules_hit(found) == set(), [issue for issue in found if issue["severity"] == "error"]


def test_the_bad_stage_fails_by_each_rule_it_breaks(tmp_path):
    hit = rules_hit(judged.issues(stage_of(tmp_path, BAD)))
    for rule in ("DefaultPrimChecker", "StageMetadataChecker", "MissingReferenceChecker", "DanglingOverPrimChecker",
                 "ExtentsChecker", "MassChecker", "TriangleColliderOnDynamicBody"):
        assert rule in hit, (rule, hit)


def test_y_up_is_never_a_fault_and_the_rule_set_names_no_z_up_rule():
    assert "UpAxisZChecker" not in (*rules.ERRORS, *rules.WARNINGS)
    assert {rule.__name__ for rule in rules.engine().enabled_rules} >= {"StageMetadataChecker", "RigidBodyChecker"}


def test_a_triangle_collider_is_a_fault_only_on_a_dynamic_body(tmp_path):
    kinematic = BAD.replace("float physics:mass = -3", "bool physics:kinematicEnabled = 1")
    assert "TriangleColliderOnDynamicBody" not in rules_hit(judged.issues(stage_of(tmp_path, kinematic)))
    hull = GOOD.replace('"convexHull"', '"none"')
    assert "TriangleColliderOnDynamicBody" in rules_hit(judged.issues(stage_of(tmp_path, hull)))
    switched_off = hull.replace('uniform token physics:approximation = "none"',
                                'uniform token physics:approximation = "none"\n            bool physics:collisionEnabled = 0')
    assert "TriangleColliderOnDynamicBody" not in rules_hit(judged.issues(stage_of(tmp_path, switched_off)))


def test_a_warning_rule_never_fails_the_place(tmp_path):
    found = judged.issues(stage_of(tmp_path, GOOD))
    written = check.written_for("place", "assembly@place", "out", found + [
        {"rule": "ManifoldChecker", "severity": "warning", "message": "2 edges are non-manifold.", "prim": "/x"}])
    assert written["answer"] == "pass" and written["counts"]["warning"] >= 1 and written["findings"] == []


def test_findings_group_one_rule_and_message_into_one_problem():
    found = [{"rule": "DanglingOverPrimChecker", "severity": "error", "message": "dangling", "prim": f"/p/{n}"}
             for n in range(107)]
    groups = judged.grouped(found)
    assert len(groups) == 1 and groups[0]["count"] == 107 and len(groups[0]["prims"]) == judged.SAMPLES
    assert groups[0]["sentence"].startswith("107 x DanglingOverPrimChecker")


def test_a_place_is_judged_on_its_accepted_assembly_from_the_store(tmp_path):
    store = Store.in_folder(tmp_path / "store")
    output = made(store, tmp_path / "made", "assembly@place", {"place.usda": BAD},
                  {"made": verdict("made", "pass")})
    written = check.judged_place(store, "place", tmp_path / "out" / "place")
    on_disk = json.loads((tmp_path / "out/place/findings.json").read_text())
    assert on_disk == written and written["answer"] == "fail"
    assert written["outputs"] == {"assembly@place": output}
    assert check.judged_place(store, "nowhere", tmp_path / "out/nowhere")["answer"] == "unknown"
