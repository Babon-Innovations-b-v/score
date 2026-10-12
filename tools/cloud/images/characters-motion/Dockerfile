# The character maker's motion environment with SAM3DBody-cpp, as tools/props/cloud/characters_setup.sh's motion and
# sam3dbody steps install them on a rented card; one image for both because body_picture.py (the body read off a
# picture by SAM3DBody-cpp) runs in the motion environment, as do export_body.py, head.py, the face and hair fits and
# the build. So the characters-body and characters-motion kinds share this image.
#   /root/envs/motion    Python 3.11: torch 2.11.0+cu128, Kimodo (nv-tlabs/kimodo at the commit vendor/kimodo holds,
#                        Apache-2.0) with SOMA-X (NVlabs/SOMA-X, Apache-2.0, pinned) and the rest of motion()'s list
#                        (requirements.txt, resolved and hashed).
#   /root/sam3dbody-cpp  SAM3DBody-cpp (AmmarkoV/SAM3DBody-cpp at the commit vendor/sam3dbody-cpp holds, MIT) built with
#                        CUDA 12.6 and cuDNN 9 against ONNX Runtime 1.20.1, its unpinned fetches pinned here (ggml,
#                        RGBDAcquisition); its CMakeLists forces sm_86 with PTX, so Ada and Hopper cards JIT it, as on
#                        the machines. Only the CUDA 12.6 and cuDNN runtime libraries reach the image, in
#                        /usr/local/cuda-12.6/lib64 where chain.py points LD_LIBRARY_PATH.
# No weights: score-job fetches Kimodo, its Llama 3 text encoder, SOMA-X's assets and SAM3DBody-cpp's ONNX models into
# the node cache (models.json), and run.sh links them where the tools look.
ARG BASE

