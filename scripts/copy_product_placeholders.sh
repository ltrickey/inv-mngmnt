#!/usr/bin/env bash
# Copy an existing product image to all products that don't have an image yet.
# Run from repo root. Requires: jq
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SEED_DATA="$PROJECT_ROOT/server/seed_data/products.json"
IMAGES_DIR="$PROJECT_ROOT/infrastructure/images"
SOURCE_IMAGE="$IMAGES_DIR/0123456789012-organic-whole-milk.jpg"

if [ ! -f "$SOURCE_IMAGE" ]; then
  echo "Error: Source image not found: $SOURCE_IMAGE" >&2
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo "Error: jq is required." >&2
  exit 1
fi

created=0
while IFS= read -r filename; do
  [ -z "$filename" ] && continue
  dest="$IMAGES_DIR/$filename"
  if [ ! -f "$dest" ]; then
    cp "$SOURCE_IMAGE" "$dest"
    echo "  Created $filename"
    created=$((created + 1))
  fi
done < <(jq -r '.[].image_url | split("/") | .[-1]' "$SEED_DATA")

echo "Done. Created $created placeholder image(s)."
