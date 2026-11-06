# Build and packaging

Build machines may access the internet. Target installations must not need it. Keep the entire release bundle and its SHA-256 manifest inside the offline transfer process.

## Windows

Prerequisites for building: .NET SDK pinned by global.json (10.0.402), uv, the source repository, the verified Python environment at ../.venv, the downloaded model caches, and uv-managed CPython 3.12.13. These are build prerequisites, not end-user prerequisites. Build-Windows.ps1 publishes a self-contained app and uses WiX 4.0.6 to produce a per-user MSI.

```powershell
cd C:\Users\CEO\marker\desktop
.\scripts\Build-Windows.ps1
```

The engine staging script accepts --python-home and a fresh --output directory. It copies a portable interpreter and verified site-packages, replaces editable Marker references with source, applies documented Surya patches, dereferences model cache links, and retains package/license metadata. The Windows Python package versions are pinned in engine/requirements-windows.txt. Install its CPU PyTorch wheels from https://download.pytorch.org/whl/cpu, install the remaining pinned packages, and install this repository into the build environment. Stage the Windows llama.cpp b11829 binaries under ../tools/llama.cpp before packaging. Keep this package lock with the build. The generated MSI is unsigned; no signing certificate is configured.

The MSI does not download dependencies or register a background network service. It installs app/.NET/Python/models, a Start menu link, and a desktop link. User settings/results survive uninstall.

## Linux

Run scripts/prepare-linux.sh on an online x64 Linux build host after staging the shared model assets from Windows (or copying equivalent pinned models to artifacts/win-x64/engine). The build script downloads a Linux CPython, Linux CPU wheels, and llama.cpp b11829 Ubuntu binaries, then applies the same offline policy and model-path configuration. It does not reuse Windows DLLs.

Publish the UI:

```sh
dotnet publish src/Marker.Desktop -c Release -r linux-x64 --self-contained true -o artifacts/linux-x64
bash scripts/prepare-linux.sh
```

System baseline: x64 desktop Linux with compatible glibc, fontconfig, X11/Wayland/XWayland stack, ICU and standard desktop libraries. Exact verified environments belong in QA.md. This release does not claim universal Linux compatibility. The installer performs no apt/dnf calls and works without root. A build host may use apt to prepare its own QA environment.

## Checks

```powershell
.\.build\dotnet\dotnet.exe run --project tests\Marker.Desktop.Checks -c Release -- qa-output
..\.venv\Scripts\python.exe tests\check_engine.py artifacts\win-x64\engine qa-output\engine
..\.venv\Scripts\python.exe scripts\manifest.py artifacts\win-x64
..\.venv\Scripts\python.exe scripts\manifest.py artifacts\win-x64 --verify
```

Model revision pins: layout 0aee81d5fd9275c0582e545bf3a56944b1e75679; OCR GGUF 6a3a4c30e5e74446d4f8b6afd05b2f2da970f470; OCR error detection 2025_02_18. Per-file release hashes are in bundle-manifest.json.
