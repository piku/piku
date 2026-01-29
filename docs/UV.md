# UV Support (Experimental)

Piku has experimental support for [uv](https://github.com/astral-sh/uv), a fast Python package installer and resolver written in Rust. When piku detects a `pyproject.toml` file in your app (without a `requirements.txt`), it will use `uv` for dependency management.

## Prerequisites

Install `uv` for the piku user:

```bash
sudo -u piku -i
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Optionally, pre-install Python versions:

```bash
sudo -u piku -i
~/.local/bin/uv python install 3.10 3.11 3.12
```

## How It Works

When you push an app with `pyproject.toml`:

1. Piku detects `pyproject.toml` and activates UV mode
2. Creates a virtualenv in `~/.piku/envs/<app>`
3. Runs `uv sync` to install dependencies
4. Dependencies are only reinstalled when `pyproject.toml` or `uv.lock` changes

## Python Version Selection

You can specify which Python version to use in three ways (in priority order):

### 1. ENV file (highest priority)

```bash
# In your app's ENV file
PYTHON_VERSION=3.10
```

### 2. `.python-version` file

```bash
# .python-version in your app root
3.11
```

### 3. Default

If no version is specified, uv will use its default Python resolution.

## Important Limitation: uWSGI Compatibility

**When using system-installed uWSGI, the virtualenv Python version must match the system Python.**

### Why?

uWSGI installed from system packages (apt, yum) is compiled against a specific Python version. Even though uv can create virtualenvs with any Python version, uWSGI will use its compiled-in interpreter. This causes a mismatch:

- uv creates virtualenv with Python 3.12
- uWSGI loads the virtualenv but uses Python 3.10 (system)
- Packages installed for 3.12 are invisible to uWSGI's 3.10 interpreter
- Result: `ModuleNotFoundError`

### Solution

**Always set `PYTHON_VERSION` in your ENV file to match your system Python:**

```bash
# Check your system Python version
python3 --version  # e.g., Python 3.10.12

# In your app's ENV file
PYTHON_VERSION=3.10
```

Common system Python versions:
- Ubuntu 22.04: Python 3.10
- Ubuntu 24.04: Python 3.12
- Debian 12: Python 3.11

### Alternative: Use Gunicorn

If you need a different Python version, you can use gunicorn instead of uWSGI. Gunicorn runs inside the virtualenv and uses the virtualenv's Python:

```python
# Procfile
web: gunicorn wsgi:application --bind 127.0.0.1:$PORT
```

```toml
# pyproject.toml
[project]
dependencies = [
    "flask>=2.0",
    "gunicorn>=21.0",
]
```

## Example App

### pyproject.toml

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "flask>=2.0",
    "requests>=2.0",
]
```

### ENV

```bash
PYTHON_VERSION=3.10
```

### wsgi.py

```python
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello from UV!'

application = app
```

### Procfile

```bash
wsgi: wsgi:application
```

## Dependency Updates

Piku tracks changes to `pyproject.toml` and `uv.lock`. When either file changes:

1. `uv sync` runs to update dependencies
2. The app is restarted with the new dependencies

If neither file changes, dependencies are not reinstalled (faster deploys).

## UV Configuration

UV respects its standard configuration. You can set options via environment variables in your ENV file:

```bash
# Allow UV to download Python versions not on the system
UV_PYTHON_PREFERENCE=managed

# Use only system-installed Python versions
UV_PYTHON_PREFERENCE=only-system
```

By default, piku sets `UV_PYTHON_PREFERENCE=managed` to allow UV to download Python versions if needed.

## Troubleshooting

### "ModuleNotFoundError" in uWSGI logs

Check that your `PYTHON_VERSION` matches the system Python:

```bash
# On your piku server
python3 --version
```

Then set `PYTHON_VERSION` in your app's ENV file to match.

### "No interpreter found for Python X.Y"

UV can't find the requested Python version. Either:

1. Install it: `uv python install 3.X`
2. Change `PYTHON_VERSION` to an available version
3. Ensure `UV_PYTHON_PREFERENCE=managed` is set (allows UV to download)

### Dependencies not updating

Make sure you're modifying `pyproject.toml` or `uv.lock`. Piku only runs `uv sync` when these files change.

## Testing

Run the UV test suite:

```bash
./tests/uv/run_tests.sh
```

See [TESTING_UV_DOCKER.md](TESTING_UV_DOCKER.md) for more details.
