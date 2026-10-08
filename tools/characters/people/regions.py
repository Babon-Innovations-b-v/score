"""Which part of a person each joint belongs to, so the body can be drawn in more than one colour.

The crew wear clothes, and the cheapest clothes in the world are no clothes at all: the body is
one mesh, but its triangles are handed out to three surfaces by the joint they hang from, and a
surface is what a material goes on. So overalls, bare hands and boots cost nothing but a name,
and changing what the crew wear is a material swap rather than new geometry.

That only works because the look is flat colour. In a realistic style the seam between two
surfaces would need a hem to hide it.

There is no suit here. A suit is bulkier than the body underneath it, so it is its own mesh with
these same weights transferred onto it, and it is not built yet.
"""

SKIN = "skin"
CLOTHES = "clothes"
BOOTS = "boots"

# In the order they are tried: the first rule whose test matches a joint name wins, and anything
# no rule claims is clothes. Written as tests on the name rather than a list of all 78 joints,
# because the body model names its joints from a scheme and a list would rot the first time a
# joint was added.
_RULES = (
    (SKIN, ("Head", "Jaw", "Eye", "Neck")),
    (SKIN, ("Hand",)),
    (BOOTS, ("Foot", "Toe")),
)


def region_of(joint_name):
    """Which surface the vertices hanging from one joint belong to."""
    for region, marks in _RULES:
        if any(mark in joint_name for mark in marks):
            return region
    return CLOTHES


def regions_of(joint_names):
    """The same answer for a whole skeleton, in the order the joints were given."""
    return [region_of(name) for name in joint_names]


def surfaces(joint_names):
    """The surface names in a fixed order, so the mesh a run writes is the same every time."""
    found = set(regions_of(joint_names))
    return [name for name in (SKIN, CLOTHES, BOOTS) if name in found]
