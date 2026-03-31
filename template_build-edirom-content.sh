#!/bin/bash
# Build Edirom content locally using Dockerfile.dev

set -e

# Script is in project root, so PROJECT_ROOT is the directory of this script
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Überprüfe, dass wir im richtigen Verzeichnis sind
if [ ! -f "$PROJECT_ROOT/frbr-tree.xml" ]; then
    echo "ERROR: frbr-tree.xml not found in $PROJECT_ROOT"
    exit 1
fi

cd "$PROJECT_ROOT"

echo "Building Edirom content using Dockerfile.dev..."
echo "Project root: $PROJECT_ROOT"
echo ""

# Build the image
docker build \
  -f build-ewkwa-content/build-edirom/Dockerfile.dev \
  -t edirom-content-builder:local \
  .

# Prepare output directory - just delete and recreate
rm -rf build-xar 2>/dev/null || true
mkdir -p build-xar

# Run container with volume mount to copy xar files directly to build-xar
echo "Running build process and copying output..."
docker run --rm \
  -v "$PROJECT_ROOT/build-xar:/output" \
  edirom-content-builder:local

# Copy Edirom_generated directory from image to host for debugging
#CONTAINER_ID=$(docker create edirom-content-builder:local)
#docker cp "$CONTAINER_ID:/output/Edirom_generated" "$PROJECT_ROOT/build-xar/" 2>/dev/null || true
#docker rm "$CONTAINER_ID" > /dev/null 2>&1

echo ""
echo "Build completed successfully!"
ls -lh build-xar/