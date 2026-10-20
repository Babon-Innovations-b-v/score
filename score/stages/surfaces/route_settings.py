"""The finish list's settings on a part's library surface (#18, library first): the list matches each finish to a
library surface with settings (a palette token, roughness, metal and the node's seed, route_list.finishes_of); the
parts row keeps them on each part whose finish kept its listed surface, and the bake (which paints too) carries them
as one library surface a setting: the variant's own spec with the list's token colour, roughness and metal over it,
named for the variant and those settings (`settings_name`). Wear stays the place's one level (the room's wear rule,
owner), as the bake's job sets it. The seed is recorded, not applied: the bake's recipes take the job's one seed
(recipes.arguments), and letting a spec carry its own re-keys surface-tiles at every place (2026-10-20). A finish the
free colour check moved to another surface (nearest of its family by colour, the room's kit surface) takes that
surface's own spec: the list's settings were for the surface it named.

    applied(finish)                   its settings, or None when the colour check moved its surface
    settings_name(surface, settings)  the surface a part paints and bakes as
    set_spec(spec, settings, colours) the variant's spec with the settings over it (colours: library.token_colours())
"""
SEPARATOR = "__"


def applied(finish):
    """A checked finish's list settings, or None when it has none or the colour check gave it another surface."""
    if not finish.get("settings") or finish["surface"] != finish.get("listed_surface", finish["surface"]):
        return None
    return finish["settings"]


def settings_name(surface, settings):
    """The name a library surface with settings paints and bakes as: the variant's, then its token, roughness and
    metal in hundredths (letters, digits and underscores only: a file stem and a prim name)."""
    token = settings["token"].replace("-", "_")
    return f"{surface}{SEPARATOR}{token}_r{round(settings['roughness'] * 100):03d}_m{round(settings['metal'] * 100):03d}"


def set_spec(spec, settings, colours):
    """The variant's resolved spec (library.spec: it keeps `library`, the variant's name) in the settings' token
    colour, roughness and metal, the settings recorded beside."""
    return dict(spec, token=settings["token"], colour=colours[settings["token"]], roughness=settings["roughness"],
                metal=settings["metal"], settings=dict(settings))
