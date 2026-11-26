"""The close-up photo's eye and brow landmarks (#223), read by MediaPipe's Face Landmarker (Apache-2.0, on the CPU),
for `lids.py`: each eye's upper and lower lid margin, its corners and its iris, each brow's upper and lower edge.

    uv run --no-project -p 3.12 --with mediapipe==1.2.3 --with pillow python -m tools.characters.generated.marks \
        <close-up photo> <marks.json>

MediaPipe is not one of the repo's own dependencies (it pins its own numpy and OpenCV), so this one reading runs in
its own throwaway environment and writes a small JSON that `lids.py` reads. Its model (MODEL_URL, 3.6 MB) is cached
in MODEL_CACHE. The library needs libGLESv2 and libEGL even on the CPU; a box without them takes them from Ubuntu's
packages unpacked into a folder on LD_LIBRARY_PATH (`apt-get download libgles2 libglvnd0 libegl1`, `dpkg -x`).

Pixels are the photo's (column, row); the eyes and brows come the picture's left first (the subject's right, as
`eyes.photo_pupils` orders them), each lid and brow from its inner end (by the nose) out.
"""
import json
import pathlib
import sys
import urllib.request

import numpy as np
from PIL import Image

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/"
             "face_landmarker.task")
MODEL_CACHE = pathlib.Path.home() / ".cache" / "score" / "mediapipe" / "face_landmarker.task"
# Face Mesh's canonical indices, the subject's right eye and brow first (the picture's left), inner end first.
EYES = ({"upper": [133, 173, 157, 158, 159, 160, 161, 246, 33], "lower": [133, 155, 154, 153, 145, 144, 163, 7, 33],
         "iris": [468, 469, 470, 471, 472]},
        {"upper": [362, 398, 384, 385, 386, 387, 388, 466, 263], "lower": [362, 382, 381, 380, 374, 373, 390, 249, 263],
         "iris": [473, 474, 475, 476, 477]})
BROWS = ({"upper": [107, 66, 105, 63, 70], "lower": [55, 65, 52, 53, 46]},
         {"upper": [336, 296, 334, 293, 300], "lower": [285, 295, 282, 283, 276]})


def model_path():
    """The landmarker's model, fetched once into MODEL_CACHE."""
    if not MODEL_CACHE.exists():
        MODEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_CACHE)
    return MODEL_CACHE


def landmarks(photo):
    """The face's 478 landmarks in the photo's pixels (column, row); raises when no face is found."""
    import mediapipe
    from mediapipe.tasks.python import BaseOptions, vision
    options = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=str(model_path())), num_faces=1)
    detector = vision.FaceLandmarker.create_from_options(options)
    found = detector.detect(mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB, data=np.asarray(photo)))
    if not found.face_landmarks:
        raise ValueError("no face found on the photo")
    return np.array([[mark.x * photo.width, mark.y * photo.height] for mark in found.face_landmarks[0]])


def marks_of(points):
    """The eyes' and brows' marks out of the 478 landmarks: {eyes: [{upper, lower, iris_centre, iris_radius}],
    brows: [{upper, lower}]}, pixel lists."""
    eyes = []
    for eye in EYES:
        iris = points[eye["iris"]]
        eyes.append({"upper": points[eye["upper"]].round(2).tolist(), "lower": points[eye["lower"]].round(2).tolist(),
                     "iris_centre": iris[0].round(2).tolist(),
                     "iris_radius": round(float(np.linalg.norm(iris[1:] - iris[0], axis=1).mean()), 2)})
    brows = [{"upper": points[brow["upper"]].round(2).tolist(), "lower": points[brow["lower"]].round(2).tolist()}
             for brow in BROWS]
    return {"eyes": eyes, "brows": brows}


def main():
    photo_path, out = sys.argv[1:3]
    photo = Image.open(photo_path).convert("RGB")
    marks = {"photo": str(photo_path), "size": [photo.width, photo.height], **marks_of(landmarks(photo))}
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out).write_text(json.dumps(marks, indent=1))
    print(f"marks: {out}")


if __name__ == "__main__":
    main()
