# Testing UV Support in Docker

## Quick Start

```bash
./tests/uv/run_tests.sh
```

Options:
- `--no-cache` or `-f`: Force full Docker rebuild

## Test Structure

```
tests/uv/
├── Dockerfile      # Debian + uv + Python 3.11/3.12
├── run_tests.sh    # Build and run container
└── test_uv.sh      # Test cases (15 tests)
```

## Interactive Debugging

```bash
docker build -t piku-uv-test tests/uv/
docker run -it --rm -v "$PWD":/piku piku-uv-test /bin/bash

# Inside container:
/piku/tests/uv/test_uv.sh
```

## What's Tested

1. Basic UV deployment
2. Virtualenv structure (python, lib/)
3. Dependencies work (Flask instantiation)
4. `PYTHON_VERSION` env variable
5. `.python-version` file support
6. ENV priority over .python-version
7. Skip sync when unchanged
8. Sync when pyproject.toml changes
9. Multiple dependencies
10. uWSGI detection (pyvenv.cfg)
11. Virtualenv directory creation
12. Redeploy with different Python version
13. Virtualenv isolation
14. Default Python (no version specified)
15. Lockfile (uv.lock) change detection
