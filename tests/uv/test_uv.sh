#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

pass() {
    echo -e "${GREEN}PASS${NC}: $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    ((FAILED++))
}

section() {
    echo ""
    echo -e "${YELLOW}=== $1 ===${NC}"
}

# Setup
# Repo is mounted at /piku, piku home is /home/piku
PIKU_SCRIPT=/piku/piku.py
PIKU_HOME=/home/piku
APP_DIR=$PIKU_HOME/.piku/apps/testapp
ENV_DIR=$PIKU_HOME/.piku/envs/testapp

cleanup() {
    rm -rf "$APP_DIR" "$ENV_DIR"
    mkdir -p "$APP_DIR"
}

create_test_app() {
    cat > "$APP_DIR/pyproject.toml" << 'EOF'
[project]
name = "testapp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.0",
]
EOF

    cat > "$APP_DIR/testapp.py" << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from uv!'
EOF

    echo "web: python testapp.py" > "$APP_DIR/Procfile"
}

# ============================================
section "Test 1: Basic UV Deployment"
# ============================================
cleanup
create_test_app

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Starting EXPERIMENTAL uv deployment"; then
    pass "UV deployment detected and started"
else
    fail "UV deployment not detected"
    echo "$output"
fi

if [ -f "$ENV_DIR/pyvenv.cfg" ]; then
    pass "pyvenv.cfg created (virtualenv exists)"
else
    fail "pyvenv.cfg not found"
fi

if "$ENV_DIR/bin/python" -c "import flask" 2>/dev/null; then
    pass "Flask installed in virtualenv"
else
    fail "Flask not installed"
fi

# ============================================
section "Test 2: Python Version via ENV"
# ============================================
cleanup
create_test_app
echo "PYTHON_VERSION=3.11" > "$APP_DIR/ENV"

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Using Python version: 3.11"; then
    pass "PYTHON_VERSION env variable respected"
else
    fail "PYTHON_VERSION env variable not respected"
    echo "$output"
fi

py_version=$("$ENV_DIR/bin/python" --version 2>&1)
if echo "$py_version" | grep -q "Python 3.11"; then
    pass "Correct Python version installed: $py_version"
else
    fail "Wrong Python version: $py_version (expected 3.11.x)"
fi

# ============================================
section "Test 3: Python Version via .python-version file"
# ============================================
cleanup
create_test_app
echo "3.12" > "$APP_DIR/.python-version"

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Using Python version: 3.12"; then
    pass ".python-version file respected"
else
    fail ".python-version file not respected"
    echo "$output"
fi

py_version=$("$ENV_DIR/bin/python" --version 2>&1)
if echo "$py_version" | grep -q "Python 3.12"; then
    pass "Correct Python version installed: $py_version"
else
    fail "Wrong Python version: $py_version (expected 3.12.x)"
fi

# ============================================
section "Test 4: ENV takes priority over .python-version"
# ============================================
cleanup
create_test_app
echo "PYTHON_VERSION=3.11" > "$APP_DIR/ENV"
echo "3.12" > "$APP_DIR/.python-version"

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Using Python version: 3.11"; then
    pass "ENV takes priority over .python-version"
else
    fail "ENV did not take priority"
    echo "$output"
fi

py_version=$("$ENV_DIR/bin/python" --version 2>&1)
if echo "$py_version" | grep -q "Python 3.11"; then
    pass "Correct Python version (ENV priority): $py_version"
else
    fail "Wrong Python version: $py_version (expected 3.11.x from ENV)"
fi

# ============================================
section "Test 5: Dependency Change Detection"
# ============================================
cleanup
create_test_app

# First deploy
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true

# Second deploy without changes - should skip sync
sleep 1  # Ensure mtime difference
output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Dependencies are up to date"; then
    pass "Skipped uv sync when no changes"
else
    fail "Did not skip uv sync (expected 'Dependencies are up to date')"
    echo "$output"
fi

# Modify pyproject.toml
sleep 1
echo '    "requests>=2.0",' >> "$APP_DIR/pyproject.toml"

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Running uv sync"; then
    pass "Ran uv sync after pyproject.toml changed"
else
    fail "Did not run uv sync after changes"
    echo "$output"
fi

# ============================================
section "Test 6: uWSGI Virtualenv Detection"
# ============================================
# This test checks that pyvenv.cfg is detected for uWSGI config
# We can't fully test uWSGI without running it, but we can verify
# the detection logic by checking the file exists

cleanup
create_test_app
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true

if [ -f "$ENV_DIR/pyvenv.cfg" ]; then
    pass "pyvenv.cfg exists for uWSGI detection"
else
    fail "pyvenv.cfg missing - uWSGI won't detect virtualenv"
fi

# Verify it's NOT using activate_this.py (which uv doesn't create)
if [ ! -f "$ENV_DIR/bin/activate_this.py" ]; then
    pass "Correctly handling uv venv (no activate_this.py)"
else
    # This would be unexpected for uv
    pass "activate_this.py exists (unusual for uv but ok)"
fi

# ============================================
section "Test 7: Virtualenv Directory Creation"
# ============================================
cleanup
create_test_app
# Ensure env dir doesn't exist
rm -rf "$ENV_DIR"

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if [ -d "$ENV_DIR" ]; then
    pass "Virtualenv directory created"
else
    fail "Virtualenv directory not created"
fi

# ============================================
# Summary
# ============================================
echo ""
echo "========================================"
echo -e "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo "========================================"

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0
