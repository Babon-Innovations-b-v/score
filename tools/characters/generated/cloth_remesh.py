"""In gpytoolbox's own Python (cloth_mesh.REMESH): a garment's cleaned surface remeshed even (Botsch and Kobbelt's
isotropic remesher, gpytoolbox.remesh_botsch, reprojected onto the surface; its rim points stay where they stand).

    uv run --no-project -p 3.12 --with gpytoolbox==0.3.8 python cloth_remesh.py <in.npz> <out.npz> '{"edge": m,
    "rounds": n}'
"""
import json
import sys

import gpytoolbox
import numpy as np


def main():
    given, made, options = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    surface = np.load(given)
    points, faces = gpytoolbox.remesh_botsch(surface["points"].astype(np.float64), surface["faces"].astype(np.int32),
                                             i=options["rounds"], h=options["edge"], project=True)
    np.savez(made, points=points, faces=faces)


if __name__ == "__main__":
    main()
