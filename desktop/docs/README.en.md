# Marker Desktop Wiki

Convert PDFs and images to Markdown, HTML, JSON, or structural chunks on this PC. Korean and English UI switching is available in the top-right corner. This edition includes CPU OCR models and a private Python/.NET runtime. No account, API key, Python installation, or first-run download is required.

## Install

Windows x64: run `MarkerDesktop-0.1.0-win-x64.msi`, then launch Marker Desktop Offline from the desktop or Start menu. This is a per-user installation. Remove it through Windows Installed Apps.

Linux x64: run `chmod +x MarkerDesktop-0.1.0-linux-x64.run`, then execute `./MarkerDesktop-0.1.0-linux-x64.run`. This installs to a user-owned directory and registers an application-menu entry. A supported Linux desktop and its system libraries are required; see the QA support scope. Windows and Linux use separate native runtimes.

The app defaults to CPU. 16 GB RAM and enough disk space for models and results are recommended. OCR of large scanned documents can take a long time. Progress is based on completed files, not an estimate of page-level completion.

## Convert

1. Add one or more PDFs or images: PNG, JPEG, TIFF, BMP, WebP.
2. Select the output folder and format.
3. Start with Fast mode and all checkboxes off.
4. Convert documents. Cancel terminates the active worker and its child processes.
5. Open results. Every input gets a unique directory, so existing results are preserved.

Markdown/HTML images are stored alongside the document. Move the whole output folder, not only the text file. JSON includes document structure and encoded images; chunks are structural blocks with zero-based page indices, bounding boxes, and section hierarchy. Fixed-token splitting, embeddings, retrieval databases, and document translation are not part of this app. A text-only LLM cannot interpret an image from its Markdown link alone.

## Settings

- Language: switches immediately and is saved for future launches.
- Fast: lightweight layout detection, PDF text extraction, and selective OCR.
- Balanced: more VLM layout/OCR work; usually slower on CPU and not guaranteed to be more accurate.
- Pages: blank means all pages. `0,2-5` means the first and the third through sixth pages; applies to every input.
- Re-read all pages with OCR: use when embedded text is broken. May introduce recognition errors in otherwise correct text.
- Skip OCR: embedded PDF text only. Scans and image equations may be omitted. Mutually exclusive with forced OCR and stripping existing OCR.
- Ignore existing OCR: re-read pages with an invisible OCR layer.
- Keep headers/footers: retain repeated page headers and footers.
- Diagnostic files: save intermediate page images and layout details. Does not improve accuracy by itself.

External LLM correction is not exposed in this offline edition. Included local OCR/VLM inference does not require an API key.

## Troubleshooting

If scanned text is missing, turn off Skip OCR. Try forced OCR for broken embedded text. File-level errors appear in Activity; the remaining files continue. Missing models require reinstalling the full package, not an online download. Always compare important extracted text, tables, and equations with the original.

Open logs shows per-run requests, engine logs, and model-server logs. Logs may contain internal document paths or content and should remain inside your organization. Uninstallation preserves user documents and user logs/preferences.

## Technical Wiki

- [한국어](README.md)
- [Architecture](ARCHITECTURE.md)
- [Build and packaging](BUILD.md)
- [QA evidence](QA.md)
- [Licenses](LICENSES.md)
