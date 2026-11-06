"""Assemble a relocatable runtime from the verified local installation."""
import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys

DESKTOP = Path(__file__).resolve().parents[1]
REPO = DESKTOP.parent


def patch_surya(packages):
    path = packages / "surya/inference/backends/spawn.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_stop_process")
    lines = source.splitlines(keepends=True)
    lines[function.lineno - 1:function.end_lineno] = ['''def _stop_process(pid: int, name: str) -> None:
    # Marker Desktop modification: Windows-safe process-tree cleanup.
    import psutil
    try:
        parent = psutil.Process(pid)
        processes = list(reversed(parent.children(recursive=True))) + [parent]
        for process in processes:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        _, alive = psutil.wait_procs(processes, timeout=5)
        for process in alive:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass
    except psutil.NoSuchProcess:
        pass
''']
    source = "".join(lines)
    source = source.replace('base = Path(os.path.expanduser("~/.cache/datalab/surya"))',
                            'base = Path(os.environ.get("MARKER_RUNTIME_DIR", os.path.expanduser("~/.cache/datalab/surya")))')
    path.write_text(source, encoding="utf-8")
    path = packages / "surya/inference/backends/llamacpp.py"
    source = path.read_text(encoding="utf-8").replace(
        'Path("~/.cache/datalab/surya/llamacpp_server.log").expanduser()',
        'Path(os.environ.get("MARKER_RUNTIME_DIR", os.path.expanduser("~/.cache/datalab/surya"))) / "llamacpp_server.log"')
    path.write_text(source, encoding="utf-8")
    path = packages / "surya/common/batch_service/client.py"
    source = path.read_text(encoding="utf-8")
    if "import os\n" not in source:
        source = source.replace("import subprocess\n", "import os\nimport subprocess\n")
    source = source.replace('Path(\n            f"~/.cache/datalab/surya/{self.config.backend}_server.log"\n        ).expanduser()',
                            'Path(os.environ.get("MARKER_RUNTIME_DIR", os.path.expanduser("~/.cache/datalab/surya"))) / f"{self.config.backend}_server.log"')
    path.write_text(source, encoding="utf-8")


def copy_models(output):
    hub = Path.home() / ".cache/huggingface/hub"
    from huggingface_hub import snapshot_download, hf_hub_download
    # Pin model revisions; copied files are regular files, not cache symlinks.
    layout = Path(snapshot_download("datalab-to/surya_layout2", revision="0aee81d5fd9275c0582e545bf3a56944b1e75679", local_files_only=True))
    shutil.copytree(layout, output / "models/layout", ignore=shutil.ignore_patterns(".gitattributes"))
    ocr = output / "models/ocr"
    ocr.mkdir(parents=True)
    for name in ("surya-2.gguf", "surya-2-mmproj.gguf"):
        path = hf_hub_download("datalab-to/surya-ocr-2-gguf", name, revision="6a3a4c30e5e74446d4f8b6afd05b2f2da970f470", local_files_only=True)
        shutil.copyfile(path, ocr / name)
    cache = Path(os.environ["LOCALAPPDATA"]) / "datalab/datalab/Cache/models/ocr_error_detection/2025_02_18"
    shutil.copytree(cache, output / "models/ocr-error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Use a fresh output directory: {output}")
    output.mkdir(parents=True)
    print("Copying portable Python and packages", flush=True)
    shutil.copytree(args.python_home, output / "python", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    packages = output / "python/Lib/site-packages"
    shutil.copytree(REPO / ".venv/Lib/site-packages", packages, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_editable*", "_virtualenv*", "tests", "test", "include"))
    shutil.copytree(REPO / "marker", packages / "marker", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(REPO / "static", packages / "static")
    patch_surya(packages)
    for name in ("worker.py", "sitecustomize.py"):
        shutil.copyfile(DESKTOP / "engine" / name, output / name)
    shutil.copyfile(DESKTOP / "engine/sitecustomize.py", packages / "sitecustomize.py")
    shutil.copytree(REPO / "tools/llama.cpp", output / "llama")
    shutil.copytree(REPO / "static/fonts", output / "fonts")
    print("Copying pinned OCR/layout/error models", flush=True)
    copy_models(output)
    licenses = output / "licenses"
    licenses.mkdir()
    for name in ("LICENSE", "MODEL_LICENSE"):
        shutil.copyfile(REPO / name, licenses / f"marker-{name}.txt")
    shutil.copyfile(args.python_home / "LICENSE.txt", licenses / "Python-LICENSE.txt")
    inventory = []
    for dist in importlib.metadata.distributions(path=[str(packages)]):
        inventory.append({"name": dist.metadata["Name"], "version": dist.version,
                          "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", "See package metadata"),
                          "metadata": str(Path(dist._path).relative_to(output)).replace("\\", "/")})
    (licenses / "packages.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    (licenses / "MODIFICATIONS.txt").write_text(
        "Marker Desktop modifications: correct page indices in Marker chunk output; per-run server cache/log paths and Windows-safe process-tree cleanup in Surya; Python external-network refusal in sitecustomize. Original notices are retained.\n",
        encoding="utf-8")
    print("Engine staged", output, flush=True)


if __name__ == "__main__":
    main()