FROM ${BASE} AS engine
ARG SAM3DBODY_COMMIT=f4bd235f9ad3667003c8a24abbafb29cf1a53aad
ARG GGML_COMMIT=ffa4e8b80930029a35991f94e7c8a93cd67730ab
ARG RGBD_COMMIT=e3447eb3b7470efa47e9cd56507825add653609b
ARG ORT_VERSION=1.20.1
ARG ORT_SHA256=6bfb87c6ebe55367a94509b8ef062239e188dccf8d5caac8d6909b2344893bf0
ARG CUDA_TOOLKIT=12.6.3-1
ARG CUDNN=9.27.0.42-1
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends build-essential cmake git wget unzip libjpeg-dev libpng-dev \
      libzstd-dev liblz4-dev libopencv-dev libgl1-mesa-dev libglew-dev "cuda-toolkit-12-6=${CUDA_TOOLKIT}" \
      "libcudnn9-cuda-12=${CUDNN}" "libcudnn9-dev-cuda-12=${CUDNN}" >/dev/null \
 && rm -rf /var/lib/apt/lists/*
RUN fetch() { git init -q "$3" && git -C "$3" fetch -q --depth 1 "$1" "$2" && git -C "$3" checkout -q FETCH_HEAD \
      && test "$(git -C "$3" rev-parse HEAD)" = "$2"; } \
 && fetch https://github.com/AmmarkoV/SAM3DBody-cpp "${SAM3DBODY_COMMIT}" /root/sam3dbody-cpp \
 && fetch https://github.com/ggml-org/ggml "${GGML_COMMIT}" /opt/src/ggml \
 && fetch https://github.com/AmmarkoV/RGBDAcquisition "${RGBD_COMMIT}" /root/sam3dbody-cpp/RGBDAcquisition \
 && ln -s /root/sam3dbody-cpp/RGBDAcquisition/opengl_acquisition_shared_library/opengl_depth_and_color_renderer/src/Library \
      /root/sam3dbody-cpp/src/GraphicsEngine \
 && ln -s /root/sam3dbody-cpp/RGBDAcquisition/tools/AmMatrix /root/sam3dbody-cpp/src/AmMatrix \
 && curl -fsSL -o /tmp/ort.tgz \
      "https://github.com/microsoft/onnxruntime/releases/download/v${ORT_VERSION}/onnxruntime-linux-x64-gpu-${ORT_VERSION}.tgz" \
 && echo "${ORT_SHA256}  /tmp/ort.tgz" | sha256sum -c - \
 && mkdir -p /opt/onnxruntime && tar -xzf /tmp/ort.tgz -C /opt/onnxruntime --strip-components 1 && rm /tmp/ort.tgz
RUN cd /root/sam3dbody-cpp \
 && PATH=/usr/local/cuda-12.6/bin:$PATH cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DONNX_RUNTIME_DIR=/opt/onnxruntime \
      -DFETCHCONTENT_SOURCE_DIR_GGML=/opt/src/ggml >/tmp/configure.log \
 && grep -q "CUDA 12.6" /tmp/configure.log \
 && PATH=/usr/local/cuda-12.6/bin:$PATH cmake --build build -- -j"$(nproc)" >/tmp/build.log \
 && test -f build/libfast_sam_3dbody.so
# What the built engine loads at run time, by package: the final stage installs exactly these.
# The engine's own shared libraries (ggml's, miniz's) stay where its RPATH finds them, under build/_deps; only the
# build's object files go.
RUN for library in /root/sam3dbody-cpp/build/fast_sam_3dbody_run $(find /root/sam3dbody-cpp/build -name '*.so*' -type f) \
      /opt/onnxruntime/lib/libonnxruntime*.so*; do \
      LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:/opt/onnxruntime/lib ldd "$library"; done \
    | awk '/=> \// {print $3}' | sort -u | xargs -r readlink -f | xargs -r dpkg -S 2>/dev/null \
    | cut -d: -f1 | sort -u > /opt/runtime-packages \
 && echo libcudnn9-cuda-12 >> /opt/runtime-packages && cat /opt/runtime-packages \
 && find /root/sam3dbody-cpp/build -name '*.o' -delete \
 && rm -rf /root/sam3dbody-cpp/.git /root/sam3dbody-cpp/RGBDAcquisition/.git

FROM ${BASE}
ARG CUDNN=9.27.0.42-1
ARG KIMODO_COMMIT=58e781898b3d7e328a676a75d3e338c45dce3ad9
ARG SOMA_COMMIT=d6aa640f7787498009c4e3d57fcc14a243905d10
ARG PYTHON=3.11.15
COPY --from=engine /opt/runtime-packages /opt/runtime-packages
RUN apt-get update -qq \
 && apt-get install -y -qq --no-install-recommends git libgl1 libegl1 libglib2.0-0 libgomp1 \
      $(sed "s/^libcudnn9-cuda-12$/libcudnn9-cuda-12=${CUDNN}/" /opt/runtime-packages) >/dev/null \
 && rm -rf /var/lib/apt/lists/*
COPY --from=engine /opt/onnxruntime /opt/onnxruntime
COPY --from=engine /root/sam3dbody-cpp /root/sam3dbody-cpp
# Every library the engine loads is found (the driver's libcuda comes from the node at run time).
RUN ! LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:/opt/onnxruntime/lib ldd /root/sam3dbody-cpp/build/libfast_sam_3dbody.so \
      $(find /root/sam3dbody-cpp/build -name '*.so*' -type f) /opt/onnxruntime/lib/libonnxruntime_providers_cuda.so \
      | grep "not found" | grep -v "libcuda.so.1" 

COPY requirements.txt /root/envs/motion-requirements.txt
RUN uv venv --quiet --python ${PYTHON} /root/envs/motion \
 && uv pip sync --quiet --python /root/envs/motion/bin/python --require-hashes --index-strategy unsafe-best-match \
      --index-url https://pypi.org/simple --extra-index-url https://download.pytorch.org/whl/cu128 \
      /root/envs/motion-requirements.txt
# Kimodo's install builds its MotionCorrection extension with cmake (the environment's own, as the setup's PATH gave it)
# and a C++ compiler, fetching pybind11 and Eigen at their pinned tags; the compiler is removed after.
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends build-essential >/dev/null \
 && git init -q /root/kimodo \
 && git -C /root/kimodo fetch -q --depth 1 https://github.com/nv-tlabs/kimodo "${KIMODO_COMMIT}" \
 && git -C /root/kimodo checkout -q FETCH_HEAD \
 && test "$(git -C /root/kimodo rev-parse HEAD)" = "${KIMODO_COMMIT}" && rm -rf /root/kimodo/.git \
 && PATH="/root/envs/motion/bin:$PATH" uv pip install --quiet --python /root/envs/motion/bin/python --no-deps \
      -e /root/kimodo "py-soma-x @ git+https://github.com/NVlabs/SOMA-X.git@${SOMA_COMMIT}" \
 && apt-get purge -y -qq build-essential >/dev/null && apt-get autoremove -y -qq >/dev/null \
 && rm -rf /var/lib/apt/lists/* \
 && /root/envs/motion/bin/python -c "import soma, kimodo, pxr, cv2; print('motion ok')" \
 && mkdir -p /root/motion-home && ln -s /root/envs/motion /root/motion-home/env

COPY --chmod=755 run.sh /usr/local/bin/characters-run
ENV LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64
