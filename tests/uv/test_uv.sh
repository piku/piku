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
    ((PASSED++)) || true
}

fail() {
    echo -e "${RED}FAIL${NC}: $1"
    ((FAILED++)) || true
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
section "Test 2: Virtualenv Structure"
# ============================================
# Verify the virtualenv has the expected structure

if [ -x "$ENV_DIR/bin/python" ]; then
    pass "Python executable exists and is executable"
else
    fail "Python executable missing or not executable"
fi

# Note: uv doesn't install pip by default (it manages packages directly)
if [ -x "$ENV_DIR/bin/pip" ]; then
    pass "pip executable exists (optional for uv)"
else
    pass "No pip (expected for uv - it manages packages directly)"
fi

if [ -d "$ENV_DIR/lib" ]; then
    pass "lib directory exists"
else
    fail "lib directory missing"
fi

# Check Python is from the virtualenv, not system
python_path=$("$ENV_DIR/bin/python" -c "import sys; print(sys.executable)")
if echo "$python_path" | grep -q "$ENV_DIR"; then
    pass "Python executable is from virtualenv: $python_path"
else
    fail "Python is not from virtualenv: $python_path"
fi

# ============================================
section "Test 3: Dependencies Actually Work"
# ============================================
# Test that Flask can actually be used, not just imported

test_output=$("$ENV_DIR/bin/python" -c "
from flask import Flask
app = Flask(__name__)
@app.route('/')
def hello():
    return 'test'
# Verify app was created correctly
assert app.name == 'testapp' or app.name == '__main__'
print('Flask app created successfully')
" 2>&1) || true

if echo "$test_output" | grep -q "Flask app created successfully"; then
    pass "Flask app can be instantiated"
else
    fail "Flask app creation failed: $test_output"
fi

# Test Flask version is recent (use importlib.metadata to avoid deprecation warning)
flask_version=$("$ENV_DIR/bin/python" -c "from importlib.metadata import version; print(version('flask'))" 2>&1)
if [[ "$flask_version" =~ ^[23]\. ]]; then
    pass "Flask version is 2.x or 3.x: $flask_version"
else
    fail "Unexpected Flask version: $flask_version"
fi

# ============================================
section "Test 4: Python Version via ENV"
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

# Verify it's actually 3.11, not just in the string
py_minor=$("$ENV_DIR/bin/python" -c "import sys; print(sys.version_info.minor)")
if [ "$py_minor" = "11" ]; then
    pass "Python minor version confirmed: 3.$py_minor"
else
    fail "Python minor version mismatch: expected 11, got $py_minor"
fi

# ============================================
section "Test 5: Python Version via .python-version file"
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
section "Test 6: ENV takes priority over .python-version"
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
section "Test 7: Dependency Change Detection - Skip When Unchanged"
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

# ============================================
section "Test 8: Dependency Change Detection - Sync When Changed"
# ============================================
# Modify pyproject.toml to add requests
sleep 1
cat > "$APP_DIR/pyproject.toml" << 'EOF'
[project]
name = "testapp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.0",
    "requests>=2.0",
]
EOF

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

if echo "$output" | grep -q "Running uv sync"; then
    pass "Ran uv sync after pyproject.toml changed"
else
    fail "Did not run uv sync after changes"
    echo "$output"
fi

# Verify requests was actually installed
if "$ENV_DIR/bin/python" -c "import requests; print(requests.__version__)" 2>/dev/null; then
    requests_version=$("$ENV_DIR/bin/python" -c "import requests; print(requests.__version__)")
    pass "New dependency 'requests' installed: $requests_version"
else
    fail "New dependency 'requests' not installed"
fi

# ============================================
section "Test 9: Multiple Dependencies"
# ============================================
cleanup
cat > "$APP_DIR/pyproject.toml" << 'EOF'
[project]
name = "testapp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.0",
    "requests>=2.0",
    "click>=8.0",
]
EOF
echo "web: python -c 'print(1)'" > "$APP_DIR/Procfile"

