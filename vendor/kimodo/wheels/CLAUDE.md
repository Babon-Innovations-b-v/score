# vendor/kimodo/wheels

Kimodo's MotionCorrection (`../MotionCorrection`, C++ via CMake, pybind11 and Eigen) as prebuilt wheels, so no box
that runs `uv sync` compiles it: the conductor has no compiler and no agent can install one (#70, 2026-11-06).
pyproject.toml's `motion-correction` is a path source to each wheel, one per Python in `requires-python`, chosen by
marker; torch, its unused wrapper's requirement, stays out by pyproject's override.

- `motion_correction-1.0.0-cp311-cp311-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` (219,357 bytes)
- `motion_correction-1.0.0-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` (219,525 bytes)

Linux x86_64 with glibc 2.28 or later and AVX (its CMakeLists builds with `-msse4.1 -mavx`) only.

**Rebuild** (docker, network; a CPU build on this PC): `bash vendor/kimodo/wheels/build.sh`, then `uv lock` (a
wheel's hash is in uv.lock). It runs `quay.io/pypa/manylinux_2_28_x86_64@sha256:7e41b1c7fd64dfc69703a1124b43c404382973ee06ec5d764b85c34d2221fded`
(gcc 14.2.1, cmake 4.x, auditwheel 6.8.2), setuptools 80.9.0 and wheel 0.45.1 pinned, from a scratch copy of the
source whose CMakeLists asks for Python's `Development.Module` instead of `Development` (manylinux has no
libpython to embed); the vendored source stays as released. Kimodo's own `.gitignore` ignores `wheels/`: add a file
here with `git add -f`. A new Python in `requires-python` needs its tag in build.sh's loop and its source in
pyproject.toml.
