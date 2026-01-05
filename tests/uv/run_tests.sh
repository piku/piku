#!/bin/bash
# Run UV deployment tests locally in Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIKU_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse args
NO_CACHE=""
if [[ "$1" == "--no-cache" ]] || [[ "$1" == "-f" ]]; then
    NO_CACHE="--no-cache"
    echo "Forcing full rebuild..."
fi

echo "Building test container..."
docker build $NO_CACHE -t piku-uv-test "$SCRIPT_DIR"

echo ""
echo "Running tests..."
echo "(tests mounted from: $PIKU_ROOT/tests/uv/)"
echo ""
docker run --rm -v "$PIKU_ROOT":/piku piku-uv-test
