"""A layer SCORE writes, made a whole OpenUSD asset on its own: every place layer is handed to the library as an
asset of its own (score_lib's `layer/<layer>.<place>` entries), where its root layer is the only one, so it carries
the stage's metres, Y up and default prim itself (the USD check, score/stages/complete/usd, fails a layer without).

    whole_layer.stamped(layer, place)    # an Sdf.Layer: metres, Y up, /<place> its default prim, a def Xform

Composition is unchanged: a sublayer's stage metadata and default prim are read only on the root layer, and the
place's root is a def Xform in every base (tools/usd/export.py), so a layer's root said the same way agrees with it.
What a layer overrides below the root (a base object's pose, a prim made inactive) stays an `over`.
"""
from pxr import Sdf, UsdGeom

ROOT_TYPE = "Xform"


def stamped(layer, place):
    """The layer stamped as a whole asset: metres, Y up, /<place> its default prim, that prim a def (an `over` of the
    place's root dangles in the layer alone) typed Xform where the layer gave it no type; the layer back."""
    layer.pseudoRoot.SetInfo(UsdGeom.Tokens.upAxis, UsdGeom.Tokens.y)
    layer.pseudoRoot.SetInfo(UsdGeom.Tokens.metersPerUnit, 1.0)
    layer.defaultPrim = place
    spec = layer.GetPrimAtPath(f"/{place}")
    if spec:
        spec.specifier = Sdf.SpecifierDef
        spec.typeName = spec.typeName or ROOT_TYPE
    return layer
