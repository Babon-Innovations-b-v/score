"""review.py's Blender side: blender_views.py (usd_views with the place's laid ground, thin glass and recipe looks) run
as it is, with two things a review needs patched into usd_views' camera: an orthographic lens (a view's "ortho", its
metres across) and a near cut (a view's "near", the camera's clip start, so the plan sees under the roofs); the
review's samples set to REVIEW_SAMPLES (denoised) and the laid ground's displacement drawn as bump: a review picture
never ships, and neither changes what a reviewer reads off it (layout, sizes, faults).

    blender -b --python review_views.py -- <scene.usda> <views.json> <out folder>
"""
import pathlib
import runpy
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools/blender/inside"))
import usd_views  # noqa: E402

REVIEW_SAMPLES = 8
drawn_camera = usd_views.camera


def flat_ground():
    """The laid ground's displacement (blender_views.displaced: faces cut finer for every camera, the review's slowest
    part) drawn as bump only; its relief is the terrain's own mesh still."""
    import bpy
    ground = bpy.data.objects.get("Ground")
    if ground is None or "displaced" not in ground.modifiers:
        return
    ground.modifiers.remove(ground.modifiers["displaced"])
    for slot in ground.material_slots:
        if slot.material is not None:
            slot.material.displacement_method = "BUMP"


def camera(scene, view):
    """usd_views' camera, made orthographic and cut near where the view asks; the ground left undisplaced and the
    scene's render data kept between views."""
    flat_ground()
    scene.render.use_persistent_data = True
    drawn_camera(scene, view)
    data = scene.camera.data
    if view.get("ortho"):
        data.type = "ORTHO"
        data.ortho_scale = float(view["ortho"])
    if view.get("near"):
        data.clip_start = float(view["near"])


usd_views.camera = camera
usd_views.REVIEW_SAMPLES = REVIEW_SAMPLES
runpy.run_path(str(HERE / "blender_views.py"), run_name="__main__")
