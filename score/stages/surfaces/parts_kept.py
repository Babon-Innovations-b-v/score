"""surfaces-parts' make with corrections to how the parts row takes a finish over (route_parts.make_parts, its
finish_parts.kit_taken, checked_finishes and reordered and route_parts.lit_finishes held to them while it runs):

- `kit_taken`: a scene shell surface takes a finish over only where it lies no further from the close-up's colour
  than the finish's own surface. Shiplock's dark locker interior, its list's frame-charcoal locker_interior dE 12.9
  from the close-up, was painted as the gunmetal hull panel at dE 27.6 and failed its recheck as mid-grey; the wall
  screen's dark bezel the same, which then baked L* 63.9 against its close-up's 25.5 (2026-11-11).
- `lit_finishes`: a code-built light's finish listed on one of the scene library's glowing surfaces is lit, whatever
  its family. Shiplock's ceiling and wall lights listed their diffusers in plastic on the glowing strip_lamp, so no
  finish was lit by family, every finish was, and their dark metal housings were painted as the blue terminal screen.
- `checked_finishes`: a surface made with the scene library's glowing recipe is judged by its own colour (owner, #8),
  whatever family the library coined. The engine room's core glow and flare, family "energy", were off their colour
  against the close-up's white-hot column (dE 55.7 and 48.9), so the free colour check's picks refused the whole take
  and its grey casing stayed on wall-charcoal (2026-11-13).
- `kit_taken` and `reordered`: a picked finish keeps its pick. The engine room's crate, ramp and shelf were picked
  (steel-grey at metal 0.6, floor-gunmetal at 0.8, engine-slate) and the kit or the order took each back to the
  surface the recheck had failed, so the one remake baked them as before and the recheck failed them again
  (2026-11-13).

Its own module, set on the row in the table (stages.parts_kept), so no row reading finish_parts.py or route_parts.py
(the bake, the recheck, the people's dress) moves for it; route_parts.make_parts runs in this process.
"""
import contextlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import finish_parts  # noqa: E402
import route_parts  # noqa: E402


# The per-take function the table answers through kept.call (stages.PER_TAKE, which sets it in this module's
# namespace while the row runs): route_parts.make_parts calls whatever this name holds then.
parts_take = route_parts.parts_take


def make_parts(inputs, out, seed, params):
    """route_parts.make_parts with kit_taken and lit_finishes held as this module's, and its per-take calls through
    this module's parts_take."""
    take = route_parts.parts_take
    route_parts.parts_take = parts_take
    try:
        with held():
            return route_parts.make_parts(inputs, out, seed, params)
    finally:
        route_parts.parts_take = take


@contextlib.contextmanager
def held():
    """finish_parts.kit_taken, checked_finishes and reordered and route_parts.lit_finishes as this module's while the
    block runs."""
    kit, checked, order, lit = (finish_parts.kit_taken, finish_parts.checked_finishes, finish_parts.reordered,
                                route_parts.lit_finishes)
    finish_parts.kit_taken, finish_parts.checked_finishes = kit_kept(kit), glow_kept(checked)
    finish_parts.reordered, route_parts.lit_finishes = pick_kept(order), lit_kept(lit)
    try:
        yield
    finally:
        finish_parts.kit_taken, finish_parts.checked_finishes, finish_parts.reordered = kit, checked, order
        route_parts.lit_finishes = lit


def kit_kept(kit_taken):
    """kit_taken, its shell surface refused where it lies further from the close-up's colour than the record's own
    surface (the record's `delta_e`), and always for a picked finish (`picked`: recheck_picks, colour_picks)."""
    def taken(record, colour, every, kit):
        if record.get("picked"):
            return record
        found = kit_taken(record, colour, every, kit)
        if found.get("kit_over") is None or record.get("delta_e") is None:
            return found
        return found if found["delta_e"] <= record["delta_e"] else record
    return taken


def glow_kept(checked_finishes):
    """checked_finishes with each surface of `every` made with the scene library's `glowing` recipe judged by its own
    colour as a light's family is (finish_parts.OWN_COLOUR), whatever family the library coined for it."""
    def checked(entry, finishes, measured, every, kit=()):
        lit = {name: dict(spec, family="light") for name, spec in every.items()
               if spec.get("recipe") == "glowing" and spec.get("family") not in finish_parts.OWN_COLOUR}
        return checked_finishes(entry, finishes, measured, {**every, **lit}, kit)
    return checked


def pick_kept(reordered):
    """reordered with a picked finish never moved off its pick's surface: the other of the pair may take a surface
    that keeps the close-up's order, else the lighter is marked off its colour by its order as before."""
    def order(lighter, darker, every, lightness, wide):
        if not (lighter.get("picked") or darker.get("picked")):
            return reordered(lighter, darker, every, lightness, wide)
        floor = finish_parts.finish_lab(darker, every)[0] - finish_parts.ORDER_KEPT
        ceiling = finish_parts.finish_lab(lighter, every)[0] + finish_parts.ORDER_KEPT
        for finish, keeps in ((lighter, lambda level: level >= floor), (darker, lambda level: level <= ceiling)):
            if finish.get("picked"):
                continue
            fit = finish_parts.nearest_in_order(finish, every, lightness, keeps)
            if fit and (wide or fit[0] < finish_parts.close_up_apart(finish, every)):
                finish.update(surface=fit[1], delta_e=round(fit[0], 1), by="nearest of its family in order")
                return True
        return False
    return order


def lit_kept(lit_finishes):
    """lit_finishes with each finish listed on a glowing surface of `every` counted lit as a light's family is, its
    own family given back after."""
    def lit(checked, every):
        glowing = {name for name, spec in every.items() if spec.get("recipe") == "glowing"}
        marked = [finish.get("surface") in glowing and finish.get("family") not in finish_parts.SEEN_THROUGH_FAMILIES
                  for finish in checked]
        found = lit_finishes([dict(finish, family="light") if mark else finish
                              for finish, mark in zip(checked, marked)], every)
        return [own_family(entry, finish) if mark else entry for entry, finish, mark in zip(found, checked, marked)]
    return lit


def own_family(entry, finish):
    """`entry` with `finish`'s family (none where it has none)."""
    kept = {key: value for key, value in entry.items() if key != "family"}
    return {**kept, "family": finish["family"]} if "family" in finish else kept
