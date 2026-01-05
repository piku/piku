#!/bin/bash
# Run UV deployment tests locally in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIKU_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building test container..."
docker build -t piku-uv-test "$SCRIPT_DIR"

echo ""
echo "Running tests..."
docker run --rm -v "$PIKU_ROOT":/piku piku-uv-test
