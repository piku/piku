# Piku

The tiniest PaaS you've ever seen. `git push` deployments to your own servers.

## Philosophy

Piku is intentionally minimal. Every design decision prioritizes:

1. **Simplicity over features** — one file, one user, one server
2. **Readability over abstraction** — a new contributor should understand the entire system in an afternoon
3. **Unix philosophy** — compose existing tools (git, nginx, uwsgi) rather than reimplementing them
4. **ARM-friendly** — must run on a Raspberry Pi with minimal resources
5. **12-factor alignment** — Procfile for processes, ENV for config, git for deployment

Do not add complexity. If a feature requires more than ~50 lines and doesn't benefit the majority of users, it belongs in a plugin or a separate tool.

## Architecture

```
git push → SSH (piku user) → post-receive hook → do_deploy()
    → detect runtime → build (venv/npm/cargo/go build)
    → generate uwsgi config → generate nginx config
    → reload uwsgi → reload nginx
```

Everything lives under `~/.piku/`:
- `apps/` — deployed application working copies
- `repos/` — bare git repositories
- `envs/` — per-app ENV files
- `data/` — persistent app data (never deleted on redeploy)
- `logs/` — per-app log files
- `nginx/` — generated nginx configs
- `uwsgi-available/` / `uwsgi-enabled/` — uwsgi app configs

## Code Style

- **Python 3.8+** (must work on Debian LTS)
- **PEP 8** formatting
- **Direct imports**: `from os.path import abspath, join` (not `import os.path`)
- **No type hints yet** (but welcome as a contribution)
- **Click** for CLI commands
- **No classes** — functions only, flat structure
- Keep `piku.py` as a single file (it's ~1800 lines and that's fine)

## Working with the Code

### Before editing

- Read the function you're changing AND its callers
- The file is organized top-to-bottom: globals → utilities → deploy functions → spawn/stop → CLI commands
- `sanitize_app_name()` is the security boundary for app names — respect it

### Key functions

| Function | Purpose |
|---|---|
| `do_deploy(app, deltas, newrev)` | Main deploy orchestrator |
| `spawn_app(app, deltas)` | Generate uwsgi/nginx configs and start |
| `spawn_worker(app, name, settings)` | Write uwsgi config for one process type |
| `do_stop(app)` | Stop an app's uwsgi processes |
| `multi_tail(app, filenames)` | Stream log files |
| `cmd_git_hook(app)` | Post-receive hook entry point |

### Security considerations

- All app names go through `sanitize_app_name()` — never bypass this
- `shell=True` is used with `call()` — any new subprocess calls should prefer `shell=False` with argument lists
- `newrev` comes from git stdin (hex SHA1) — safe but unvalidated
- nginx configs are templates with string interpolation — be careful with user-controlled values

### Testing

- No unit tests exist in-repo — CI runs full-VM integration tests
- Test your changes manually: create an app, push, verify processes start, verify nginx routes
- If adding a new runtime, add a test app under `examples/` or document how to verify

### What NOT to do

- Don't add features that require a daemon or background process beyond uwsgi
- Don't add database dependencies
- Don't add container/Docker support (that's a different tool)
- Don't break compatibility with existing Procfile/ENV conventions
- Don't add Python dependencies without very strong justification
- Don't refactor the file structure without discussing first
- Don't add async/await (the synchronous model is intentional)

## Deployment Runtimes

Each runtime has a `deploy_*()` function that:
1. Detects the runtime from repo files (e.g., `requirements.txt` → Python)
2. Builds/installs dependencies
3. Returns worker settings for `spawn_app()`

To add a new runtime: write a `deploy_newlang()` function, add detection logic to `do_deploy()`, test manually, submit a focused PR.

## Environment

- **Target OS**: Debian/Ubuntu (including ARM)
- **Python**: 3.8+ (system Python)
- **Process manager**: uwsgi
- **Web server**: nginx
- **SSL**: Let's Encrypt via ACME
- **User**: `piku` system user with SSH access

## Pull Requests

- Small, focused PRs only
- One concern per PR
- Explain the "why" in the PR description
- If touching deploy logic, specify which runtime and how you tested
