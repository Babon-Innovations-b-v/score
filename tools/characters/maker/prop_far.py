"""The prop route's far body: the fitted mesh thinned to FAR_TRIANGLES for crowds, in body.py's three far surfaces
(skin, clothes, boots), each the mean of its parts' colours, every point weighted as the nearest point of the mesh.
Plain CPU geometry on the owner's PC (trimesh's quadric thinning, fast-simplification, MIT); prop_build.py writes it.

    ~/.farm-factory-props/env/bin/python tools/characters/maker/prop_far.py <fit rig.npz> <parts.npz> <far.npz>
"""
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

FAR_TRIANGLES = 1220
SURFACES = ("skin", "clothes", "boots")


def surface_of_parts(parts):
    """Each part's far surface: skin for skin, boots for a boot, clothes for the rest (the hair too)."""
    return {int(part): ("skin" if role == "skin" else "boots" if name == "boot" else "clothes")
            for part, role, name in zip(parts["parts"], parts["roles"], parts["names"])}


def far(fit_rig, parts):
    """The far body's arrays: points, faces, weights, each face's surface and the surfaces' colours."""
    whole = trimesh.Trimesh(fit_rig["points"], fit_rig["faces"], process=False)
    thin = whole.simplify_quadric_decimation(face_count=FAR_TRIANGLES)
    nearest_face = cKDTree(whole.triangles_center).query(thin.triangles_center)[1]
    of_part = surface_of_parts(parts)
    face_surface = np.array([SURFACES.index(of_part[int(part)]) for part in parts["part_of"][nearest_face]])
    colours = []
    for surface in SURFACES:
        members = [number for number, part in enumerate(parts["parts"]) if of_part[int(part)] == surface]
        colours.append(np.mean(parts["colours"][members], 0) if members else np.zeros(3))
    return {"points": thin.vertices, "faces": thin.faces, "surface_of_face": face_surface,
            "weights": fit_rig["weights"][cKDTree(whole.vertices).query(thin.vertices)[1]],
            "surfaces": np.array(SURFACES), "colours": np.array(colours)}


def main():
    fit_path, parts_path, out = map(pathlib.Path, sys.argv[1:4])
    arrays = far(np.load(fit_path), np.load(parts_path))
    np.savez_compressed(out, **arrays)
    print(f"far body: {len(arrays['faces'])} triangles; {out}", flush=True)


if __name__ == "__main__":
    main()
