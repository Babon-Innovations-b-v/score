"""The finish list's settings on a part's library surface (#18, library first): the list matches each finish to a
library surface with settings (a palette token, roughness, metal, its own seed, and its own wear level where the views
show a cause, route_list.finishes_of); the parts row keeps them on each part whose finish kept its listed surface, and
the bake (which paints too) carries them as one library surface a setting: the variant's own spec with the list's
token colour, roughness, metal, seed and wear over it, named for the variant and those settings (`settings_name`).
recipes.arguments takes a spec's own seed and wear over the job's seed and the place's wear (owner, 2026-10-20), so
each object's wear and dirt pattern is its own, and a finish without its own wear wears at the place's level. A
finish the free colour check moved to another surface (nearest of its family by colour, the room's kit surface)
takes that surface's own spec: the list's settings were for the surface it named.

    applied(finish)                   its settings, or None when the colour check moved its surface
    settings_name(surface, settings)  the surface a part paints and bakes as
    set_spec(spec, settings, colours) the variant's spec with the settings over it (colours: library.token_colours())
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
    return dict(spec, token=settings["token"], colour=colours[settings["token"]], roughness=settings["roughness"],
                metal=settings["metal"], **own, settings=dict(settings))
