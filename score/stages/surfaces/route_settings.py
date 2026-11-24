"""The finish list's settings on a part's library surface (#18, library first): the list matches each finish to a
library surface with settings (a palette token, roughness, metal, its own seed, and its own wear level where the views
show a cause, route_list.finishes_of); the parts row keeps them on each part whose finish kept its listed surface, and
the bake (which paints too) carries them as one library surface a setting: the variant's own spec with the list's
token colour, roughness, metal, seed and wear over it, named for the variant and those settings (`settings_name`).
recipes.arguments takes a spec's own seed and wear over the job's seed and the place's wear (owner, 2026-10-20), so
each object's wear and dirt pattern is its own, and a finish without its own wear wears at the place's level. A
finish the free colour check moved to another surface (nearest of its family by colour, the room's kit surface)
takes that surface's own spec: the list's settings were for the surface it named. A variant's second shade (a
mottle's, a leather's creases, a spangle's: `second`) moves with its colour, its CIELAB step from the colour kept
(`shade_moved`): kept as fitted, the grey leather's #686068 creases under the list's white #e8e8e8 drew the surgical
chair's seat as speckled grey-black granite (tc4r, #186). An under layer (`bare`, the metal under paint) stays.

    applied(finish)                   its settings, or None when the colour check moved its surface
    settings_name(surface, settings)  the surface a part paints and bakes as
    set_spec(spec, settings, colours) the variant's spec with the settings over it (colours: palette_library.library_tokens)
"""
SEPARATOR = "__"
OWN = ("seed", "wear")  # what a spec carries of its own over the job's seed and the place's wear (recipes.arguments)


def applied(finish):
    """A checked finish's list settings, or None when it has none or the colour check gave it another surface."""
    if not finish.get("settings") or finish["surface"] != finish.get("listed_surface", finish["surface"]):
        return None
    return finish["settings"]


def settings_name(surface, settings):
    """The name a library surface with settings paints and bakes as: the variant's, then its token, roughness and
    metal in hundredths, its seed and its own wear in hundredths where it has them (letters, digits and underscores
    only: a file stem and a prim name)."""
    token = settings["token"].replace("-", "_")
    name = f"{surface}{SEPARATOR}{token}_r{round(settings['roughness'] * 100):03d}_m{round(settings['metal'] * 100):03d}"
    name += f"_s{settings['seed']}" if "seed" in settings else ""
    return name + (f"_w{round(settings['wear'] * 100):03d}" if "wear" in settings else "")


def set_spec(spec, settings, colours):
    """The variant's resolved spec (library.spec: it keeps `library`, the variant's name) in the settings' token
    colour, roughness and metal, with its seed and own wear where it has them, the settings recorded beside."""
    own = {name: settings[name] for name in OWN if name in settings}
    colour = colours[settings["token"]]
    moved = {"second": shade_moved(spec["second"], spec["colour"], colour)} if "second" in spec else {}
    return dict(spec, token=settings["token"], colour=colour, roughness=settings["roughness"],
                metal=settings["metal"], **moved, **own, settings=dict(settings))


def shade_moved(shade, colour, new_colour):
    """A variant's second shade (linear RGB) moved with its colour onto `new_colour`: the same CIELAB step from it,
    clipped into gamut (tools/props/library/likeness/colour.py)."""
    import numpy as np
    from score.stages.props import prop_data
    with prop_data.tools("props/library/likeness"):
        import colour as lab_colour
    step = lab_colour.lab(np.asarray(shade, dtype=float)) - lab_colour.lab(np.asarray(colour, dtype=float))
    return [float(value) for value in lab_colour.linear_of_lab(lab_colour.lab(np.asarray(new_colour, dtype=float))
                                                                 + step)]
