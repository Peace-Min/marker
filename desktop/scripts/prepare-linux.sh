#!/usr/bin/env bash
set -euo pipefail
# Run on an internet-connected Linux x64 build host. Runtime use is offline.
desktop=$(cd -- "$(dirname -- "$0")/.." && pwd)
stage="${MARKER_LINUX_STAGE:-$desktop/artifacts/linux-x64}"
build="${MARKER_LINUX_BUILD:-$desktop/.build/linux}"
mkdir -p "$build" "$stage/engine"
if [ "$stage" != "$desktop/artifacts/linux-x64" ]; then
  tar -C "$desktop/artifacts/linux-x64" --exclude='./engine' -cf - . | tar -C "$stage" -xf -
fi
if [ ! -x "$build/uv/uv" ]; then
  mkdir -p "$build/uv"
  curl -fL https://github.com/astral-sh/uv/releases/download/0.11.6/uv-x86_64-unknown-linux-gnu.tar.gz -o "$build/uv.tar.gz"
  tar -xzf "$build/uv.tar.gz" -C "$build/uv" --strip-components=1
fi
uv="$build/uv/uv"
"$uv" python install 3.12.13 --install-dir "$build/python"
python_home=$(find "$build/python" -maxdepth 1 -type d -name 'cpython-3.12.13-linux-x86_64-gnu' -print -quit)
if [ -z "$python_home" ]; then echo 'Portable Python not found' >&2; exit 1; fi
if [ ! -d "$stage/engine/python" ]; then cp -a "$python_home" "$stage/engine/python"; fi
python="$stage/engine/python/bin/python3"
# The lock file is captured from the verified Windows installation. OS-specific wheels are resolved on Linux.
"$uv" pip install --break-system-packages --python "$python" torch==2.14.1+cpu torchvision==0.29.1+cpu --index-url https://download.pytorch.org/whl/cpu
"$uv" pip install --break-system-packages --python "$python" -r "$desktop/engine/requirements-linux.txt"
site=$($python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
mkdir -p "$site/marker" "$site/static"
cp -a "$desktop/../marker/." "$site/marker/"
cp -a "$desktop/../static/." "$site/static/"
"$python" -c 'import importlib.util,sys; from pathlib import Path; p=Path(sys.argv[1]); spec=importlib.util.spec_from_file_location("prep",p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.patch_surya(Path(sys.argv[2]))' "$desktop/scripts/prepare_engine.py" "$site"
cp "$desktop/engine/sitecustomize.py" "$site/sitecustomize.py"
cp "$desktop/engine/worker.py" "$desktop/engine/sitecustomize.py" "$stage/engine/"
if [ ! -d "$stage/engine/models" ]; then cp -aL "$desktop/artifacts/win-x64/engine/models" "$stage/engine/models"; fi
mkdir -p "$stage/engine/fonts"
cp -a "$desktop/../static/fonts/." "$stage/engine/fonts/"
mkdir -p "$stage/engine/llama" "$stage/engine/licenses"
curl -fL https://github.com/ggml-org/llama.cpp/releases/download/b11829/llama-b11829-bin-ubuntu-x64.tar.gz -o "$build/llama.tar.gz"
tar -xzf "$build/llama.tar.gz" -C "$stage/engine/llama" --strip-components=1
cp -a "$desktop/artifacts/win-x64/engine/licenses/." "$stage/engine/licenses/"
chmod +x "$stage/Marker.Desktop" "$stage/engine/llama/llama-server"
"$python" "$stage/engine/worker.py" --check
printf '\nLinux engine ready: %s\n' "$stage"
