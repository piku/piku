# Design

The idea behind `piku` is that it provides the simplest possible way to deploy web apps or services. Simplicity comes at the expense of features, of course, and this document tries to capture the trade-offs.

## Core values

* Run on low end devices.
* Accessible to hobbyists and K-12 schools.
* ~1500 lines readable code.
* Functional code style.
* Few (single?) dependencies
* [12 factor app](https://12factor.net).
* Simplify user experience.
* Cover 80% of common use cases.
* Sensible defaults for all features.
* Leverage distro packages in Raspbian/Debian/Ubuntu (Alpine and RHEL support is WIP)
* Leverage standard tooling (`git`, `ssh`, `uwsgi`, `nginx`).
* Preserve backwards compatibility where possible

## Why uWSGI

Using [uWSGI][uwsgi] in [emperor mode][emperor] gives us the following features for free:

* Painless Python WSGI and `virtualenv` integration
* Process monitoring, restarting, basic resource limiting, etc.
* Basic security scaffolding, beginning with the ability to define `uid`/`gid` on a per-app basis (if necessary)

## Application packaging

An app is simply a `git` repository with some additional files on the top level, the most important of which is the `Procfile`.

## `ENV` settings

Since `piku` is targeted at [12 Factor apps][12f], it allows you to set environment variables in a number of ways, the simplest of which is by adding an `ENV` file to your repository:

```bash
SETTING1=foo
# piku supports comments and variable expansion
SETTING2=${SETTING1}/bar
# if this isn't defined, piku will assign a random TCP port
PORT=9080
```

See [configuration](../configuration/index.md) for a full list of environment variables that can also be set.

Environment variables can be changed after deployment using the `config:set` command.

## Runtime detection

`piku` follows a very simple set of rules to determine what kind of runtime is required, outlined in [the configuration section](../configuration/index.md#runtime-detection)

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

This diagram outlines how its components interact:

```mermaid
graph TD
    subgraph "systemd"
        nginx([nginx])
        sshd([sshd])
        uwsgi([uwsgi])
    end
    uwsgi-->vassal([vassal])
    vassal-.->uwsgi.ini
    sshd-->piku([piku.py])-->repo[git repo]
    Procfile-->uwsgi.ini
    an-->app
    repo---app
    repo---ENV
    repo---requirements.txt
    repo---Procfile
    requirements.txt-->virtualenv
    uwsgi.ini-->virtualenv
    ENV-->an
    ENV-->uwsgi.ini
    nginx-.-mn[master<br>nginx.conf]
    mn-.-an[app<br>nginx.conf]
```


[uwsgi]: https://github.com/unbit/uwsgi
[emperor]: http://uwsgi-docs.readthedocs.org/en/latest/Emperor.html
[12f]: http://12factor.net
