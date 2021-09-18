[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![piku logo](./img/logo.png)

The tiniest Heroku/CloudFoundry-like PaaS you've ever seen.

`piku`, inspired by [dokku][dokku], allows you do `git push` deployments to your own servers.

[![asciicast](https://asciinema.org/a/Ar31IoTkzsZmWWvlJll6p7haS.svg)](https://asciinema.org/a/Ar31IoTkzsZmWWvlJll6p7haS)

### Documentation: [Using](#using-piku) | [Install](#install) | [Procfile](docs/DESIGN.md#procfile-format) | [ENV](./docs/ENV.md) | [Examples](./examples/README.md) | [Roadmap](https://github.com/piku/piku/projects/2) | [Contributing](./docs/CONTRIBUTING.md) | [LinuxConf Talk](https://www.youtube.com/watch?v=ec-GoDukHWk) | [Fast Web App Tutorial](https://github.com/piku/webapp-tutorial)

## Goals and Motivation

I kept finding myself wanting an Heroku/CloudFoundry-like way to deploy stuff on a few remote ARM boards and [my Raspberry Pi cluster][raspi-cluster], but since [dokku][dokku] didn't work on ARM at the time and even `docker` can be overkill sometimes, I decided to roll my own.

### Core values

 * Runs on low end devices.
 * Accessible to hobbyists and K-12 schools.
 * ~1000 lines readable code.
 * Functional code style.
 * Few (single?) dependencies
 * [12 factor app](https://12factor.net).
 * Simplify user experience.
 * Cover 80% of common use cases.
 * Sensible defaults.
 * Leverage distro packages in Raspbian/Debian/Ubuntu (Alpine and RHEL support is WIP)
 * Leverage standard tooling (`git`, `ssh`, `uwsgi`, `nginx`).
 * Preserve backwards compatibility where possible

## Using `piku`

`piku` supports a Heroku-like workflow, like so:

* Create a `git` SSH remote pointing to your `piku` server with the app name as repo name.
  `git remote add piku piku@yourserver:appname`.
* Push your code: `git push piku master`.
* `piku` determines the runtime and installs the dependencies for your app (building whatever's required).
   * For Python, it segregates each app's dependencies into a `virtualenv`.
   * For Go, it defines a separate `GOPATH` for each app.
   * For Node, it installs whatever is in `package.json` into `node_modules`.
   * For Java, it builds your app depending on either `pom.xml` or `build.gradle` file.
* It then looks at a [`Procfile` which is documented here](docs/DESIGN.md#procfile-format) and starts the relevant workers using [uWSGI][uwsgi] as a generic process manager.
* You can optionally also specify a `release` worker which is run once when the app is deployed.
* You can then remotely change application settings (`config:set`) or scale up/down worker processes (`ps:scale`).
* You can also bake application settings into a file called [`ENV` which is documented here](./docs/ENV.md).
* A `static` worker type, with the root path as the argument, can be used to deploy a gh-pages style static site.

## Install

To use `piku` you need a VPS, Raspberry Pi, or other server bootstrapped with `piku`'s requirements. You can use a single server to run multiple `piku` apps.

There are two main ways of deploying `piku` onto a new server:

* Use `cloud-init` when creating a new virtual machine or barebones automated deploy (check [this repository](https://github.com/piku/cloud-init) for examples)
* Use `piku-bootstrap` to reconfigure a new or existing virtual machine

**Warning**: You should use a fresh server or VPS instance without anything important running on it already, as `piku-bootstrap` will make changes to configuration files, running services, etc.

Once you've got a fresh server, download the [piku-bootstrap](./piku-bootstrap) shell script onto your local machine and run it:

```shell
curl https://piku.github.io/get | sh
```

The first time it is run `piku-bootstrap` will install itself into `~/.piku-bootstrap` on your local machine and set up a virtualenv there with the dependencies it requires. It will only need to do this once.

The script will display a usage message and you can then bootstrap your server:

```shell
./piku-bootstrap root@yourserver.net
```

If you put the `piku-bootstrap` script on your `PATH` somewhere, you can use it again to provision other servers in the future.

See below for instructions on [installing other custom dependencies](#installing-other-dependencies) that your apps might need like a database etc.

### `piku` client

To make life easier you can also install the [piku](./piku) helper CLI. Install it into your path e.g. `~/bin` to run it from anywhere.

```shell
./piku-bootstrap install-cli ~/bin
```

This shell script makes working with `piku` remotes a bit simpler. If you have a git remote called `piku` in the current folder it will infer the remote server and app name and insert those into the remote piku commands. This allows you to execute commands like the following on your running remote app:

```shell
$ piku logs
$ piku config:set MYVAR=12
$ piku stop
$ piku deploy
$ piku destroy
$ piku # <- will show help for the remote app
```

You can pass flags through to the underlying SSH command, for example `-t` to run interactive commands remotely, and `-A` to proxy authentication credentials in order to do remote git pulls.

Here is an example of using the `-t` flag to obtain a `bash` shell in the app directory of one of your Piku apps:

```
$ piku -t run bash
Piku remote operator.
Server: piku@cloud.mccormickit.com
App: dashboard

piku@piku:~/.piku/apps/dashboard$ ls
data  ENV  index.html  package.json  package-lock.json  Procfile  server.wisp
```

Tip: If you put this `piku` script on your `PATH` you can use the `piku` command across multiple apps on your local.

### Installing other dependencies

`piku-bootstrap` uses Ansible internally and it comes with several extra built-in playbooks which you can use to bootstrap common components onto your `piku` server.

Use `piku-bootstrap list-playbooks` to show a list of built-in playbooks, and then to install one add it as an argument to the bootstrap command.

For example, to deploy `nodeenv` onto your server:

```shell
piku-bootstrap root@yourserver.net nodeenv.yml
```

You can also use `piku-bootstrap` to run your own Ansible playbooks like this:

```shell
piku-bootstrap root@yourserver.net ./myplaybook.yml
```

## Virtual Hosts

If you are on a LAN and are accessing `piku` from macOS/iOS/Linux clients, you can try using [`piku/avahi-aliases`](https://github.com/piku/avahi-aliases) to announce different hosts via Avahi/mDNS/Bonjour.

## Supported Platforms

`piku` is intended to work in any POSIX-like environment where you have Python, [uWSGI][uwsgi] and SSH, i.e.: 
Linux, FreeBSD, [Cygwin][cygwin] and the [Windows Subsystem for Linux][wsl].

As a baseline, it began its development on an original, 256MB Rasbperry Pi Model B, and still runs reliably on it.

Since I have an ODROID-U2, [a bunch of Pi 2s][raspi-cluster] and a few more ARM boards on the way, it is often tested on a number of places where running `x64` binaries is unfeasible.

But there are already a few folk using `piku` on vanilla `x64` Linux without any issues whatsoever, so yes, you can use it as a micro-PaaS for 'real' stuff. Your mileage may vary.

## Supported Runtimes

`piku` currently supports deploying apps (and dependencies) written in Python, with Go, Clojure (Java) and Node (see [above](#project-statustodo)) in the works. But if it can be invoked from a shell, it can be run inside `piku`.

[click]: http://click.pocoo.org
[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
