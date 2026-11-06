# QA evidence and support scope

Date: 2026-10-23 (Asia/Seoul). Product version 0.1.0.

## Verified environments

- Windows 11 x64, Intel i5-12500, 16 GB RAM, CPU PyTorch 2.14.1, portable CPython 3.12.13.
- Ubuntu 24.04 x64 under WSL2, separate Linux Python/wheels/llama.cpp. This is not a physical Ubuntu desktop certification. Rocky/RHEL, ARM64, GPU execution, and other Linux versions are unverified.

## Completed functional checks

- Windows/Linux self-contained .NET 10 publish and Avalonia UI startup.
- Korean/English resource-key parity, live switch, saved language, UI screenshots. Linux uses an embedded Noto CJK font instead of depending on host Korean fonts.
- OCR option mutual exclusion and malformed/reversed/overflow page-range rejection.
- Real cancellation of a running bundled OCR worker through the C# process runner.
- General PDF → Markdown; PDF with an embedded figure → text plus a real image file, with valid relative Markdown links.
- JSON, HTML, chunks output; chunks retain zero-based real page indices and bounding boxes.
- Duplicate input names get distinct directories. Korean/space-containing input/output paths.
- A corrupt input reports a file error and the next valid input still succeeds. Invalid range fails before model processing.
- Scanned-image forced OCR and balanced mode with included local models.
- Missing model preflight and Python refusal of an external socket; per-run empty Hugging Face cache. Integration logs were checked for unexpected external connection attempts.
- Linux native X11 app launch under Xvfb. Mesa software fallback messages do not prevent startup.

## Issues discovered and corrected

1. Windows portable Python default code page corrupted JSON output containing Korean paths. The protocol and child I/O are now explicitly UTF-8.
2. Upstream chunks used the final page-block number as the page index. A focused regression check and an actual output check cover the fix.
3. Surya's process stop logic used Windows signal 0 as a liveness test. The packaged runtime uses psutil process-tree shutdown.
4. Global Surya sentinel/log files could attach to another Marker instance. Packaged workers use an isolated per-run directory.
5. The generic OCR font had clipped Korean UI glyphs on Linux. UI now embeds Noto Sans CJK KR and was visually rechecked.
6. Linux without an XDG Documents folder produced a relative default output path. The app now falls back to an absolute home/Documents path.
7. The optional reading-order head was initially omitted, causing raster-sort fallback on some scans. The final package includes the pinned order model and uses its explicit local path. A disconnected-network OCR check confirmed no missing-order-model fallback.

## Reproducible evidence

- tests/Marker.Desktop.Checks: headless interaction assertions and screenshot capture; optional real-worker cancellation.
- tests/check_engine.py: end-to-end cases against the actual bundled interpreter, models and binaries.
- tests/check_chunk_pages.py: page index regression check.
- scripts/manifest.py: SHA-256 inventory generator/verifier.
- Local results are kept under desktop/qa-output. Linux raw reports are generated in the isolated QA build environment and copied into that folder for review.

## Release verification

Installer installation/relocation, final SHA-256 checks and isolated-network results are recorded in RELEASE-QA.md after release assembly. A passing build alone does not certify installation or offline inference. The release is unsigned; Windows policy may warn about an unknown publisher.

## Limits

Fixture success is not an accuracy benchmark for arbitrary documents. CPU speed depends on document size, scan quality and hardware. The Linux installer does not install an operating system or replace system desktop/glibc libraries. Application socket refusal is not a substitute for OS-level isolation. Model/license eligibility for organizational deployment must be reviewed separately.
