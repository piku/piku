# Design Notes

The idea behind `piku` is that it provides the simplest possible way to deploy web apps or services. Simplicity comes at the expense of features, of course, and this document tries to capture the trade-offs.

## Why uWSGI

Using [uWSGI][uwsgi] in [emperor mode][emperor] gives us the following features for free:

* Painless Python WSGI and `virtualenv` integration
* Process monitoring, restarting, basic resource limiting, etc.
* Basic security scaffolding, beginning with the ability to define `uid`/`gid` on a per-app basis (if necessary)

## Application packaging

An app is simply a `git` repository with some additional files on the top level, the most important of which is the `Procfile`.

### `Procfile` format

`piku` recognizes six kinds of process declarations in the `Procfile`:

* `wsgi` workers, in the format `dotted.module:entry_point` (Python-only)
* `web` workers, which can be anything that honors the `PORT` environment variable
* `static` workers, which simply mount the first argument as the root static path
* `preflight` which is a special "worker" that is run once _before_ the app is deployed _and_ installing deps (can be useful for cleanups).
* `release` which is a special worker that is run once when the app is deployed, after installing deps (can be useful for build steps).
* `cron` workers, which require a simplified `cron` expression preceding the command to be run (e.g. `cron: */5 * * * * python batch.py` to run a batch every 5 minutes)
* `worker` processes, which are standalone workers and can have arbitrary names

So a Python application could have a `Procfile` like such:

```bash
# A module to be loaded by uwsgi to serve HTTP requests
wsgi: module.submodule:app
# A background worker
worker: python long_running_script.py
# Another worker with a different name
fetcher: python fetcher.py
# Simple cron expression: minute [0-59], hour [0-23], day [0-31], month [1-12], weekday [1-7] (starting Monday, no ranges allowed on any field)
cron: 0 0 * * * python midnight_cleanup.py
release: python initial_cleanup.py
```

...whereas a generic app would be:

```bash
web: embedded_server --port $PORT
worker: background_worker
```

Any worker will be automatically respawned upon failure ([uWSGI][uwsgi] will automatically shun/throttle crashy workers).

## `ENV` settings

Since `piku` is targeted at [12 Factor apps][12f], it allows you to set environment variables in a number of ways, the simplest of which is by adding an `ENV` file to your repository:

```bash
SETTING1=foo
# piku supports comments and variable expansion
SETTING2=${SETTING1}/bar
# if this isn't defined, piku will assign a random TCP port
PORT=9080
```

See [ENV.md](./ENV.md) for a full list of Piku variables which can also be set.

Environment variables can be changed after deployment using `config:set`.

## Runtime detection

`piku` follows a very simple set of rules to determine what kind of runtime is required:

1. If there's a `requirements.txt` file at the top level, then the app is assumed to require Python.
2. _TODO: Go_
3. _TODO: Node_
4. _TODO: Java_
2. For all the rest, a `Procfile` is required to determine application entry points. 


## Application isolation

Application isolation can be tackled at several levels, the most relevant of which being:

* OS/process isolation
* Runtime/library isolation

For 1.0, all applications run under the same `uid`, under separate branches of the same filesystem, and without any resource limiting.

Ways to improve upon that (short of full containerisation) typically entail the use of a `chroot` jail environment (which is available under most POSIX systems in one form or another) or Linux kernel namespaces - both of which are supported by [uWSGI][uwsgi] (which can also handle resource limiting to a degree).

As to runtime isolation, `piku` only provides `virtualenv` support until 1.0. Python apps can run under Python 2 or 3 depending on the setting of `PYTHON_VERSION`, but will always use pre-installed interpreters (Go, Node and Java support will share these limitations in each major version).

## Internals

`piku` uses two `git` repositories for each app: a bare repository for client push, and a clone for deployment (which is efficient in terms of storage since `git` tries to use hardlinks on local clones whenever possible).

This separation makes it easier to cope with long/large deployments and restore apps to a pristine condition, since the app will only go live after the deployment clone is reset (via `git checkout -f`).

## Components

This diagram (available as a `dot` file in the `img` folder) outlines how its components interact:

![](../img/piku.png)

[uwsgi]: https://github.com/unbit/uwsgi
[emperor]: http://uwsgi-docs.readthedocs.org/en/latest/Emperor.html
[12f]: http://12factor.net
