"""The prop benchmark's truth (#163, steps 1 and 2): which adopted NVIDIA SimReady models the prop pipeline is scored
against (the set), and what each one truly is (the truth), read free from its score_lib entry.

    from tools.props.bench import truth
    truth.the_set()            # the set file: {rule, score_lib_commit, kinds, objects}
    truth.picked(root, commit) # the set #162's rule gives on a score_lib checkout (what `pick` writes)
    truth.read(address)        # one object's truth, the shape below
    truth.Unread               # raised for an entry whose truth cannot be read as it stands

    python3 -m tools.props.bench.truth pick             # the rule run on SCORE_LIB_ROOT, written to SET_FILE
    python3 -m tools.props.bench.truth read <address>   # one summary line of an object's truth

The set file (`SET_FILE`, the one record of the benchmark in the repo): `rule` (the words of the rule), `score_lib_commit`
(the library checkout it ran on), `kinds` ({kind: {classes, words, matching}}), `objects` (a list of {address
`model/<id>@<version>`, kind (one of `_pick.KINDS`, or `overlap`), split `tune` or `held-out`, withdrawn: the
withdrawn models' addresses an overlap target replaced, else []}).

The truth (a plain dict: numpy arrays and JSON-able fields; the frame of tools/props/bench/measures: every length in
metres, Z up as NVIDIA authors it, the stage's units brought to metres, every USD instance flattened):

- `address`, `id`, `title`, `words` (its description tags), `wikidata_class`: the entry's own words.
- `vertices` float64 (V, 3); `faces` int64 (F, 3), the drawn meshes' polygons fanned into triangles, outward wound.
- `face_material` int32 (F,): each triangle's bound material, an index into `materials` (-1: none bound);
  `materials` [{prim, name, surface, one_model}], `surface` the library address its `score:surface` names (None:
  names none), `one_model` whether that surface is painted for one model (its index row's `painted_for`).
- `face_prim` int32 (F,): each triangle's mesh, an index into `prims` (its USD prim paths).
- `box`: [low, high], each [x, y, z], over the drawn triangles; `size`: high - low.
- `mass`: NVIDIA's authored MassAPI mass in kg summed over its rigid bodies (USD physics' rule: a body's own mass,
  else the masses authored under it); None when a body has none. `bodies` [{prim, mass}]; `joints` [{prim, type,
  body0, body1}], each body an index into `bodies` (-1: the world).
- `colliders`: the MuJoCo payload's colliders, the convex ones a drop trial uses (#155: Newton crashes on a triangle
  mesh collider, and 71 of the set's 83 author no Newton approximation). `friction`: the static friction they touch
  with (their physics materials', weighted by collider volume when they differ; None when none authors one).
- `payloads`: {"newton": [...], "mujoco": [...]}, each payload's variant enabled alone; a collider {prim, body (an
  index into `bodies`), approximation (as authored, "none" when not), physics_material (its prim path),
  max_hull_vertices (None: no limit), convex (bool), vertices float64 (n, 3), faces int64 (m, 3)}. The shape is the one
  the simulator collides with: MuJoCo's every mesh's convex hull (MuJoCo convexifies a mesh geom whatever it is told),
  Newton's a convexHull's hull, else the mesh itself (`convex` False: a triangle mesh, or a convexDecomposition the
  simulator cuts at load).
- `physics_materials`: {"newton": {prim: material}, "mujoco": {...}}, a material {static_friction, dynamic_friction,
  restitution, density (kg/m^3), own: its newton:/mjc: settings}, None for each it does not author.
"""
import json
import pathlib

from tools.props.bench.truth._pick import picked
from tools.props.bench.truth._read import Unread, read

REPO = pathlib.Path(__file__).resolve().parents[4]
SET_FILE = REPO / "data/checks/prop-bench-set.json"

__all__ = ["SET_FILE", "Unread", "picked", "read", "the_set"]


def the_set():
    """The set file's record."""
    return json.loads(SET_FILE.read_text())