python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true

# Check all dependencies
for pkg in flask requests click; do
    if "$ENV_DIR/bin/python" -c "import $pkg" 2>/dev/null; then
        pass "Dependency '$pkg' installed"
    else
        fail "Dependency '$pkg' not installed"
    fi
done

# ============================================
section "Test 10: uWSGI Virtualenv Detection"
# ============================================
# This test checks that pyvenv.cfg is detected for uWSGI config
cleanup
create_test_app
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true

if [ -f "$ENV_DIR/pyvenv.cfg" ]; then
    pass "pyvenv.cfg exists for uWSGI detection"
else
    fail "pyvenv.cfg missing - uWSGI won't detect virtualenv"
fi

# Verify pyvenv.cfg has expected content
if grep -q "home" "$ENV_DIR/pyvenv.cfg"; then
    pass "pyvenv.cfg has 'home' directive"
else
    fail "pyvenv.cfg missing 'home' directive"
fi

# Verify it's NOT using activate_this.py (which uv doesn't create)
if [ ! -f "$ENV_DIR/bin/activate_this.py" ]; then
    pass "Correctly handling uv venv (no activate_this.py)"
else
    pass "activate_this.py exists (unusual for uv but ok)"
fi

# ============================================
section "Test 11: Virtualenv Directory Creation"
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

if echo "$output" | grep -q "Creating virtualenv directory"; then
    pass "Directory creation message shown"
else
    fail "Directory creation message not shown"
fi

# ============================================
section "Test 12: Redeploy With Different Python Version"
# ============================================
cleanup
create_test_app
echo "3.11" > "$APP_DIR/.python-version"

# First deploy with 3.11
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true
py_version_1=$("$ENV_DIR/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if [ "$py_version_1" = "3.11" ]; then
    pass "Initial deploy with Python 3.11"
else
    fail "Initial deploy version mismatch: $py_version_1"
fi

# Change to 3.12 and redeploy
rm -rf "$ENV_DIR"  # Need to remove old venv for Python version change
echo "3.12" > "$APP_DIR/.python-version"
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true
py_version_2=$("$ENV_DIR/bin/python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

if [ "$py_version_2" = "3.12" ]; then
    pass "Redeploy with Python 3.12"
else
    fail "Redeploy version mismatch: expected 3.12, got $py_version_2"
fi

# ============================================
section "Test 13: Virtualenv Isolation"
# ============================================
cleanup
create_test_app
python3 $PIKU_SCRIPT deploy testapp >/dev/null 2>&1 || true

# Verify site-packages is isolated
site_packages=$("$ENV_DIR/bin/python" -c "import site; print(site.getsitepackages()[0])")
if echo "$site_packages" | grep -q "$ENV_DIR"; then
    pass "site-packages is in virtualenv: $site_packages"
else
    fail "site-packages not in virtualenv: $site_packages"
fi

# Verify sys.prefix points to virtualenv
sys_prefix=$("$ENV_DIR/bin/python" -c "import sys; print(sys.prefix)")
if echo "$sys_prefix" | grep -q "$ENV_DIR"; then
    pass "sys.prefix is virtualenv: $sys_prefix"
else
    fail "sys.prefix not in virtualenv: $sys_prefix"
fi

# ============================================
section "Test 14: No Python Version Specified (Default)"
# ============================================
cleanup
create_test_app
# No .python-version, no PYTHON_VERSION in ENV

output=$(python3 $PIKU_SCRIPT deploy testapp 2>&1) || true

# Should NOT show "Using Python version" message
if echo "$output" | grep -q "Using Python version"; then
    fail "Should not show version message when none specified"
    echo "$output"
else
    pass "No version message when using default Python"
fi

# Should still create working virtualenv
if "$ENV_DIR/bin/python" -c "import flask" 2>/dev/null; then
    pass "Default Python deployment works"
else
    fail "Default Python deployment failed"
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
