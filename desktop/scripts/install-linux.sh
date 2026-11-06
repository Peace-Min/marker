#!/usr/bin/env bash
set -euo pipefail
source_dir=$(cd -- "$(dirname -- "$0")" && pwd)
target="${XDG_DATA_HOME:-$HOME/.local/share}/marker-desktop/0.1.0"
if [ -e "$target/Marker.Desktop" ]; then
  echo "Marker Desktop 0.1.0 is already installed at $target" >&2
  exit 1
fi
mkdir -p "$(dirname -- "$target")"
staging=$(mktemp -d "$(dirname -- "$target")/.install-XXXXXXXX")
trap 'if [ -n "${staging:-}" ] && [ -d "$staging" ]; then rm -rf -- "$staging"; fi' EXIT
cp -a "$source_dir/." "$staging/"
"$staging/engine/python/bin/python3" "$staging/verify-bundle.py" "$staging" --verify
mv -T "$staging" "$target"
staging=''
chmod +x "$target/Marker.Desktop" "$target/engine/python/bin/python3" "$target/engine/llama/llama-server"
"$target/engine/python/bin/python3" "$target/engine/worker.py" --check
applications="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$applications"
cat > "$applications/marker-desktop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Marker Desktop Offline
Comment=Offline PDF and image conversion
Exec="$target/Marker.Desktop"
Path=$target
Terminal=false
Categories=Office;Utility;
EOF
printf 'Installed: %s\nLaunch: %s/Marker.Desktop\n' "$target" "$target"
printf 'Uninstall: remove the version folder above and %s/marker-desktop.desktop. Your results are kept separately.\n' "$applications"
