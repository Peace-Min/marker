# Release verification

Final artifacts were built and exercised on 2026-10-23. Installer hashes, retained reports and the Windows installed-file inventory were reviewed again on 2026-10-26, Asia/Seoul.

## Windows x64

- Installer: MarkerDesktop-0.1.0-win-x64.msi, 1,939,079,282 bytes. Its SHA-256 matches the adjacent .sha256 file.
- Final installation exit code: 0. The earlier internal QA package also uninstalled with exit code 0. User result documents were preserved.
- On 2026-10-26 the final installed bundle passed SHA-256 verification for all 21,816 inventoried files.
- Installed engine includes the OCR, multimodal projection, layout, reading-order and text-error model files. No separate Python or .NET installation is used by the app.
- Actual installed-engine acceptance: embedded-image PDF and scanned image, local OCR, Markdown image references, diagnostic images, Korean/space-containing paths, and offline Wiki. Exit code 0; two successful files; 155.59 seconds for this fixture batch on the test PC. This is not a general performance benchmark.
- Raw report: qa-output/windows-release 한글/installed-report.json. Install/uninstall logs are under qa-output.
- Desktop shortcut: Marker Desktop Offline. Installed location: %LOCALAPPDATA%/Programs/MarkerDesktop.

## Linux x64

- Installer: MarkerDesktop-0.1.0-linux-x64.run, 2,129,802,656 bytes. Its SHA-256 matches the adjacent .sha256 file.
- Final installer was run inside an unshared network namespace with only loopback enabled, into a fresh user data folder containing spaces. It performed no apt/dnf operation or dependency download.
- Installed-file SHA-256 verification passed for 23,653 files. Model preflight and external-socket refusal passed.
- Installed-engine acceptance in the same disconnected namespace: embedded-image PDF, scanned-image OCR, image references, diagnostic images and offline Wiki. Exit code 0; two successful files; 86.0 seconds for the fixture batch.
- Raw copied evidence: qa-output/linux-final/release-install and qa-output/linux-final/release-acceptance.
- Reading-order model check: qa-output/linux-final/order-model.log. No missing-order-model fallback.

## Common QA

Korean/English UI bindings and persisted language, OCR option conflicts, page-range validation, Markdown/HTML/JSON/chunks output, correct chunk page indices, duplicate names, corrupt-file continuation and real C# worker cancellation passed. UI screenshots and integration artifacts are retained under qa-output. Native Linux X11 startup was checked under Xvfb.

## Scope and conditions

Windows 11 x64 and Ubuntu 24.04 x64 under WSL2 were tested. Physical Linux desktops, Rocky/RHEL, other distributions, ARM64 and GPU inference are not certified by this QA. Installation files are unsigned. Review the separate model license before organizational deployment or redistribution; successful packaging does not establish license eligibility.

Functional details and reproducible commands are in QA.md and BUILD.md. Preserve RELEASE-QA.txt and the .sha256 files with the installers. The app's bundled Wiki describes usage; this source Wiki and the adjacent release report retain final acceptance evidence.
