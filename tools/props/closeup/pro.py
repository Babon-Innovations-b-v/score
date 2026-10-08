"""A close-up from Nano Banana Pro (Google's gemini-3-pro-image), the stage's fallback for a close-up the shape
check fails: the same wording and references as the open model's, drawn at 2K. It is a paid, closed service with a
daily quota (250 pictures a day, 20 a minute on the account's tier, 2026-10-08), so the stage calls it only for
failures. Its key is the secret `gemini-api-key`, read by name (../cloud/secret_store.py), never written down.
"""
import base64
import io
import json
import time
import urllib.error
import urllib.request

from PIL import Image

MODEL = "gemini-3-pro-image"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
KEY_SECRET = "gemini-api-key"
# The price of one 2K picture (Google's price list, as the close-ups were billed on 2026-10-08).
DOLLARS_A_PICTURE = 0.134
ATTEMPTS = 4
WAIT_SECONDS = 60


def part(picture, longest):
    """A picture as an inline JPEG part, its longer side at most `longest` pixels."""
    picture = picture.convert("RGB")
    picture.thumbnail((longest, longest))
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=90)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buffer.getvalue()).decode()}}


def request_body(wording, crop, concept=None):
    """The request: the wording, the crop (image 1) and the whole concept when given (image 2), one 2K picture back."""
    parts = [{"text": wording}, part(crop, 1024)] + ([part(concept, 1600)] if concept else [])
    return {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"imageSize": "2K"}}}


def pictures_in(answer):
    """The pictures in an answer, as base64 strings."""
    return [piece["inlineData"]["data"] for candidate in answer.get("candidates", [])
            for piece in candidate.get("content", {}).get("parts", []) if "inlineData" in piece]


def draw(key, wording, crop, concept, path):
    """One close-up into `path`; True when a picture came back, False when the service refused every attempt. A
    refused request (quota, overload) is tried again after a wait."""
    body = json.dumps(request_body(wording, crop, concept)).encode()
    for attempt in range(ATTEMPTS):
        request = urllib.request.Request(URL, data=body, method="POST",
                                         headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=400) as response:
                found = pictures_in(json.loads(response.read()))
        except urllib.error.HTTPError as error:
            print(f"Nano Banana Pro refused ({error.code}); trying again", flush=True)
            time.sleep(WAIT_SECONDS * (attempt + 1))
            continue
        if found:
            Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB").save(path)
            return True
    return False
