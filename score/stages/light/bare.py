"""What a lit place would render bare (the light layer's gate "surfaced", before light-passes is bought): its made
ground, water and room shell each a mesh the library finishes, and an outdoor place's sky holding something
(2026-11-04: the eyes review of env1 found the campgrounds', the base's, the square's and the street's ground a
white sheet: the light rows laid the made ground and never its library surface, as the assembly does).

    faults(root, place) -> [str]    the bare meshes and the empty sky of the stage at `root`

A mesh is bare when it is drawn (active, not made invisible) under /<place>, is the ground's, the water's or the
shell's (`score:kind` ground, water or structure), and is bound to no material or names its finish missing
(`score:surface:missing`, as the terrain, the record's writer and bind_surface name it). A place is outdoor when it
draws a made ground (a ground mesh under /<place>/Outside); its sky is empty when no sky element of the light
layer's (`score:kind` sky light, sky body, sky disc or sky backdrop) nor a dome light is active under /<place>.
"""
SURFACED = ("ground", "water", "structure")
SKY_KINDS = ("sky light", "sky body", "sky disc", "sky backdrop")


def kind_of(prim):
    attribute = prim.GetAttribute("score:kind")
    return attribute.Get() if attribute and attribute.HasAuthoredValue() else None


def drawn(prim):
    """Active and not made invisible, here or above."""
    from pxr import UsdGeom
    imageable = UsdGeom.Imageable(prim)
    return prim.IsActive() and (not imageable or imageable.ComputeVisibility() != UsdGeom.Tokens.invisible)


def bare_why(prim):
    """Why a drawn ground, water or shell mesh renders with no library surface, or None when it has one."""
    from pxr import UsdShade
    missing = prim.GetAttribute("score:surface:missing")
    if missing and missing.HasAuthoredValue():
        return f"its finish is named missing: {missing.Get()}"
    if not UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]:
        return "it is bound to no material"
    return None


def faults(root, place):
    """Every bare ground, water or shell mesh of the stage at `root` under /<place>, and its empty sky when the place
    is outdoor (module docstring)."""
    from pxr import Usd, UsdGeom, UsdLux
    stage = Usd.Stage.Open(str(root))
    top = stage.GetPrimAtPath(f"/{place}")
    found, outdoor, sky = [], False, False
    for prim in Usd.PrimRange(top) if top else []:
        kind = kind_of(prim)
        if not prim.IsActive():
            continue
        if kind in SKY_KINDS or prim.IsA(UsdLux.DomeLight):
            sky = True
        if not prim.IsA(UsdGeom.Mesh) or kind not in SURFACED or not drawn(prim):
            continue
        outdoor = outdoor or (kind == "ground" and str(prim.GetPath()).startswith(f"/{place}/Outside/"))
        why = bare_why(prim)
        if why:
            found.append(f"{prim.GetPath()} ({kind}): {why}")
    if outdoor and not sky:
        found.append(f"/{place}: an outdoor place with an empty sky (no sky element nor dome light)")
    return found
