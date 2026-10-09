"""The body read off one picture: SAM3DBody-cpp (vendor/sam3dbody-cpp, MIT code by Ammar Qammaz; its ONNX and GGUF
weights are converted from Meta's SAM 3D Body and stay under the SAM License) on the person in a full-body picture,
written as the identity the people tools build a body from (tools/characters/people/body.py `build_layer`: MHR's
`shape_params` and its 204 `mhr_model_params`, whose last 68 are the part scales and 130 to 135 the bone lengths).

    /root/envs/motion/bin/python body_picture.py <picture> <identity.npz> [--engine /root/sam3dbody-cpp]

Runs on a rented card (characters.py); the weights are never shipped, only the measured body. The person found is the
largest in the picture. The file also keeps the 2D and 3D keypoints, which the colour picks read (where the face and
the hair are in the picture).
"""
import argparse
import ctypes
import pathlib
import sys

import cv2
import numpy as np

ENGINE = pathlib.Path("/root/sam3dbody-cpp")
MOST_PEOPLE = 8
# The vendored frontend's own defaults (python/fast_sam_3dbody_frontend.py).
PERSON_THRESHOLD = 0.5
OVERLAP = 0.45


def frontend(engine):
    """The vendored Python frontend's ctypes structures, imported from its own file so they never drift from the
    library they mirror (it checks the result's size against the library's)."""
    sys.path.insert(0, str(engine / "python"))
    import fast_sam_3dbody_frontend
    return fast_sam_3dbody_frontend


def load(engine, front):
    """The engine loaded on the first card; its handle."""
    library = front.load_library(str(engine / "build"))
    handle = library.fsb_create()
    onnx = engine / "onnx"
    config = front.FsbConfig(onnx_dir=str(onnx).encode(), gguf_path=str(onnx / "pipeline.gguf").encode(),
                             yolo_path=str(onnx / "yolo.onnx").encode(), cuda_device=0, skip_body_model=0,
                             person_thresh=PERSON_THRESHOLD, person_nms_iou=OVERLAP, max_persons=MOST_PEOPLE,
                             focal_x=0.0, focal_y=0.0, principal_x=0.0, principal_y=0.0, zero_face_params=1)
    if not library.fsb_load(handle, ctypes.byref(config)):
        raise SystemExit("SAM3DBody-cpp would not load its models")
    return library, handle


def largest(results, count):
    """The person whose box is largest."""
    def area(result):
        left, top, right, bottom = result.bbox
        return (right - left) * (bottom - top)
    return max((results[index] for index in range(count)), key=area)


def read_person(library, handle, front, picture):
    """The largest person SAM3DBody-cpp finds in the picture."""
    image = cv2.imread(str(picture))
    if image is None:
        raise SystemExit(f"cannot read {picture}")
    height, width = image.shape[:2]
    results = (front.FsbResult * MOST_PEOPLE)()
    pixels = np.ascontiguousarray(image)
    count = library.fsb_process_bgr(handle, pixels.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), width, height,
                                    results, MOST_PEOPLE)
    if count < 1:
        raise SystemExit(f"nobody found in {picture}")
    return largest(results, count)


def identity(result):
    """The identity file's arrays, named as SAM 3D Body's own answer names them."""
    def array(field, *shape):
        return np.array(getattr(result, field), dtype=np.float32).reshape(*shape)
    return {"shape_params": array("shape", 45), "scale_params": array("scale", 28),
            "mhr_model_params": array("mhr_model_params", 204), "body_pose_params": array("body_pose", 133),
            "global_rot": array("global_rot", 3), "pred_cam_t": array("pred_cam_t", 3),
            "focal_length": np.float32(result.focal_length), "bbox": array("bbox", 4),
            "pred_keypoints_3d": array("kps_3d", 70, 3), "pred_keypoints_2d": array("kps_2d", 70, 2),
            "pred_joint_coords": array("skel_3d", 127, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("picture", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--engine", type=pathlib.Path, default=ENGINE)
    options = parser.parse_args()
    front = frontend(options.engine)
    library, handle = load(options.engine, front)
    try:
        person = read_person(library, handle, front, options.picture)
    finally:
        library.fsb_destroy(handle)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(options.out, **identity(person))
    print(f"identity of {options.picture.name}: box {np.round(person.bbox, 0).tolist()}, "
          f"focal {person.focal_length:.0f} px", flush=True)


if __name__ == "__main__":
    main()
