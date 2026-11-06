"""Exclude wheel test suites and C/C++ headers from an inference-only bundle."""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("python_root", type=Path)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
root = args.python_root.resolve(strict=True)
if root.name != "python" or root.parent.name != "engine":
    raise ValueError("Only an explicitly named engine/python runtime can be pruned")
candidates = sorted((path for path in root.rglob("*") if path.is_dir() and path.name in {"tests", "test", "include", "__pycache__"}), key=lambda path: len(path.parts))
selected = []
for path in candidates:
    resolved = path.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Refusing path outside runtime: {resolved}")
    if not any(path.is_relative_to(parent) for parent in selected):
        selected.append(path)
print("Verified runtime root:", root)
print("Development/cache directories:", len(selected))
for path in selected[:8]:
    print(path)
if args.apply:
    for path in selected:
        shutil.rmtree(path)
    print("Removed optional development/cache directories")
