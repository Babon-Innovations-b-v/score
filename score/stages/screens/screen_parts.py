"""The screens stage on any model's screen part (#201, owner's choice of 2026-11-25): tc5r's coffee vending machine
shows a coffee picture on its LCD, which the list named "glass display screen" on `glass_screen_a` (the glass family,
no glow), so the look drew a dark pane: its row is a machine, not one that shows, and its screen is not lit, so the
screens stage (screens.make: a row whose kind shows, its lit parts) never reached it.

So beside the rows that show (screens.make, as before), every other baked model of the place is pictured on its screen
parts: each surface whose library name holds a screen word (screens.json `words`), lit or not (`named`), all of them
one picture as a display part's is (screens.pictured). A model with no such part is no gap: only a row that shows
must show something. Its record says `by` "screen part". row-kinds.json is not changed (a row kind changed there
re-buys paid rows); the stage applies to every place whose design bakes a model (`applies`).

Set on the screens row in the table (stages.SCREENS), so the assembly, whose make screens.assembled wraps and whose
code version holds score/stages/screens/__init__.py, does not move with it.
"""
import json
import pathlib

from score.stages import screens
import score.stages.row_kinds as row_kinds

BY = "screen part"


def said(name, specs, words):
    """Whether a surface's library name (its spec's `library`, else its own name) holds a screen word."""
    return bool(set(str(specs.get(name, {}).get("library", name)).replace("-", "_").split("_")) & set(words))


def named(surfaces, areas, specs, words):
    """A model's screen parts: its surfaces whose library name holds a screen word, lit or not (`areas` unused: every
    one is a screen, as screens.display's signature takes it)."""
    return [name for name in sorted(set(surfaces)) if said(name, specs, words)]


def applies(place):
    """A place whose design's surface data bakes any model (screens.applies' rows that show among them)."""
    path = screens.DESIGN_SURFACES / f"{place}.json"
    if not path.is_file():
        return False
    return bool((json.loads(path.read_text()).get("bake") or {}).get("models"))


def labelled_names(paint, take):
    """The surface names the paint labelled a take with (its labelled .ply files)."""
    return {path.stem for path in (paint / "labelled" / take).glob("*.ply")}


def make(inputs, out, seed, params):
    """screens.make (the rows that show), then every other baked model with a screen part pictured on it (named),
    added to screens.json with `by` BY."""
    screens.make(inputs, out, seed, params)
    bake, paint = pathlib.Path(inputs["surfaces-bake"]), pathlib.Path(inputs["surfaces-paint"])
    data = json.loads(pathlib.Path(inputs["surfaces"]).read_text())
    shown_takes = screens.screen_takes(data, row_kinds.table(inputs["row kinds"]))
    words = screens.rules(inputs["screens"])["words"]
    palette = screens.palette_library.read(inputs)
    colours = screens.palette_library.library_tokens(palette)
    recipes = screens.palette_library.scene_library(palette)["recipes"]
    specs = json.loads((bake / "specs.json").read_text())
    plan = screens.drawn_plan(json.loads(pathlib.Path(inputs["plan"]).read_text()) if "plan" in inputs else None)
    glass = screens.darkest(colours)
    record = json.loads((out / screens.RECORD).read_text())
    display = screens.display
    screens.display = named
    try:
        for model, entry in sorted(json.loads((bake / "baked.json").read_text()).items()):
            if entry["parts"] in shown_takes or not any(said(name, specs, words)
                                                        for name in labelled_names(paint, entry["parts"])):
                continue
            found = screens.pictured(model, screens.faces(bake / "made", model, paint / "labelled" / entry["parts"],
                                                          entry), specs, colours, glass, recipes, plan, words, out)
            if found is not None:
                record["models"][model] = dict(found, take=entry["parts"], glass=glass, by=BY)
    finally:
        screens.display = display
    (out / screens.RECORD).write_text(json.dumps(record, indent=1))
