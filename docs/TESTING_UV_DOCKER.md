# Testing UV Support in Docker

This document explains how to test the piku `uv` deployment functionality locally using Docker.

## Quick Start (Automated)

Run the automated test suite:

```bash
./tests/uv/run_tests.sh
```

This builds a Docker container and runs all uv deployment tests automatically.

The same tests run in CI via `.github/workflows/uv-tests.yml`.

## Test Structure

```
.github/workflows/
├── uv-test/
│   └── Dockerfile      # Test container with uv + Python 3.11/3.12
└── uv-tests.yml        # CI workflow

tests/uv/
├── run_tests.sh        # Local test runner
└── test_uv.sh          # Test cases
```

## Prerequisites

- Docker installed and running

## Manual Testing

### 1. Build the Test Container

```bash
docker build .github/workflows/uv-test -t local/uv-test
```

### 2. Run the Tests

```bash
docker run -v "$PWD":/run local/uv-test
```

### 3. Interactive Mode

To debug or run tests manually:

```bash
docker run -it -v "$PWD":/run local/uv-test /bin/bash
# Then inside the container:
/run/tests/uv/test_uv.sh
```

## Test Cases

### Test Case 1: Basic UV Deployment

Create a minimal Python app with `pyproject.toml`:

```bash
# Inside the container
mkdir -p ~/.piku/apps/testapp
cd ~/.piku/apps/testapp

cat > pyproject.toml << 'EOF'
[project]
name = "testapp"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.0",
]

[project.scripts]
testapp = "testapp:main"
EOF

cat > testapp.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from uv!'

def main():
    app.run()
EOF

# Create Procfile
echo "web: python testapp.py" > Procfile
```

Run the deployment test:

```bash
cd /home/piku
python3 piku.py deploy testapp
```

**Expected Output:**
```
=====> Starting uv deployment for 'testapp'
-----> Creating virtualenv directory for 'testapp'
-----> Running uv sync for 'testapp'
```

**Verify:**
```bash
# Check virtualenv was created with pyvenv.cfg
ls -la ~/.piku/envs/testapp/
cat ~/.piku/envs/testapp/pyvenv.cfg

# Check Flask was installed
~/.piku/envs/testapp/bin/python -c "import flask; print(flask.__version__)"
```

### Test Case 2: Python Version Selection

Test that `PYTHON_VERSION` environment variable works:

```bash
# Create ENV file with specific Python version
mkdir -p ~/.piku/apps/testapp
echo "PYTHON_VERSION=3.11" > ~/.piku/apps/testapp/ENV

# Re-run deployment
rm -rf ~/.piku/envs/testapp
python3 piku.py deploy testapp
```

**Expected Output:**
```
=====> Starting uv deployment for 'testapp'
-----> Creating virtualenv directory for 'testapp'
-----> Using Python version: 3.11
-----> Running uv sync for 'testapp'
```

**Verify:**
```bash
~/.piku/envs/testapp/bin/python --version
# Should show Python 3.11.x
```

### Test Case 3: .python-version File Support

Test that `.python-version` file works (standard uv/pyenv convention):

```bash
# Remove any ENV override first
rm -f ~/.piku/apps/testapp/ENV

# Create .python-version file
echo "3.11" > ~/.piku/apps/testapp/.python-version

# Re-run deployment
rm -rf ~/.piku/envs/testapp
python3 piku.py deploy testapp
```

**Expected Output:**
```
=====> Starting uv deployment for 'testapp'
-----> Creating virtualenv directory for 'testapp'
-----> Using Python version: 3.11
-----> Running uv sync for 'testapp'
```

**Test Priority (ENV overrides .python-version):**
```bash
# Set both ENV and .python-version
echo "PYTHON_VERSION=3.12" > ~/.piku/apps/testapp/ENV
echo "3.10" > ~/.piku/apps/testapp/.python-version

rm -rf ~/.piku/envs/testapp
python3 piku.py deploy testapp
```

**Expected Output:**
```
-----> Using Python version: 3.12
```
(ENV variable takes precedence over .python-version file)

### Test Case 4: Dependency Change Detection

Test that piku only re-syncs when `pyproject.toml` changes:

```bash
# First deployment
python3 piku.py deploy testapp

# Second deployment without changes
python3 piku.py deploy testapp
```

**Expected Output (second run):**
```
=====> Starting uv deployment for 'testapp'
-----> Dependencies are up to date for 'testapp'
```

Now modify `pyproject.toml`:

```bash
# Add a new dependency
cd ~/.piku/apps/testapp
cat >> pyproject.toml << 'EOF'
    "requests>=2.0",
EOF

# Re-deploy
cd /home/piku
python3 piku.py deploy testapp
```

**Expected Output:**
```
=====> Starting uv deployment for 'testapp'
-----> Running uv sync for 'testapp'
```

### Test Case 5: uWSGI Virtualenv Detection

Test that uWSGI correctly detects the uv-created virtualenv:

```bash
# Check that pyvenv.cfg exists (used for uWSGI detection)
ls ~/.piku/envs/testapp/pyvenv.cfg

# The spawn_worker function should now detect this as a valid virtualenv
# and add the 'virtualenv' setting to uWSGI config
```

## Testing with Multiple Python Versions

To test Python version switching, you can install multiple Python versions in the container:

```bash
# In the Dockerfile, add:
RUN uv python install 3.10 3.11 3.12

# Then test each version:
echo "PYTHON_VERSION=3.10" > ~/.piku/apps/testapp/ENV
rm -rf ~/.piku/envs/testapp
python3 piku.py deploy testapp
~/.piku/envs/testapp/bin/python --version  # Should be 3.10

echo "PYTHON_VERSION=3.12" > ~/.piku/apps/testapp/ENV
rm -rf ~/.piku/envs/testapp
python3 piku.py deploy testapp
~/.piku/envs/testapp/bin/python --version  # Should be 3.12
```

## Troubleshooting

### UV Not Found

If you see "uv: command not found":

```bash
# Check if uv is installed
which uv

# If not, install it
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

### Python Version Not Available

If uv can't find the requested Python version:

```bash
# List available Python versions
uv python list

# Install a specific version
uv python install 3.12
```

### Virtualenv Not Detected by uWSGI

Check that `pyvenv.cfg` exists in the virtualenv:

```bash
ls ~/.piku/envs/YOUR_APP/pyvenv.cfg
```

If missing, the virtualenv may not have been created properly. Check the uv sync output for errors.

## Comparing with Poetry Deployment

To verify uv works similarly to poetry:

```bash
# Install poetry
pip install poetry

# Deploy same app with poetry (requires poetry.lock)
cd ~/.piku/apps/testapp
poetry init  # or copy an existing pyproject.toml
python3 /home/piku/piku.py deploy testapp
```

## CI Integration

To add this to GitHub Actions, update `.github/workflows/core-tests.yml`:

```yaml
  uv-test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Install uv
      run: curl -LsSf https://astral.sh/uv/install.sh | sh
    - name: Test uv deployment
      run: |
        export PATH="$HOME/.local/bin:$PATH"
        # Create test app and run deployment tests
        mkdir -p ~/.piku/apps/testapp
        # ... (add test commands)
```
