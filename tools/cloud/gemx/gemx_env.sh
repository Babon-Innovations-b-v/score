#!/usr/bin/env bash
# GEM-X Body Motion's Python, weights and SOMA assets in one folder on a rented card machine (blender_cloud.py's `env`
# for tools/cloud/gemx/on_machine.py): built once a machine, under a lock, so jobs side by side on it never build it
# twice; a changed pin here or in requirements.txt builds the folder again (the mark is both files' hash).
#
#   bash tools/cloud/gemx/gemx_env.sh <folder>
#
# Every piece is pinned: the code by requirements.txt (GEM-X at commit 4aef1452e5df and every dependency, hashed),
# the weights by their Hugging Face revision and sha256, the person detector by its archive's and its file's sha256.
# Licences: GEM-X's code Apache-2.0 (a few EgoHand-derived files OpenMDW-1.1, ATTRIBUTIONS.md upstream); its weights
# the NVIDIA Open Model License; SOMA-X's code and assets Apache-2.0; YOLOX-X HumanArt from OpenMMLab's mmpose
# (Apache-2.0).
set -euo pipefail

folder=${1:?usage: gemx_env.sh <folder>}
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$(dirname "$folder")"
exec 9>"$folder.lock"
flock 9
mark="$folder/.built-$(cat "$0" "$here/requirements.txt" | sha256sum | cut -c1-16)"
if [ -f "$mark" ]; then
  exit 0
fi

GEMX_REVISION=b111f2dcf3ebcf57965fd53499cb645dfa5ba25c   # huggingface.co/nvidia/GEM-X, 2026-11-02
SOMA_REVISION=3648707b69e1b1dcf14c473e30613266b786b9f1   # huggingface.co/nvidia/SOMA-X tag v0.3.3 (GEM-X's runtime)
YOLOX_ZIP=https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/yolox_x_8xb8-300e_humanart-a39d44ed.zip
YOLOX_ZIP_SHA256=1c6fccc5cd450eb563b1fe4eba13c9bdf9ea8263b6ae1cb3ada765aa4ebea2c7
YOLOX_SHA256=8e9ea96a176bd48501eaaa77216e49ee30794d2f8ba80c7b9862beca4ea972da

# <url> <sha256> <path>: downloaded beside its place, checked, then moved in; a mismatch stops the build.
fetch() {
  curl -fsSL --retry 4 --retry-delay 5 "$1" -o "$3.part"
  echo "$2  $3.part" | sha256sum -c --quiet -
  mv "$3.part" "$3"
}

uv=$(command -v uv || true)
if [ -z "$uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/root/uv sh >/dev/null
  uv=/root/uv/uv
fi
"$uv" venv --clear --quiet --python 3.12 "$folder"
"$uv" pip install --quiet --python "$folder/bin/python" --require-hashes -r "$here/requirements.txt" \
  --index-url https://download.pytorch.org/whl/cu128 --extra-index-url https://pypi.org/simple \
  --index-strategy unsafe-best-match
# GEM-X calls `ffmpeg` by name: the pinned imageio-ffmpeg's static build, on the folder's bin (on_machine.py puts that
# first on PATH).
ln -sf "$("$folder/bin/python" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" "$folder/bin/ffmpeg"

weights="$folder/weights"
mkdir -p "$weights" "$folder/soma"
gemx=https://huggingface.co/nvidia/GEM-X/resolve/$GEMX_REVISION
while read -r name sha; do
  fetch "$gemx/$name" "$sha" "$weights/$name"
done <<'EOF'
body_s240000.ckpt e244d27f2834eb6382c5f6b9cbf2a38681b685514a1b2e86f8f3d2592d614959
vitpose.pth 8e3eec71dbd6bb745eba8c6debe3e4b97bcfd1d01f300099f2eedf50b9a80c8e
motion_native77_e774_s292175.ckpt c7790f4587e518bcea40cb8281c9be2233d37f6caa668835462542760dcf82aa
motion_stats_raw.npz b7719b634e0fc1f001005605d117d77448c8d4a110923149df58529c68112ed6
body_video_native77.yaml 796a306aca61e0c928888a23d74996740795bfa7cd1735bdc184d1e5274a02d7
EOF
soma=https://huggingface.co/nvidia/SOMA-X/resolve/$SOMA_REVISION
while read -r name sha; do
  fetch "$soma/$name" "$sha" "$folder/soma/$name"
done <<'EOF'
SOMA_neutral.npz 5829af4a5333abdba5ad449360b868faacee99d395971e62f35c0e7169432b63
SOMA_template_rig.usda a952cb7bdf4ccd801e355d53122d395b985b69d0d9181439edad5081bb171856
SOMA_procedural_transforms.json 9853e19ab51625ffaa7d9e7ccf0e443272c2740837604e6bacd66604e8edf509
EOF
# The release's video configuration names the detector yolox_humanart.onnx beside it: the archive's end2end.onnx.
fetch "$YOLOX_ZIP" "$YOLOX_ZIP_SHA256" "$weights/yolox_humanart.zip"
"$folder/bin/python" -I -c '
import pathlib, shutil, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:
    member = next(name for name in archive.namelist() if name.endswith("/end2end.onnx"))
    with archive.open(member) as source, pathlib.Path(sys.argv[2]).open("wb") as target:
        shutil.copyfileobj(source, target)
' "$weights/yolox_humanart.zip" "$weights/yolox_humanart.onnx.part"
echo "$YOLOX_SHA256  $weights/yolox_humanart.onnx.part" | sha256sum -c --quiet -
mv "$weights/yolox_humanart.onnx.part" "$weights/yolox_humanart.onnx"
rm "$weights/yolox_humanart.zip"

"$folder/bin/python" -c "import gem, soma, torch, onnxruntime; print('gem', 'soma', soma.__version__, 'torch', torch.__version__, 'cuda', torch.cuda.is_available())"
touch "$mark"
