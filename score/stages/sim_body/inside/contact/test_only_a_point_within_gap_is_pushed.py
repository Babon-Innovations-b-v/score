"""contact: the ground pushes the person's skin (`Skin`, carried by the body's bones) only where it comes within GAP
of the drawn ground, whichever drawn surface that is (a seat as a floor), inside a friction pyramid when slow and
sliding against its slip when fast, a point blended over two bodies moving with both by its weights (worked by hand).
It runs in Newton's own Python (MuJoCo pinned there; score/stages/physics/inside/newton_env.sh, built at
$PROPS_HOME/envs/newton_env): with none built there, as in `make tests`' sandbox home, it prints `skipped`.

Breaks (each applied once with the env linked into a sandbox home, seen red, reverted), 2026-10-28:
- pushes' `<= GAP` made `<= 1.0`: a ball 6 mm over the ground is pushed.
- pushes' `np.linalg.norm(moving) > SLIDE_MOST` made `< SLIDE_MOST`: a slow point slides and a fast one sticks.
2026-11-01:
- pushes' `own` made the colliders' points (`surface(model, data, range(model.ngeom)) @ TO_OWN.T`, the contact before
  the skin): the ball's 3 cm collider stands 24 mm over its seat inside its 5 cm skin, and nothing is pushed.
- Skin.jacobian's `found += self.weights[point, segment] * along` made `found += along`: the half-and-half point
  moves as fast as the ball.

Run: .venv/bin/python score/stages/sim_body/inside/contact/test_only_a_point_within_gap_is_pushed.py
"""
import os
import pathlib
import subprocess
import sys

INSIDE = pathlib.Path(__file__).resolve().parents[1]
IN_ENV = "SIM_BODY_INSIDE_TEST"
BALL = """<mujoco model="ball">
  <worldbody>
    <body name="ball" pos="0 0 1">
      <freejoint/>
      <geom name="ball" type="sphere" size="0.03" mass="1"/>
    </body>
  </worldbody>
</mujoco>
"""


SKIN = 0.05  # the ball's skin's radius (m), its collider 3 cm inside it


def flat():
    """The ground: a 10 m square at height 0 (the person's frame, Y up), two triangles."""
    import numpy as np
    return np.array([[[-5.0, 0.0, -5.0], [5.0, 0.0, 5.0], [5.0, 0.0, -5.0]],
                     [[-5.0, 0.0, -5.0], [-5.0, 0.0, 5.0], [5.0, 0.0, 5.0]]])


def seated():
    """The flat ground with a seat: a 50 cm square top 0.45 m over it, round the ball's line."""
    import numpy as np
    top = np.array([[[-0.25, 0.45, -0.25], [0.25, 0.45, 0.25], [0.25, 0.45, -0.25]],
                    [[-0.25, 0.45, -0.25], [-0.25, 0.45, 0.25], [0.25, 0.45, 0.25]]])
    return np.concatenate([flat(), top])


def ball_at(height, speed=0.0):
    """The ball's model and its data with its centre `height` metres up (MuJoCo's frame, Z up), moving `speed` m/s
    along x."""
    import mujoco
    model = mujoco.MjModel.from_xml_string(BALL)
    data = mujoco.MjData(model)
    data.qpos[2], data.qvel[0] = height, speed
    mujoco.mj_forward(model, data)
    return model, data


