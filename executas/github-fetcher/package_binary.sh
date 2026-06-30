#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

EXECUTA_JSON="executa.json"
ENTRY_FILE="github_fetcher.py"
OUT_DIR="dist-anna"

if [ ! -f "$EXECUTA_JSON" ]; then
  echo "ERROR: $EXECUTA_JSON not found" >&2
  exit 1
fi

if [ ! -f "$ENTRY_FILE" ]; then
  echo "ERROR: $ENTRY_FILE not found" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required. Please install uv first." >&2
  exit 1
fi

TOOL_ID="$(python -c 'import json; print(json.load(open("executa.json", "r", encoding="utf-8"))["tool_id"])')"
VERSION="$(python -c 'import json; print(json.load(open("executa.json", "r", encoding="utf-8")).get("version", "0.0.0"))')"
DISPLAY_NAME="$(python -c 'import json; d=json.load(open("executa.json", "r", encoding="utf-8")); print(d.get("name", d["tool_id"]))')"
DESCRIPTION="$(python -c 'import json; print(json.load(open("executa.json", "r", encoding="utf-8")).get("description", ""))')"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"

case "$OS" in
  msys*|cygwin*|mingw*) OS="windows" ;;
esac

case "$ARCH" in
  x86_64|amd64) ARCH="x86_64" ;;
  arm64|aarch64) ARCH="arm64" ;;
esac

PLATFORM="$OS-$ARCH"

case "$PLATFORM" in
  darwin-arm64|darwin-x86_64|linux-x86_64|windows-x86_64)
    ;;
  *)
    echo "ERROR: unsupported platform: $PLATFORM" >&2
    exit 1
    ;;
esac

echo "Tool ID:  $TOOL_ID"
echo "Version:  $VERSION"
echo "Platform: $PLATFORM"
echo

rm -rf build dist "$OUT_DIR/staging-$PLATFORM"
mkdir -p "$OUT_DIR/staging-$PLATFORM/bin"

echo "==> Building single-file executable with PyInstaller"

uv run --with pyinstaller python -m PyInstaller \
  --onefile \
  --clean \
  --noupx \
  --name "$TOOL_ID" \
  "$ENTRY_FILE"

BINARY="dist/$TOOL_ID"
ENTRYPOINT_BIN="$TOOL_ID"
if [ "$OS" = "windows" ]; then
  BINARY="dist/$TOOL_ID.exe"
  ENTRYPOINT_BIN="$TOOL_ID.exe"
fi

if [ ! -f "$BINARY" ]; then
  echo "ERROR: PyInstaller did not produce $BINARY" >&2
  exit 1
fi

if [ "$(uname -s)" = "Darwin" ]; then
  codesign --force --sign - "$BINARY" 2>/dev/null || true
fi

STAGE="$OUT_DIR/staging-$PLATFORM"
cp "$BINARY" "$STAGE/bin/$ENTRYPOINT_BIN"
chmod 0755 "$STAGE/bin/$ENTRYPOINT_BIN" 2>/dev/null || true

echo "==> Writing archive manifest"

python - "$STAGE/manifest.json" "$TOOL_ID" "$VERSION" "$DISPLAY_NAME" "$DESCRIPTION" "$ENTRYPOINT_BIN" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
tool_id = sys.argv[2]
version = sys.argv[3]
display_name = sys.argv[4]
description = sys.argv[5]
entrypoint_bin = sys.argv[6]

entrypoint = f"bin/{entrypoint_bin}"

manifest = {
    "name": tool_id,
    "display_name": display_name,
    "version": version,
    "description": description,
    "runtime": {
        "binary": {
            "entrypoint": {
                "default": entrypoint
            },
            "permissions": {
                entrypoint: "0o755"
            }
        }
    }
}

manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY

ARCHIVE="$OUT_DIR/$TOOL_ID-$PLATFORM.tar.gz"

echo "==> Creating archive: $ARCHIVE"

(
  cd "$STAGE"
  tar czf "../$TOOL_ID-$PLATFORM.tar.gz" .
)

if command -v shasum >/dev/null 2>&1; then
  SHA256="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
else
  SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
fi

SIZE="$(wc -c < "$ARCHIVE" | tr -d ' ')"

echo
echo "Built archive:"
echo "  $ARCHIVE"
echo "SHA-256:"
echo "  $SHA256"
