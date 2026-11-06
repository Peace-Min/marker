#!/usr/bin/env bash
set -euo pipefail
desktop=$(cd -- "$(dirname -- "$0")/.." && pwd)
stage="${MARKER_LINUX_STAGE:-$desktop/artifacts/linux-x64}"
release="$desktop/artifacts/release"
mkdir -p "$release"
python="$stage/engine/python/bin/python3"
tar -C "$desktop/artifacts/linux-x64" --exclude='./engine' -cf - . | tar -C "$stage" -xf -
cp "$desktop/scripts/install-linux.sh" "$stage/install.sh"
cp "$desktop/scripts/manifest.py" "$stage/verify-bundle.py"
chmod +x "$stage/install.sh" "$stage/Marker.Desktop"
cp -a "$desktop/artifacts/win-x64/engine/licenses/." "$stage/engine/licenses/"
"$python" - "$stage/engine" <<'PY'
import importlib.metadata
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
items = [{"name": dist.metadata["Name"], "version": dist.version,
          "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", "See package metadata"),
          "metadata": str(Path(dist._path).relative_to(root))}
         for dist in importlib.metadata.distributions()]
(root / "licenses/packages.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
PY
"$python" "$desktop/scripts/build_wiki.py" "$stage/Wiki"
"$python" "$desktop/scripts/manifest.py" "$stage"
archive="${MARKER_LINUX_BUILD:-$desktop/.build/linux}/release.tar.gz"
mkdir -p "$(dirname -- "$archive")"
tar -C "$stage" --exclude='__pycache__' -cf - . | gzip -1 > "$archive"
installer="$release/MarkerDesktop-0.1.0-linux-x64.run"
cat > "$installer" <<'HEADER'
#!/usr/bin/env bash
set -euo pipefail
task_tmp=$(mktemp -d "${TMPDIR:-/tmp}/marker-installer.XXXXXXXX")
trap 'rm -rf -- "$task_tmp"' EXIT
archive_line=$(awk '/^__MARKER_ARCHIVE_BELOW__$/ {print NR + 1; exit}' "$0")
tail -n +"$archive_line" "$0" | tar -xz -C "$task_tmp"
bash "$task_tmp/install.sh"
exit 0
__MARKER_ARCHIVE_BELOW__
HEADER
cat "$archive" >> "$installer"
chmod +x "$installer"
(cd "$release" && sha256sum "$(basename -- "$installer")" > "$(basename -- "$installer").sha256")
printf 'Offline Linux installer: %s\n' "$installer"
