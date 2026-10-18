"""What already exists for a film script to show, per place, from the source of this mode (the store beside the
cockpit, or the pushed export): the place's accepted films, its hero picture, its 3D web copy and OpenUSD layers, and
the pictures of the framework's steps. Read only; nothing is made here."""
from score.dashboard.films import script

MOST_PICTURES = 6
# A model's turntable frame that is its colour picture (not its metal and roughness pass).
TURNTABLE_PASS = "-mr.png"


def place_words(place):
    """A place's name in words."""
    return place.replace("_", " ").capitalize()


def usd_layers(source, place):
    """The names of the OpenUSD layers the place's accepted stage holds, in the stage's order."""
    index = source.usd_index(place) if hasattr(source, "usd_index") else getattr(
        source.place_detail(place), "usd_index", None)
    return [layer.name for layer in (index.layers if index else []) if layer.present]


def own_film(source, place):
    """{"url", "thumb"} of the place's accepted film (demo-film@<place>), or None."""
    card = source.place_card(place)
    film = card.film if card else None
    return {"url": film.url, "name": film.name} if film else None


def extra_films(source, place):
    """{film name: url} of the place's other accepted films (demo-film-extra@<place>, a folder each)."""
    detail = source.step_detail(place, "demo-film-extra")
    if detail is None or detail.accepted is None:
        return {}
    return {ref.name.split("/")[0]: ref.url for ref in detail.files if ref.kind == "film" and "/" in ref.name}


def hero_picture(source, place):
    """{"url", "thumb"} of the place's hero picture (its film's first frame where it has one), or None."""
    card = source.place_card(place)
    hero = card.hero if card else None
    return {"url": hero.url, "thumb": hero.thumb_url} if hero else None


def place_media(source, place):
    """Everything the editor and the preview need to know about one place, without its step pictures."""
    copy = source.web3d(place)
    return {"place": place, "words": place_words(place), "film": own_film(source, place),
            "extras": extra_films(source, place), "hero": hero_picture(source, place),
            "web3d": bool(copy), "layers": usd_layers(source, place) if copy else []}


def refs_of(pictures):
    """[{"url", "thumb"}] of at most MOST_PICTURES picture FileRefs."""
    return [{"url": ref.url, "thumb": ref.thumb_url} for ref in pictures[:MOST_PICTURES]]


def step_images(source, place, stage):
    """The images of a step's accepted output at the place (none when it has none)."""
    detail = source.step_detail(place, stage)
    if detail is None or detail.accepted is None:
        return []
    return [ref for ref in detail.files if ref.kind == "image"]


def reference_pictures(source, place):
    """The picture of the look the place is made in (its style's reference)."""
    for engine in source.world_state().engines:
        for style in engine.styles:
            if style.picture and any(card.place == place for card in style.places):
                return [style.picture]
    return []


def concept_pictures(source, place):
    """The place's concept picture, where it has one."""
    concept = source.concept(place) if hasattr(source, "concept") else getattr(
        source.place_detail(place), "concept", None)
    return [concept] if concept else []


def plan_pictures(source, place):
    return step_images(source, place, "plan")


def pieces_pictures(source, place):
    """The place's pieces: its close-ups, else its models' turntable fronts (one a model)."""
    closeups = step_images(source, place, "closeup")
    if closeups:
        return closeups
    fronts = {}
    for ref in step_images(source, place, "surfaces-turntable"):
        if not ref.name.endswith(TURNTABLE_PASS):
            fronts.setdefault(ref.name.rsplit("/", 1)[0], ref)
    return list(fronts.values())


STEP_PICTURES = {"reference": reference_pictures, "concept": concept_pictures, "plan": plan_pictures,
                 "pieces": pieces_pictures}


def step_pictures(source, place):
    """{framework step: [{"url", "thumb"}]} of every step a step card can show, for one place."""
    return {step: refs_of(STEP_PICTURES[step](source, place)) for step in script.STEPS}
