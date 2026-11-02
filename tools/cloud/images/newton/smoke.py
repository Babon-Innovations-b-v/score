"""The newton image's proof job (prove.json): what its Python holds and does, in <out>/smoke.json.

    newton-run /work/repo/tools/cloud/images/newton/smoke.py <out folder>

- `versions`: every installed package's version (the proof checks newton_env.sh's pins against it).
- `cuda_devices` and `kernel_sum`: Warp's CUDA devices, and 1 + 2 + ... + KERNEL_COUNT summed by a Warp kernel on the
  first card (an atomic add a thread).
- `fall_metres`: a free sphere in MuJoCo dropped for FALL_SECONDS, how far it fell (about g t^2 / 2, 4.9 m).
"""
import importlib.metadata
import json
import pathlib
import sys

KERNEL_COUNT = 1000
FALL_SECONDS = 1.0
SPHERE = """<mujoco><option timestep="0.001" gravity="0 0 -9.81"/><worldbody>
<body pos="0 0 10"><freejoint/><geom type="sphere" size="0.1" mass="1"/></body></worldbody></mujoco>"""


def versions():
    """Every package of the image's requirements as installed, once its modules load."""
    import fcl  # noqa: F401
    import mink  # noqa: F401
    import mujoco  # noqa: F401
    import newton  # noqa: F401
    import scipy  # noqa: F401
    import warp  # noqa: F401
    from pxr import Usd  # noqa: F401
    return {distribution.metadata["Name"].lower().replace("_", "-"): distribution.version
            for distribution in importlib.metadata.distributions()}


def kernel_sum():
    """Warp's CUDA device count and 1..KERNEL_COUNT summed on the first card."""
    import warp
    warp.init()

    @warp.kernel
    def added(total: warp.array(dtype=warp.int32)):
        warp.atomic_add(total, 0, warp.tid() + 1)
    total = warp.zeros(1, dtype=warp.int32, device="cuda:0")
    warp.launch(added, dim=KERNEL_COUNT, inputs=[total], device="cuda:0")
    return warp.get_cuda_device_count(), int(total.numpy()[0])


def fall():
    """How far MuJoCo's free sphere fell in FALL_SECONDS."""
    import mujoco
    model = mujoco.MjModel.from_xml_string(SPHERE)
    data = mujoco.MjData(model)
    start = float(data.qpos[2])
    while data.time < FALL_SECONDS - 1e-9:
        mujoco.mj_step(model, data)
    return start - float(data.qpos[2])


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    devices, summed = kernel_sum()
    found = {"versions": versions(), "cuda_devices": devices, "kernel_sum": summed, "fall_metres": round(fall(), 3)}
    (out / "smoke.json").write_text(json.dumps(found, indent=1))
    print(json.dumps(found), flush=True)


if __name__ == "__main__":
    main()
