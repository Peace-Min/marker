"""A local, line-delimited JSON worker. No external LLM or downloads."""
import argparse
import atexit
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import traceback
import uuid

ROOT = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
PROTOCOL = sys.stdout
sys.stdout = sys.stderr


def emit(kind, **fields):
    PROTOCOL.write(json.dumps({"type": kind, **fields}, ensure_ascii=False) + "\n")
    PROTOCOL.flush()


def configure():
    runtime = Path(os.environ.get("MARKER_RUNTIME_DIR", tempfile.mkdtemp(prefix="marker-run-")))
    runtime.mkdir(parents=True, exist_ok=True)
    models = ROOT / "models"
    settings = {
        "TORCH_DEVICE": "cpu", "SURYA_INFERENCE_BACKEND": "llamacpp",
        "SURYA_INFERENCE_URL": "", "FAST_LAYOUT_SERVER_URL": "", "OCR_ERROR_SERVER_URL": "",
        "SURYA_INFERENCE_KEEP_ALIVE": "false", "SURYA_INFERENCE_PARALLEL": "1",
        "SURYA_INFERENCE_TIMEOUT_SECONDS": "1800", "SURYA_INFERENCE_STARTUP_TIMEOUT": "900",
        "LLAMA_CPP_BINARY": str(ROOT / "llama" / ("llama-server.exe" if os.name == "nt" else "llama-server")),
        "LLAMA_CPP_NGL": "0", "LLAMA_CPP_EXTRA_ARGS": f"--threads {min(os.cpu_count() or 2, 6)}",
        "SURYA_GGUF_LOCAL_MODEL_PATH": str(models / "ocr" / "surya-2.gguf"),
        "SURYA_GGUF_LOCAL_MMPROJ_PATH": str(models / "ocr" / "surya-2-mmproj.gguf"),
        "FAST_LAYOUT_MODEL_CHECKPOINT": str(models / "layout"),
        "FAST_ORDER_MODEL_CHECKPOINT": str(models / "layout" / "order"),
        "FAST_LAYOUT_USE_ORDER": "false", "FAST_LAYOUT_NUM_THREADS": str(min(os.cpu_count() or 2, 6)),
        "OCR_ERROR_MODEL_CHECKPOINT": str(models / "ocr-error"),
        "MODEL_CACHE_DIR": str(runtime / "model-cache"),
        "HF_HOME": str(runtime / "empty-hf"), "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "MARKER_RUNTIME_DIR": str(runtime), "DISABLE_TQDM": "true",
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1",
        "GOOGLE_API_KEY": "", "GEMINI_API_KEY": "", "OPENAI_API_KEY": "",
        "NO_PROXY": "localhost,127.0.0.1,::1", "no_proxy": "localhost,127.0.0.1,::1",
        "FONT_DIR": str(ROOT / "fonts"), "FONT_PATH": str(ROOT / "fonts" / "GoNotoCurrent-Regular.ttf"),
    }
    os.environ.update(settings)
    # Enforce offline policy even when run from a developer Python installation.
    import importlib.util
    spec = importlib.util.spec_from_file_location("marker_offline_policy", ROOT / "sitecustomize.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = [Path(settings[name]) for name in ("LLAMA_CPP_BINARY", "SURYA_GGUF_LOCAL_MODEL_PATH", "SURYA_GGUF_LOCAL_MMPROJ_PATH", "FONT_PATH")]
    required += [models / "layout" / "rfdetr_layout.pth", models / "layout" / "order" / "order_ar.pt", models / "ocr-error" / "model.safetensors"]
    missing = [str(path) for path in required if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise FileNotFoundError("Incomplete offline installation: " + ", ".join(missing))
    return runtime


def cleanup_children():
    import psutil
    children = psutil.Process().children(recursive=True)
    for process in reversed(children):
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(children, timeout=5)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            pass


def validate(request):
    if request.get("format") not in {"markdown", "json", "html", "chunks"}:
        raise ValueError("Unsupported output format")
    if request.get("mode") not in {"fast", "balanced"}:
        raise ValueError("Unsupported processing mode")
    if request.get("force_ocr") and request.get("disable_ocr"):
        raise ValueError("Force OCR and Skip OCR cannot both be selected")
    if request.get("strip_existing_ocr") and request.get("disable_ocr"):
        raise ValueError("Ignoring existing OCR requires OCR to be enabled")
    pages = request.get("page_range", "").strip()
    if pages:
        if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", pages):
            raise ValueError("Invalid page range")
        for part in pages.split(","):
            ends = [int(value) for value in part.split("-")]
            if max(ends) > 1000000 or ends[-1] < ends[0]:
                raise ValueError("Invalid page range")
    files = request.get("files")
    if not isinstance(files, list) or not files or any(not isinstance(item, str) for item in files):
        raise ValueError("No input files")
    output = Path(request.get("output", ""))
    if not request.get("output") or not output.is_absolute():
        raise ValueError("Output folder must be an absolute path")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    runtime = configure()
    if args.check:
        import socket
        try:
            socket.create_connection(("192.0.2.1", 443), timeout=1)
        except PermissionError:
            emit("check", message="Models present; external sockets blocked", output=str(ROOT))
            return 0
        raise RuntimeError("Offline policy check failed")
    request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
    output = validate(request)
    output.mkdir(parents=True, exist_ok=True)
    atexit.register(cleanup_children)
    from marker.config.parser import ConfigParser
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import save_output

    models = create_model_dict()
    errors = 0
    total = len(request["files"])
    for index, filename in enumerate(request["files"]):
        emit("file_started", file=filename, done=index, total=total)
        try:
            source = Path(filename)
            if not source.is_file() or source.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
                raise ValueError("Input must be an existing PDF or supported image")
            # A unique run directory keeps earlier results and duplicate names intact.
            target = output / f"{source.stem[:80]}-{uuid.uuid4().hex[:8]}"
            target.mkdir()
            options = {
                "output_format": request["format"], "mode": request["mode"], "use_llm": False,
                "force_ocr": request.get("force_ocr", False), "disable_ocr": request.get("disable_ocr", False),
                "strip_existing_ocr": request.get("strip_existing_ocr", False), "pdftext_workers": 1,
                "keep_pageheader_in_output": request.get("keep_headers", False),
                "keep_pagefooter_in_output": request.get("keep_headers", False),
                "debug": request.get("debug", False), "output_dir": str(target),
                "page_range": request.get("page_range") or None,
            }
            config = ConfigParser(options)
            converter = PdfConverter(config=config.generate_config_dict(), artifact_dict=models,
                                     processor_list=config.get_processors(), renderer=config.get_renderer())
            rendered = converter(str(source))
            save_output(rendered, str(target), source.stem[:80])
            emit("file_done", file=filename, output=str(target), done=index + 1, total=total)
        except Exception as error:
            errors += 1
            traceback.print_exc(file=sys.stderr)
            emit("file_error", file=filename, message=str(error), done=index + 1, total=total)
    emit("complete", done=total, total=total, message=str(errors))
    return 2 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        emit("error", message=str(error))
        sys.exit(1)
