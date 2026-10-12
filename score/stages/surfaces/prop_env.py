"""The surface stage's steps that need trimesh, SciPy and the prop tools run in the prop environment (PROPS_PYTHON),
each through its own module's command line: `<module>.py <step> <inputs listing> <out>`, under a memory cap.

    def make_paint(inputs, out, seed, params):     # a Stage's make, defined in the step's own module, so that
        prop_env.handover(__file__, "paint", inputs, out)   # module is the make's code version
    prop_env.main(STEPS)                           # in the module: run the step the command line names
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", PROPS_HOME / "env/bin/python"))
MEMORY = "MemoryMax=14G"
LISTING = ".inputs.json"  # the make's inputs listing, beside its output while the step runs


def run(module, step, listing, out, *more):
    """One module's step in the prop environment under the memory cap (`more`: the step's own arguments)."""
    checked(["systemd-run", "--user", "--scope", "-q", "-p", MEMORY, "nice", str(PROPS_PYTHON), str(module), step,
             str(listing), str(out), *more], f"{pathlib.Path(module).name} {step}")


def checked(command, what):
    """Run a command to its end; when it fails, an error with its output's tail, and for a killed process its signal
    and peak memory (campgrounds' and garage's paint, killed at the memory cap on 2026-10-12, said nothing)."""
    with tempfile.TemporaryFile("w+") as output:
        process = subprocess.Popen(command, cwd=REPO, stdout=output, stderr=subprocess.STDOUT, text=True)
        _, status, usage = os.wait4(process.pid, 0)
        process.returncode = code = os.waitstatus_to_exitcode(status)
        output.seek(0)
        text = output.read()
    if code == 0:
        return
    killed = (f", killed by {signal.Signals(-code).name} at a peak of {usage.ru_maxrss / 1e6:.1f} GB "
              f"(the cap: {MEMORY})" if code < 0 else "")
    raise RuntimeError(f"{what} failed with exit code {code}{killed}: {text[-4000:]}")


def handover(module, step, inputs, out):
    """Write the make's inputs' paths beside its output and run `step` of `module` on them."""
    listing = out / LISTING
    listing.write_text(json.dumps({name: str(path) for name, path in inputs.items()}))
    try:
        run(module, step, listing, out)
    finally:
        listing.unlink()


def short(inputs):
    """{step: path} for the rows' inputs (surfaces-<step>, the trial's fm-<step>); world files keep their
    names."""
    return {(name.rsplit("-", 1)[1] if name.startswith(("surfaces-", "fm-")) else name): pathlib.Path(path)
            for name, path in inputs.items()}


def main(steps):
    """The prop environment's side: the step the command line names, on its inputs listing and output folder."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    step, listing, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    steps[step](short(json.loads(listing.read_text())), out, *sys.argv[4:])
