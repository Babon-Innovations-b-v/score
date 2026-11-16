# score/stages/place_build/maker/shim/

Stand-ins put first on the maker's Python path (generate.py), so TRELLIS.2 runs with no compiled wheel from a third
party: `flash_attn` (the six calls TRELLIS.2 makes, on torch's scaled_dot_product_attention) and `nvdiffrast` (only the
UV-space rasterize and interpolate o_voxel's to_glb uses; NVIDIA's nvdiffrast is non-commercial). Each answers exactly
as the original for TRELLIS.2's inputs and nothing more; a new call TRELLIS.2 makes is added here, never the original.
