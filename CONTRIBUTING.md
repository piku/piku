# Contributing

`piku` is a stable project, but we welcome contributions that:

* Help us move beyond Python 3.8+ (which is the current target due to Linux LTS distribution alignment)
* Help us do better automated testing
* Improve documentation (some docs are a bit old by now)
* Help us deploy `piku` in various Linux distributions and environments (check the sister repositories in the project)
* Provide sample deployments of common applications (again, check the sister repositories in the project)
* Allow us to better support more language runtimes
* Allow us to support different web servers or process supervisors (Caddy springs to mind as a popular alternative for small VPSes)

## Code Size / Style

By its very nature, `piku` is a very small program. By today's standards of all-encompassing solutions this may seem strange, but it would benefit from being kept that way.

- Small and focused PRs. Please don't include changes that don't address the subject of your PR.
- Follow the style of importing functions directly e.g. `from os.path import abspath`
- Follow `PEP8`.

So please keep that in mind when contributing.

For instance, if your runtime or framework needs additional setup, it might be better to contribute an utility script to run in a `release` entry in the `Procfile` rather than patching `piku.py`--but do hack at it if that is the best way to achieve it.
