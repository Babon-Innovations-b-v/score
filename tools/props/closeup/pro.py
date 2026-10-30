"""A close-up from Nano Banana Pro (Google's gemini-3-pro-image), the stage's fallback for a close-up the shape
check fails: the same wording and references as the open model's, drawn at 2K, every call of a step as one Batch API
job at half price (owner, 2026-10-24). It is a paid, closed service, so the stage calls it only for failures. Its key
is the secret `gemini-api-key`, read by name (../cloud/secret_store.py), never written down.
Nothing is drawn outside a cleared run or the owner's override (score.adapters.compute, `require_cleared`); a step
the cache answers whole is read back free, with no ticket and no key (batch 2, 2026-10-30).
"""
import base64
import io
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "cloud"))
import google_batch  # noqa: E402
import google_spend  # noqa: E402
from score.adapters import compute  # noqa: E402

MODEL = "gemini-3-pro-image"
KEY_SECRET = "gemini-api-key"
# The price of one 2K picture (Google's price list, as the close-ups were billed on 2026-10-08), at the Batch API's
# share: every close-up is drawn through it (draw).
DOLLARS_A_PICTURE = 0.134 * google_spend.TIER_PRICE["batch"]


def part(picture, longest):
    """A picture as an inline JPEG part, its longer side at most `longest` pixels."""
    picture = picture.convert("RGB")
    picture.thumbnail((longest, longest))
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=90)
    return {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buffer.getvalue()).decode()}}


def request_body(wording, crop, concept=None, seed=None):
    """The request: the wording, the crop (image 1) and the whole concept when given (image 2), one 2K picture back;
    `seed` in its generation settings when given (a later retry's own, so its request and picture are new ones)."""
    parts = [{"text": wording}, part(crop, 1024)] + ([part(concept, 1600)] if concept else [])
    settings = {"responseModalities": ["IMAGE"], "imageConfig": {"imageSize": "2K"},
                **({"seed": seed} if seed is not None else {})}
    return {"contents": [{"role": "user", "parts": parts}], "generationConfig": settings}


def pictures_in(answer):
    """The pictures in an answer, as base64 strings."""
    return [piece["inlineData"]["data"] for candidate in answer.get("candidates", [])
            for piece in candidate.get("content", {}).get("parts", []) if "inlineData" in piece]


def draw(asks):
    """Every close-up of `asks` ({path: (wording, crop, concept or None, seed or None)}) drawn as one Batch API job at
    half price (../cloud/google_batch.py, caller "pro", the same model, request and settings as one call at a time),
    each saved at its path; {path: True when a picture came back, False for a gap}. A gap is a request the batch gave no answer
    to (google_batch.Unanswered: the job failed, was cancelled or expired, the send was cut off, or it answered with an
    error; it may be billed) or an answer with no picture, dropped from the cache so a new batch may ask again. Each
    is asked once (a batch, CONTEXT.md, owner 2026-10-20): a gap is not asked again here, it goes to the basket and a
    new batch. A request asked before (same wording, crop, concept and seed) is read back from google_spend's cache, free,
    so a re-keyed node re-draws nothing, and a step the cache answers whole asks for no ticket and reads no key (a
    free-only run reads its cached close-ups back; batch 2, 2026-10-30). A set-up fault at the send reaches the caller
    (google_batch). A step any request of which the cache misses is refused outside a cleared run
    (compute.require_cleared), before its key is read."""
    bodies = {str(path): request_body(*ask) for path, ask in asks.items()}
    key = None
    if not all(google_spend.cache_path(MODEL, body).exists() for body in bodies.values()):
        from secret_store import secret

        compute.require_cleared("a Nano Banana Pro close-up")
        key = secret(KEY_SECRET)
    answers = google_batch.generate(MODEL, bodies, key, caller="pro")
    return {path: saved(answers[str(path)], bodies[str(path)], path) for path in asks}


def cached(ask):
    """Whether one ask's (wording, crop, concept or None, seed or None) answer is in google_spend's cache: drawing it
    reads that picture back, free."""
    return google_spend.cache_path(MODEL, request_body(*ask)).exists()


def saved(answer, body, path):
    """One batch answer's picture saved at `path`; False for a gap (Unanswered, no picture in it, or an answer the
    model did not finish: google_spend.unfinished, no whole answer, which google_spend.keep never caches, so a picture
    used is always one its request reads back; batch 2, 2026-10-30)."""
    if isinstance(answer, google_batch.Unanswered):
        print(f"Nano Banana Pro gave no answer for {path.name} ({answer}); a gap", flush=True)
        return False
    found, cut = pictures_in(answer), google_spend.unfinished(answer)
    if not found or cut:
        google_spend.cache_path(MODEL, body).unlink(missing_ok=True)
        print(f"Nano Banana Pro answered {path.name} with {f'an unfinished answer ({cut})' if found else 'no picture'}; "
              "a gap", flush=True)
        return False
    Image.open(io.BytesIO(base64.b64decode(found[-1]))).convert("RGB").save(path)
    return True
