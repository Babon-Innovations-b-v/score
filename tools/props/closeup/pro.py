"""A close-up from Nano Banana Pro (Google's gemini-3-pro-image), the stage's fallback for a close-up the shape
check fails: the same wording and references as the open model's, drawn at 2K. It is a paid, closed service with a
daily quota (250 pictures a day, 20 a minute on the account's tier, 2026-10-08), so the stage calls it only for
failures. Its key is the secret `gemini-api-key`, read by name (../cloud/secret_store.py), never written down.
Nothing is drawn outside a cleared run or the owner's override (score.adapters.compute, `require_cleared`).
"""
import base64
import io
import pathlib
import sys
import time
import urllib.error

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "cloud"))
import google_spend  # noqa: E402
from score.adapters import compute  # noqa: E402

MODEL = "gemini-3-pro-image"
KEY_SECRET = "gemini-api-key"
# The price of one 2K picture (Google's price list, as the close-ups were billed on 2026-10-08).
DOLLARS_A_PICTURE = 0.134
# A request refused for the rate or the quota (429) is asked again after a wait, up to this many times: a refusal is
# free. Nothing else is asked again: a batch runs every call once (CONTEXT.md, owner 2026-10-20).
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


def quota_refusal(error):
    """Whether an HTTP error is the service's refusal for the rate or the quota, which costs nothing."""
    return error.code == 429 or "quota" in str(error.reason).lower()


def draw(key, wording, crop, concept, path):
    """One close-up into `path`; True when a picture came back, False for a hole: an answer with no picture, any other
    refusal, or a rate or quota refusal (quota_refusal, asked again after a wait) every attempt. The call runs once
    (a batch): a hole is not asked again here, it goes to the basket and a new batch. Refused outside a cleared run
    (compute.require_cleared). Each call's cost goes on the Google ledger (google_spend). The same request (same
    wording, crop and concept) is asked once: its answer is kept in google_spend's cache, so a re-keyed node re-draws
    nothing; an answer with no picture is dropped from the cache, so a new batch may ask again."""
    compute.require_cleared("a Nano Banana Pro close-up")
    body = request_body(wording, crop, concept)
    for attempt in range(ATTEMPTS):
        try:  # priced on the Google ledger (google_spend)
            found = pictures_in(google_spend.generate(MODEL, body, key, 400, caller="pro", cache=True))
        except urllib.error.HTTPError as error:
            if not quota_refusal(error):
                print(f"Nano Banana Pro refused ({error.code}); a hole", flush=True)
                return False
            print(f"Nano Banana Pro refused for the rate or the quota ({error.code}); asking again after a wait",
                  flush=True)
            time.sleep(WAIT_SECONDS * (attempt + 1))
            continue
        if not found:
            google_spend.cache_path(MODEL, body).unlink(missing_ok=True)
            print("Nano Banana Pro answered with no picture; a hole", flush=True)
            return False
        Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB").save(path)
        return True
    return False
