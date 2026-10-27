"""The USD correctness check (score/stages/complete/usd): SCORE's rule set passes a good stage (Y up, metres), fails a
bad one by each rule it breaks, its own triangle-collider rule fires only on a dynamic body, a warning rule never
fails the place, a rule's many findings are one problem, and a place's findings.json is judged from its accepted
assembly in a store of the test's own.

Breaks that turn each test red (each applied once and seen red, 2026-10-27):
- test_the_good_stage_has_no_error: rules.py's ERRORS given "UpAxisZChecker" first (SCORE's Y up made a fault).
- test_the_bad_stage_fails_by_each_rule_it_breaks: rules.py's ERRORS without "ExtentsChecker".
- test_a_triangle_collider_is_a_fault_only_on_a_dynamic_body: rules.dynamic_body's
  `return prim if enabled is not False and not kinematic else None` made `return prim if enabled is not False else
  None` (a kinematic body counted as dynamic).
- test_a_warning_rule_never_fails_the_place: rules.severity made `return "error"` (every rule an error).
- test_findings_group_one_rule_and_message_into_one_problem: judged.grouped's `"count": len(prims)` made `"count": 1`.
- test_a_place_is_judged_on_its_accepted_assembly_from_the_store: __main__.answer made `return "pass"`.
"""
import json

from score import review
from score.stages.complete.usd import __main__ as check
from score.stages.complete.usd import judged, rules
from score.store import Store

STAMP = "2026-10-19T10:00:00.000000+00:00"
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


def accepted(store, folder, node, files):
    """One node's output stored, its finish record and a passing judgement written, and accepted as the runner does."""
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (folder / name).write_text(text)
    output = store.put_tree(folder)
    key = f"key-{node.replace('@', '-')}"
    stage, place = node.split("@")
    store.write_record(node, key, {"node": node, "key": key, "output": output, "stage": stage, "place": place,
                                   "finished": STAMP, "started": STAMP, "minutes": 1.0, "euros": 0, "after": {},
                                   "files": {}})
    verdicts = {"made": {"check": "made", "answer": "pass", "reason": "0 faults", "measures": {}, "better": {},
                         "findings": []}}
    store.write_judgement(node, key, "e1", {"node": node, "key": key, "output": output, "evidence": "e1",
                                            "at": STAMP, "answer": "pass", "verdicts": verdicts})
    review.accept_automatically(store, node, output)
    return output


def test_the_good_stage_has_no_error(tmp_path):
    found = judged.issues(stage_of(tmp_path, GOOD))
    assert rules_hit(found) == set(), [issue for issue in found if issue["severity"] == "error"]


def test_the_bad_stage_fails_by_each_rule_it_breaks(tmp_path):
    hit = rules_hit(judged.issues(stage_of(tmp_path, BAD)))
    for rule in ("DefaultPrimChecker", "StageMetadataChecker", "MissingReferenceChecker", "DanglingOverPrimChecker",
                 "ExtentsChecker", "MassChecker", "TriangleColliderOnDynamicBody"):
        assert rule in hit, (rule, hit)


def test_a_triangle_collider_is_a_fault_only_on_a_dynamic_body(tmp_path):
    kinematic = BAD.replace("float physics:mass = -3", "bool physics:kinematicEnabled = 1")
    assert "TriangleColliderOnDynamicBody" not in rules_hit(judged.issues(stage_of(tmp_path, kinematic)))
    hull = GOOD.replace('"convexHull"', '"none"')
    assert "TriangleColliderOnDynamicBody" in rules_hit(judged.issues(stage_of(tmp_path, hull)))
    switched_off = hull.replace('uniform token physics:approximation = "none"',
                                'uniform token physics:approximation = "none"\n            bool physics:collisionEnabled = 0')
    assert "TriangleColliderOnDynamicBody" not in rules_hit(judged.issues(stage_of(tmp_path, switched_off)))


def test_a_warning_rule_never_fails_the_place(tmp_path):
    """A stage whose meshes have no normals: NormalsExistChecker tells of it, and the place still passes."""
    bare = GOOD.replace(GOOD_MESH, GOOD_MESH[:GOOD_MESH.index("        normal3f[]")])
    found = judged.issues(stage_of(tmp_path, bare))
    written = check.written_for("place", "assembly@place", "out", found)
    assert "NormalsExistChecker" in rules_hit(found, "warning"), found
    assert written["answer"] == "pass" and written["counts"]["warning"] >= 1 and written["findings"] == [], written


def test_findings_group_one_rule_and_message_into_one_problem():
    found = [{"rule": "DanglingOverPrimChecker", "severity": "error", "message": "dangling", "prim": f"/p/{n}"}
             for n in range(107)]
    groups = judged.grouped(found)
    assert len(groups) == 1 and groups[0]["count"] == 107 and len(groups[0]["prims"]) == judged.SAMPLES
    assert groups[0]["sentence"].startswith("107 x DanglingOverPrimChecker")


def test_a_place_is_judged_on_its_accepted_assembly_from_the_store(tmp_path):
    store = Store.in_folder(tmp_path / "store")
    output = accepted(store, tmp_path / "made", "assembly@place", {"place.usda": BAD})
    written = check.judged_place(store, "place", tmp_path / "out" / "place")
    on_disk = json.loads((tmp_path / "out/place/findings.json").read_text())
    assert on_disk == written and written["answer"] == "fail"
    assert written["outputs"] == {"assembly@place": output}
    assert check.judged_place(store, "nowhere", tmp_path / "out/nowhere")["answer"] == "unknown"
