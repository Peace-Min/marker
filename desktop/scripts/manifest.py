"""Generate/verify a SHA-256 inventory without machine-specific paths."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = root / "bundle-manifest.json"
    if args.verify:
        files = json.loads(manifest.read_text(encoding="utf-8"))["files"]
        for item in files:
            path = (root / item["path"]).resolve()
            if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size != item["size"] or digest(path) != item["sha256"]:
                raise ValueError(f"Bundle integrity check failed: {item['path']}")
        print(f"Verified {len(files)} bundled files")
    else:
        files = [{"path": str(path.relative_to(root)).replace("\\", "/"), "size": path.stat().st_size, "sha256": digest(path)}
                 for path in sorted(root.rglob("*")) if path.is_file() and path != manifest and "__pycache__" not in path.parts]
        manifest.write_text(json.dumps({"version": "0.1.0", "files": files}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Manifest: {len(files)} files, {sum(item['size'] for item in files):,} bytes")


if __name__ == "__main__":
    main()
