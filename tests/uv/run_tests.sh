#!/bin/bash
# Run UV deployment tests locally using Docker
# This matches the CI workflow in .github/workflows/uv-tests.yml

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIKU_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Building test container..."
docker build "$PIKU_ROOT/.github/workflows/uv-test" -t local/uv-test

echo ""
echo "Running tests..."
docker run -v "$PIKU_ROOT":/run local/uv-test
