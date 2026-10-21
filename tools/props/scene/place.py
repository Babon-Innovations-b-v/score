"""A scene's style, from its design alone (the owner, 2026-10-21: the framework is agnostic, so no hand-written
per-place prose words a picture): the style line of the locked environment concept (score/review/environment_concept.py
`in_force`, else the environment's concept as today's data holds it, `style_now`) and the look of the scene's own
locked concept (its picked draw in the design store, score/review/concepts.py `picked`, keyed by the scene id). Every
picture of a scene's objects is worded in it: the klein close-ups (../cloud/pictures.py), a scene's target and
redraws (../cloud/scene.py, redraw.py) and a painting (marble.py).

A locked concept is a picture, so no rule gives its look in words: it is read once per locked concept by one Gemini
3.1 Pro call on that picture (`read_look`), inside a cleared run (score.adapters.compute.require_cleared: the batch
that draws the scene's pictures), priced at the measured Gemini 3.1 Pro answer (`look_euros`), asked once through
google_spend's cache and kept beside the scene inventories:

    {home}/design/looks/<scene>/<concept sha>.json   {scene, concept, look, model, euros, at}

A new lock is a new concept, so its look is read again; a scene whose concept is not locked has no style, and its
pictures are refused. The place file (data/definitions/place.json) still holds each place's palette, materials and the
scale rules every place shares (`places`), never the words a picture is drawn in.

    python3 tools/props/scene/place.py <scene>        # print the scene's style (reads its look inside a cleared run)
"""
import datetime
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"
# The entry every place shares: the scale rules, not a place.
SHARED = "shared"
LOOKS = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "design" / "looks"
LOOK_MODEL = "gemini-3.1-pro-preview"
LOOK_CALLER = "scene-look"
LOOK_TIMEOUT = 400
LOOK_SIDE = 1600  # pixels of the concept's longer side sent with the question
LONGEST_LOOK = 400  # characters of a look kept
LOOK_QUESTION = ("This is the locked concept painting of one scene. In one sentence of at most 50 words, say only "
                 "its look, the way every object in it is made and finished: its materials, colours, surfaces, wear, "
                 "light and mood. Name no single object, no layout, no size, no people and no text.")


def places(path=PLACES):
    """Every entry in the place file, the shared one among them."""
    return json.loads(pathlib.Path(path).read_text())


def design():
    """(concepts, environment_concept, Store) of the framework, imported with the repository on the path."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from score.review import concepts, environment_concept
    from score.store import Store
    return concepts, environment_concept, Store


def environment_style(store):
    """The environment's style line: its locked concept's, else today's; refused while it has none."""
    _, environment, _ = design()
    held = environment.in_force(store)
    found = (held["style"] if held else environment.style_now()).strip()
    if not found:
        raise SystemExit("the environment concept has no style: lock its style in the creator cockpit first")
    return found


def locked_concept(store, scene):
    """The sha of the scene's locked concept; refused while it has none."""
    concepts, _, _ = design()
    sha = concepts.picked(store, scene)
    if not sha:
        raise SystemExit(f"the scene '{scene}' has no locked concept: lock one in the creator cockpit first")
    return sha


def look_path(scene, sha, looks=None):
    return pathlib.Path(looks or LOOKS) / scene / f"{sha}.json"


def kept_look(scene, sha, looks=None):
    """The kept look record of the scene's concept `sha`, None while it is not read."""
    path = look_path(scene, sha, looks)
    return json.loads(path.read_text()) if path.is_file() else None


def look_euros():
    """The euros of one look: the measured Gemini 3.1 Pro answer at the standard tier (concepts.MEASURED_ASK), None
    while it is not measured."""
    concepts, _, _ = design()
    return concepts.draw_euros(measured=(concepts.MEASURED_ASK,))


def ask(question, picture):
    """One Gemini 3.1 Pro call on the question and the picture, inside a cleared run (google_spend: priced on its
    ledger, asked once); the text it answered."""
    design()
    from score.adapters import compute
    compute.require_cleared("a scene's look read from its locked concept")
    concepts, _, _ = design()
    pro, google_spend, secret_store = concepts.tools()
    body = {"contents": [{"role": "user", "parts": [{"text": question}, pro.part(picture, LOOK_SIDE)]}],
            "generationConfig": {"temperature": 0.2}}
    answer = google_spend.generate(LOOK_MODEL, body, secret_store.secret(pro.KEY_SECRET), LOOK_TIMEOUT,
                                   caller=LOOK_CALLER, cache=True)
    candidate = (answer.get("candidates") or [{}])[0]
    return "".join(part.get("text", "") for part in candidate.get("content", {}).get("parts", [])
                   if not part.get("thought")).strip().strip('"')


def keep_look(record, looks=None):
    """Write a look record whole (a partial file renamed into place), never over one kept."""
    path = look_path(record["scene"], record["concept"], looks)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(f".{os.getpid()}.partial")
    partial.write_text(json.dumps(record, indent=1))
    os.replace(partial, path)


def read_look(store, scene, asker=ask, looks=None):
    """The record of the look of the scene's locked concept: the one kept, else read now by `asker` (one call) and
    kept; refused for an empty answer."""
    sha = locked_concept(store, scene)
    kept = kept_look(scene, sha, looks)
    if kept:
        return kept
    concepts, _, _ = design()
    look = " ".join(asker(LOOK_QUESTION, concepts.blob_picture(store, sha)).split())[:LONGEST_LOOK]
    if not look:
        raise SystemExit(f"the look of the locked concept of '{scene}' came back empty")
    record = {"scene": scene, "concept": sha, "look": look, "model": LOOK_MODEL, "euros": look_euros(),
              "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    keep_look(record, looks)
    return record


def unread(scenes, store=None, looks=None):
    """The scenes of `scenes` whose locked concept's look is not read yet: one call each in the batch that words
    them (refused for a scene with no locked concept)."""
    store = store or design()[2].default()
    return sorted({scene for scene in scenes if not kept_look(scene, locked_concept(store, scene), looks)})


def worded(store, look):
    """The style in words: the environment's style line, then the scene's look."""
    return f"{environment_style(store).rstrip('.')}. {look}"


def style_text(scene, store=None, asker=ask, looks=None):
    """The style every picture of the scene's objects is worded in: the environment's style line and its locked
    concept's look (read_look: read by `asker` when it is not kept yet)."""
    store = store or design()[2].default()
    return worded(store, read_look(store, scene, asker, looks)["look"])


def kept_style(scene, store=None, looks=None):
    """The scene's style while its look is kept, None before it is read (no call: a dry run's words)."""
    store = store or design()[2].default()
    record = kept_look(scene, locked_concept(store, scene), looks)
    return worded(store, record["look"]) if record else None


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(style_text(sys.argv[1]))


if __name__ == "__main__":
    main()
