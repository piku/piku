#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIKU_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building test container..."
docker build -t piku-uv-test -f "$SCRIPT_DIR/Dockerfile" "$PIKU_ROOT"

echo ""
echo "Running tests..."
docker run --rm piku-uv-test