def skin_of(model, data, shares=((1, 1.0),)):
    """The ball's skin: SOMA-like points SKIN round its centre in 26 directions, bound where it stands now, each
    point's weight `shares` [(body, share)], every segment riding its body's frame."""
    import contact
    import model as built_model
    import numpy as np
    directions = np.array([[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z], float)
    centre = built_model.TO_OWN @ data.xpos[1]
    points = centre + SKIN * directions / np.linalg.norm(directions, axis=1, keepdims=True)
    bodies = [body for body, _ in shares]
    weights = np.tile([share for _, share in shares], (len(points), 1))
    return contact.Skin(points, weights, [built_model.own_pose(model, data, body) for body in bodies], bodies,
                        [np.eye(4)] * len(bodies))


def pushed(height, ground, speed=0.0):
    """The ground's pushes on the ball's skin, its centre `height` up."""
    import contact
    import ground as grounds
    model, data = ball_at(height, speed)
    return contact.pushes(model, data, ground, grounds.normals(ground), skin_of(model, data))


def only_a_point_within_gap_is_pushed():
    """The ball's skin (5 cm) with its bottom 4 mm over the ground: its one lowest point is pushed, along the four
    edges of the friction pyramid (normal up, plus or minus FRICTION across); 6 mm over it, nothing is pushed."""
    import numpy as np
    near, far = pushed(0.054, flat()), pushed(0.056, flat())
    problems = [] if len(near) == 1 and len(near[0][2]) == 4 else [f"4 mm over: {len(near)} points pushed"]
    if near and not np.allclose(sorted(np.round(edge, 9).tolist() for edge in near[0][2]),
                                sorted([[0.0, 0.5, 1.0], [0.0, -0.5, 1.0], [0.5, 0.0, 1.0], [-0.5, 0.0, 1.0]])):
        problems.append(f"4 mm over: edges {[edge.tolist() for edge in near[0][2]]}")
    return problems + ([] if not far else [f"6 mm over: {len(far)} points pushed"])


def a_seat_carries_the_skin_on_it():
    """The ball's skin 4 mm over a seat 0.45 m up (its collider 24 mm over it): the seat pushes its one lowest point,
    straight up (MuJoCo's z), booked on the ball; the floor under the seat pushes nothing."""
    import numpy as np
    found = pushed(0.45 + 0.054, seated())
    if len(found) != 1:
        return [f"on the seat: {len(found)} points pushed"]
    body, along, edges = found[0]
    problems = [] if body == 1 else [f"booked on body {body}"]
    return problems + ([] if np.allclose(np.mean(edges, axis=0), [0.0, 0.0, 1.0]) else [f"edges {edges}"])


def a_fast_point_slides_against_its_slip():
    """The same ball moving 2 m/s along x (over SLIDE_MOST, 1.2 m/s): one edge, the normal and FRICTION of it
    against the slip, (-0.5, 0, 1)."""
    import numpy as np
    found = pushed(0.054, flat(), 2.0)
    edges = found[0][2] if found else []
    return [] if len(edges) == 1 and np.allclose(edges[0], [-0.5, 0.0, 1.0]) else [f"sliding edges {edges}"]


def a_blended_point_moves_by_its_weights():
    """A skin point weighed half on the ball and half on the still world: its Jacobian is half the ball's point's."""
    import mujoco
    import numpy as np
    model, data = ball_at(0.054)
    half = skin_of(model, data, ((1, 0.5), (0, 0.5)))
    whole = np.zeros((3, model.nv))
    mujoco.mj_jac(model, data, whole, None, data.xpos[1] + [0.0, 0.0, -SKIN], 1)
    lowest = int(np.argmin(half.points[:, 1]))
    found = half.jacobian(model, data, half.by_segment(model, data), lowest)
    return [] if np.allclose(found, 0.5 * whole) else [f"Jacobian {found.round(3).tolist()}, not half the ball's"]


CHECKS = (only_a_point_within_gap_is_pushed, a_seat_carries_the_skin_on_it, a_fast_point_slides_against_its_slip,
          a_blended_point_moves_by_its_weights)


def in_newton():
    """The checks, in Newton's own Python."""
    sys.path.insert(0, str(INSIDE))
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    if os.environ.get(IN_ENV):
        sys.exit(in_newton())
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[5] / "conftest.py"))["refuse_outside_sandbox"]()
    env = pathlib.Path(os.environ["PROPS_HOME"]) / "envs/newton_env"
    if not list(env.glob(".built-*")):
        print(f"skipped: no Newton env built at {env} (score/stages/physics/inside/newton_env.sh)")
        sys.exit(0)
    sys.exit(subprocess.run([str(env / "bin/python"), "-B", __file__], env={**os.environ, IN_ENV: "1"}).returncode)
