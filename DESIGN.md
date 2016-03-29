# Design Notes

The idea behind `piku` is that it provides the simplest possible way to deploy web apps or services. Simplicity comes at the expense of features, of course, and this document tries to capture the trade-offs.

## Why uWSGI

Using [uWSGI][uwsgi] in [emperor mode][emperor] gives us the following features for free:

* Painless Python WSGI and `virtualenv` integration
* Process monitoring, restarting, basic resource limiting, etc.
* Basic security scaffolding, beginning with the ability to define `uid´/`gid` on a per-app basis (if necessary)

## Application packaging

An app is simply a `git` repository with some additional files on the top level, the most important of which is the `Procfile`.

### `Procfile` format

`piku` recognizes three kinds of process declarations in the `Procfile`:

* `wsgi` workers, in the format `dotted.module:entry_point` (Python-only)
* `web` workers, which can be anything that honors the `PORT` environment variable
* `worker` prcesses, which are standalone workers

So a Python application could have a `Procfile` like such:

```bash
wsgi: module.submodule:app
worker: python long_running_script.py 
```

...whereas a generic app would be:

```bash
web: embedded_server --port $PORT
worker: background_worker
````

Any worker will be automatically respawned upon failure ([uWSGI][uwsgi] will automatically shun/throttle crashy workers).

## Runtime detection

`piku` follows a very simple set of rules to determine what kind of runtime is required:

1. If there's a `requirements.txt` file at the top level, then the app is assumed to require Python.
2. _TODO: Go_
3. _TODO: Node_
4. _TODO: Java_
2. For all the rest, a `Procfile` is required to determine the application entry points. 


## Application isolation

Application isolation can be tackled at several levels, the most relevant of which being:

* OS/process isolation
* Runtime/library isolation

For 1.0, all applications run under the same `uid`, under separate branches of the same filesystem, and without any resource limiting.

Ways to improve upon that (short of full containerisation) typically entail the use of a `chroot` jail environment (which is available under most POSIX systems in one form or another) or Linux kernel namespaces - both of which are supported by [uWSGI][uwsgi] (which can also handle resource limiting to a degree).

As to runtime isolation, `piku` only provides `virtualenv` support until 1.0, and all Python apps will use the default interpreter (Go, Node and Java support will share these limitations in each major version).

Supporting multiple Python versions can be done by deploying `piku` again under a different Python or using `pyenv` when building app environments, which makes it a little harder to manage using the same [uWSGI][uwsgi] setup (but not impossible).

## Internals

`piku` uses two `git` repositories for each app: a bare repository for client push, and a clone for deployent (which is efficient in terms of storage since `git` tries to use hardlinks on local clones whenever possible).

This separation makes it easier to cope with long/large deployments and restore apps to a pristine condition, since the app will only go live after the deployment clone is reset (via `git checkout -f`).

[uwsgi]: https://github.com/unbit/uwsgi
[emperor]: http://uwsgi-docs.readthedocs.org/en/latest/Emperor.html
