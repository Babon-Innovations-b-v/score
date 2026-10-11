"""The model adapter: one pinned container image per model kind, and the record a node's key carries for it.

    models.record("judge")   # {"kind", "image", "digest", "models": [{name, source, revision, sha256, licence,
                             #   commercial_use}]}

It reads what tools/cloud already pins, unchanged: the built image of each kind (tools/cloud/images/images.json) and
the models it fetches (tools/cloud/images/<kind>/models.json). A kind with no built image, an image not pinned by
digest, or a model without a revision, a checksum or a licence is refused: a node cannot be keyed on a model that is
not pinned. A model not for commercial use is refused unless the kind is marked tool-only (SCORE worlds are owned).

    models.api_record("gemini-judge")   # a model reached through a paid API: {"kind", "provider", "model", settings}

An API model has no image or weights to hash: its record pins the model id and the request's settings, and a change
to either re-keys the node.
"""
import json
import pathlib

IMAGES = pathlib.Path(__file__).resolve().parents[3] / "tools/cloud/images"
PINNED = ("name", "revision", "sha256", "licence", "commercial_use")
# Models reached through a paid API. gemini-judge: the surface judge (judge-decision.txt of the surface test,
# 2026-10-11: 3 of 83 answered pairs differ against Qwen3.8-27B's 12 of 87); it names surfaces from the library and
# makes nothing a world ships.
API = {"gemini-judge": {"provider": "google-gemini-api", "model": "gemini-3.1-pro-preview", "temperature": 0,
                        "thinking": "default", "timeout_seconds": 60, "tries": 5, "parallel": 32,
                        "commercial_use": True}}


class NotPinned(Exception):
    """A model kind cannot be keyed: its image or one of its models is not pinned."""


def built_image(kind, images=IMAGES):
    """The kind's built image from images.json, refused when it has none or no digest."""
    built = json.loads((images / "images.json").read_text())
    if kind not in built:
        raise NotPinned(f"no image of {kind} is built (tools/cloud/images/build.py {kind})")
    image = built[kind]
    if not image.get("digest"):
        raise NotPinned(f"the {kind} image is not pinned by digest")
    return image


def pinned_models(kind, tool_only, images=IMAGES):
    """The kind's models from its models.json, each checked for a pin, a licence and its use."""
    path = images / kind / "models.json"
    listed = json.loads(path.read_text()) if path.exists() else []
    for model in listed:
        missing = [name for name in PINNED if model.get(name) in (None, "")]
        if missing:
            raise NotPinned(f"{kind}: model {model.get('name')} lacks {', '.join(missing)}")
        if not model["commercial_use"] and not tool_only:
            raise NotPinned(f"{kind}: model {model['name']} ({model['licence']}) is not for commercial use")
    return [{name: model[name] for name in (*PINNED, "source") if name in model} for model in listed]


def record(kind, tool_only=False, images=IMAGES):
    """What a node's key and finish record carry for a model kind: its image digest and its pinned models."""
    image = built_image(kind, images)
    return {"kind": kind, "image": image["image"], "digest": image["digest"],
            "models": pinned_models(kind, tool_only, images)}


def api_record(kind):
    """What a node's key and finish record carry for a model reached through a paid API: its id and settings."""
    if kind not in API:
        raise NotPinned(f"no API model {kind} is pinned (models.API)")
    return {"kind": kind, **API[kind]}
