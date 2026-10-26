"""SCORE's curated USD rule set over usd-validation-nvidia (its overlay): the rules every place's composed stage must
pass, the ones it is told of as warnings, and SCORE's own rule the package does not have.

    engine = rules.engine()                       # a ValidationEngine with exactly SCORE's rules on
    rules.severity(issue)                         # "error" or "warning", by SCORE's table, never the package's

The package's default set is not used: it fails SCORE's own good stage (Y up: UpAxisZChecker; ASCII layers; welds a
seam needs). A rule is named here by its class name, so a package update that drops one fails `engine()` loudly
instead of checking less.
"""
import usd_validation_nvidia as validation
from pxr import UsdGeom, UsdPhysics

# Errors: a stage that fails one is not correct USD for SCORE's readers (Blender, Godot, the web copy, the library).
ERRORS = (
    # the stage: metres, Y up, one default prim, every reference and texture found, no over left with no def
    "DefaultPrimChecker", "StageMetadataChecker", "MissingReferenceChecker", "DanglingOverPrimChecker",
    "UsdValidationAttributeTypeMismatchChecker",
    # bounds and topology
    "ExtentsChecker", "ValidateTopologyChecker", "SubdivisionSchemeChecker", "UsdGeomSubsetChecker",
    "UsdGeomSubsetFamiliesChecker", "UsdGeomSubsetParentIsImageableChecker",
    # materials and their binding
    "UsdMaterialBindingApi", "UsdDanglingMaterialBinding", "UsdShadeMaterialBindingRelationships",
    "UsdShadeMaterialBindingCollectionValidator", "UsdShadeSubsetsMaterialBindFamilyChecker",
    "UsdShadeEncapsulationMaterialValidator", "UsdShadeShaderSdrCompliance", "MaterialUsdPreviewSurfaceChecker",
    "NormalMapTextureChecker",
    # physics: usd-core's UsdPhysics validators, and mass
    "RigidBodyChecker", "ColliderChecker", "PhysicsJointChecker", "ArticulationChecker", "MassChecker",
)
# Warnings: told, never failing the place (a seam's split vertices read as non-manifold; an unindexed primvar draws
# right).
WARNINGS = ("NormalsExistChecker", "NormalsValidChecker", "NormalsWindingsChecker", "ManifoldChecker",
            "ZeroAreaFaceChecker", "IndexedPrimvarChecker", "UnusedPrimvarChecker", "UnusedMeshTopologyChecker")


class TriangleColliderOnDynamicBody(validation.BaseRuleChecker):
    """A mesh collider with no approximation (a triangle mesh) under a dynamic rigid body: PhysX and Bullet take a
    triangle mesh only as a static collider, so the body falls through what it should stand on, or the engine drops
    it. The package's ColliderChecker does not catch it (measured 2026-10-26). A static or kinematic body may keep
    one."""

    def CheckPrim(self, prim):
        if not (prim.IsA(UsdGeom.Mesh) and prim.HasAPI(UsdPhysics.CollisionAPI)):
            return
        if UsdPhysics.CollisionAPI(prim).GetCollisionEnabledAttr().Get() is False:
            return  # switched off: the physics trial keeps a body's own triangles off and collides by its hull
        if approximation(prim) != UsdPhysics.Tokens.none:
            return
        body = dynamic_body(prim)
        if body is not None:
            self._AddFailedCheck(f"triangle-mesh collider under the dynamic rigid body {body.GetPath()}: give it a "
                                 "convexHull or convexDecomposition approximation", at=prim)


def approximation(prim):
    """A mesh collider's approximation token; unauthored is `none`, a triangle mesh."""
    attribute = UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr()
    value = attribute.Get() if attribute else None
    return value or UsdPhysics.Tokens.none


def dynamic_body(prim):
    """The nearest rigid body at or above the prim when it is enabled and not kinematic, else None."""
    while prim and not prim.IsPseudoRoot():
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            body = UsdPhysics.RigidBodyAPI(prim)
            enabled = body.GetRigidBodyEnabledAttr().Get()
            kinematic = body.GetKinematicEnabledAttr().Get()
            return prim if enabled is not False and not kinematic else None
        prim = prim.GetParent()
    return None


SCORE_RULES = (TriangleColliderOnDynamicBody,)


def found(name):
    """The package's rule class of that name; refuses a name it no longer has."""
    rule = getattr(validation, name, None)
    if rule is None:
        raise LookupError(f"usd-validation-nvidia {validation.__version__} has no rule {name}")
    return rule


def engine():
    """A ValidationEngine with SCORE's rules only (the package's defaults off)."""
    made = validation.ValidationEngine(init_rules=False)
    for name in (*ERRORS, *WARNINGS):
        made.enable_rule(found(name))
    for rule in SCORE_RULES:
        made.enable_rule(rule)
    return made


def severity(issue):
    """'warning' for a rule SCORE only tells of, else 'error'."""
    return "warning" if issue.rule is not None and issue.rule.__name__ in WARNINGS else "error"
