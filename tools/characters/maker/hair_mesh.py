"""A head-with-hair mesh from the clay hair picture: Hi3DGen (Stable-X, MIT code; weights Stable-X/trellis-normal-v0-1
MIT and Stable-X/yoso-normal-v1-8-1 Apache-2.0, with ZhengPeng7/BiRefNet, MIT, for the cut-out) on the rented card.

    /root/envs/hi3dgen/bin/python hair_mesh.py <picture.png> <out.glb> [--seed 1]

The picture's normals are drawn by StableNormal (hugoycj/StableNormal through torch.hub, Apache-2.0) and the mesh
grown from them, as the prop chain's make.py did on the owner's box before no model ran there (2026-10-03).
"""
import argparse
import os
import pathlib
import sys

HI3DGEN = pathlib.Path("/root/hi3dgen")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("picture", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--seed", type=int, default=1)
    options = parser.parse_args()
    os.chdir(HI3DGEN)
    sys.path.insert(0, str(HI3DGEN))
    import torch
    from PIL import Image
    from hi3dgen.pipelines import Hi3DGenPipeline
    pipeline = Hi3DGenPipeline.from_pretrained("weights/trellis-normal-v0-1")
    pipeline.cuda()
    normals = torch.hub.load("hugoycj/StableNormal", "StableNormal_turbo", trust_repo=True,
                             yoso_version="yoso-normal-v1-8-1", local_cache_dir="./weights")
    image = pipeline.preprocess_image(Image.open(options.picture), resolution=1024)
    normal_image = normals(image, resolution=768, match_input_resolution=True, data_type="object")
    normal_image.save(options.out.with_suffix(".normals.png"))
    outputs = pipeline.run(normal_image, seed=options.seed, formats=["mesh"], preprocess_image=False,
                           sparse_structure_sampler_params={"steps": 50, "cfg_strength": 3},
                           slat_sampler_params={"steps": 6, "cfg_strength": 3})
    mesh = outputs["mesh"][0].to_trimesh(transform_pose=True)
    mesh.export(options.out)
    print(f"{options.out.name}: {len(mesh.faces)} triangles, peak {torch.cuda.max_memory_allocated() / 1e9:.1f} GB",
          flush=True)


if __name__ == "__main__":
    main()
