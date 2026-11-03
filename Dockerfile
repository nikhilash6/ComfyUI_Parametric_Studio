# Parametric Studio in one container: ComfyUI and the studio, installed by install.py exactly as on a bare machine.
# Build:  docker build -t parametric-studio .
# Run:    docker run --gpus all --network host -v ps-models:/opt/runtime/ComfyUI/models -v ps-output:/opt/runtime/ComfyUI/output -e PSN_GOALS=anime parametric-studio
#         then open http://127.0.0.1:8310. With --network host the studio and ComfyUI listen on this computer's 127.0.0.1 only, as a bare install does. The first start downloads the goals in PSN_GOALS into the models volume (anime is the smallest, about 9 GB); later starts reuse them.
# Gated models need -e HF_TOKEN=... and their licence accepted on Hugging Face. Only the NVIDIA driver comes from the host (the NVIDIA Container Toolkit); CUDA comes with PyTorch's wheels.
# To publish a port instead (-p 8310:8310 -e STUDIO_HOST=0.0.0.0), the studio is then open to the network and asks for pairing (STUDIO_TOKEN), as server.py does for any non-local address.
FROM ubuntu:24.04

ARG VRAM_GB=24
ARG CHANNEL=stable
ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 \
    RUNTIME=/opt/runtime REPO=/opt/parametric-studio \
    STUDIO_HOST=127.0.0.1 STUDIO_PORT=8310 COMFYUI_URL=http://127.0.0.1:8200 TORCH_DISABLE_NATIVE_JIT=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip git ffmpeg ca-certificates curl tini \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home studio \
 && mkdir -p "$RUNTIME" "$REPO" && chown studio:studio "$RUNTIME" "$REPO"

COPY --chown=studio:studio . $REPO
USER studio
WORKDIR $REPO

# Software only at build time. There is no GPU during a build, so the planner is told it is an NVIDIA card (VRAM_GB) instead of guessing CPU and fetching the wrong PyTorch.
RUN printf '{"os": "linux", "gpus": [{"name": "NVIDIA (container)", "vram_gb": %s, "vendor": "nvidia"}], "ram_gb": 32.0, "disk_free_gb": 500.0, "backend": "cuda", "caps": ["bf16"]}\n' "$VRAM_GB" > "$RUNTIME/profile.json" \
 && python3 install.py --yes --no-models --channel "$CHANNEL" --profile-json "$RUNTIME/profile.json" --dir "$RUNTIME" \
 && test -x "$RUNTIME/venv/bin/python" && test -f "$RUNTIME/ComfyUI/main.py" \
 && mkdir -p "$RUNTIME/ComfyUI/output" "$RUNTIME/ComfyUI/input"

RUN printf '%s\n' '#!/bin/sh' \
  'set -e' \
  '# Models: fetch the goals asked for into the models volume. install.py keeps finished files and resumes partial ones, so a restart costs nothing.' \
  'if [ -n "$PSN_GOALS" ]; then python3 "$REPO/install.py" --yes --goals "$PSN_GOALS" --channel "${CHANNEL:-stable}" --dir "$RUNTIME" ${HF_TOKEN:+--include-gated}; fi' \
  'M="$RUNTIME/ComfyUI/models"' \
  '"$RUNTIME/venv/bin/python" "$RUNTIME/ComfyUI/main.py" --listen 127.0.0.1 --port 8200 $COMFY_FLAGS &' \
  'export STUDIO_MODELS_ROOT="$M" PSN_MODELS_ROOT="$M" STUDIO_OUTPUT_DIR="$RUNTIME/ComfyUI/output" STUDIO_COMFY_INPUT="$RUNTIME/ComfyUI/input"' \
  'cd "$REPO" && exec "$RUNTIME/venv/bin/python" -m studio.server' > "$RUNTIME/start.sh" \
 && chmod +x "$RUNTIME/start.sh"

VOLUME ["/opt/runtime/ComfyUI/models", "/opt/runtime/ComfyUI/output"]
EXPOSE 8310
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s CMD curl -fsS http://127.0.0.1:8310/api/health >/dev/null || exit 1
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/runtime/start.sh"]
