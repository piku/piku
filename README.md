![piku logo](./img/logo.png)

`piku`, inspired by [dokku][dokku], allows you do `git push` deployments to your own servers, no matter how small they are.

## Demo

[![asciicast](https://asciinema.org/a/Ar31IoTkzsZmWWvlJll6p7haS.svg)](https://asciinema.org/a/Ar31IoTkzsZmWWvlJll6p7haS)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

### Documentation: [Install](#install) | [Using](#using-piku) | [Procfile](https://piku.github.io/configuration/procfile.html) | [ENV](https://piku.github.io/configuration/env.html) | [Examples](https://piku.github.io/community/examples.html) | [Roadmap](https://github.com/piku/piku/projects/2) | [Contributing](https://piku.github.io/community/contributing.html) | [LinuxConf Talk](https://www.youtube.com/watch?v=ec-GoDukHWk) | [Fast Web App Tutorial](https://github.com/piku/webapp-tutorial) | [Discussion Forum](https://github.com/piku/piku/discussions)

## [Install](https://piku.github.io/install)

TL;DR:

```bash
curl https://piku.github.io/get | sh
```

There are also [other installation methods](https://piku.github.io/install) available, including [`cloud-init`](https://github.com/piku/cloud-init) and [manual installation](https://piku.github.io/install).

## Project Activity

**`piku` is considered STABLE**. It is actively maintained, but "actively" here means the feature set is pretty much done, so it is only updated when new language runtimes are added or reproducible bugs crop up.

It currently requires Python 3.7 or above, since even though 3.8+ is now the baseline Python 3 version in Ubuntu LTS 20.04 and Debian 11 has already moved on to 3.9, there are no substantial differences between those versions.

## Motivation

We wanted an Heroku/CloudFoundry-like way to deploy stuff on a few `ARM` boards, but since [dokku][dokku] didn't work on `ARM` at the time and even `docker` can be overkill sometimes, a simpler solution was needed.

`piku` is currently able to deploy, manage and independently scale multiple applications per host on both ARM and Intel architectures, and works on any cloud provider (as well as bare metal) that can run Python, `nginx` and `uwsgi`.

## Using `piku`

`piku` supports a Heroku-like workflow:

* Create a `git` SSH remote pointing to your `piku` server with the app name as repo name:
  `git remote add piku piku@yourserver:appname`.
* Push your code: `git push piku master` (or if you want to push a different branch than the current one use `git push piku release-branch-name`).
* `piku` determines the runtime and installs the dependencies for your app (building whatever's required).
   * For Python, it segregates each app's dependencies into a `virtualenv`.
   * For Go, it defines a separate `GOPATH` for each app.
   * For Node, it installs whatever is in `package.json` into `node_modules`.
   * For Java, it builds your app depending on either `pom.xml` or `build.gradle` file.
   * For Clojure, it can use either `leiningen` or the Clojure CLI and a `deps.edn` file.
   * For Ruby, it does `bundle install` of your gems in an isolated folder.
* It then looks at a [`Procfile`](docs/DESIGN.md#procfile-format) which is [documented here](docs/DESIGN.md#procfile-format) and starts the relevant workers using [uWSGI][uwsgi] as a generic process manager.
* You can optionally also specify a `release` worker which is run once when the app is deployed.
* You can then remotely change application settings (`config:set`) or scale up/down worker processes (`ps:scale`).
* You can also bake application and `nginx` settings into an [`ENV`](./docs/ENV.md) file which is [documented here](./docs/ENV.md).

You can also deploy a `gh-pages` style static site using a `static` worker type, with the root path as the argument, and run a `release` task to do some processing on the server after `git push`.

### Virtual Hosts and SSL

`piku` has full virtual host support - i.e., you can host multiple apps on the same VPS and use DNS aliases to access them via different hostnames. 

`piku`  will also set up either a private certificate or obtain one via [Let's Encrypt](https://letsencrypt.org/) to enable SSL.

If you are on a LAN and are accessing `piku` from macOS/iOS/Linux clients, you can try using [`piku/avahi-aliases`](https://github.com/piku/avahi-aliases) to announce different hosts for the same IP address via Avahi/mDNS/Bonjour.

### Caching and Static Paths

Besides static sites, `piku` also supports directly mapping specific URL prefixes to filesystem paths (to serve static assets) or caching back-end responses (to remove load from applications).

These features are configured by setting appropriate values in the [`ENV`](./docs/ENV.md) file.

### Supported Platforms

`piku` is intended to work in any POSIX-like environment where you have Python, `nginx`, [`uWSGI`][uwsgi] and SSH: it has been deployed on Linux, FreeBSD, [Cygwin][cygwin] and the [Windows Subsystem for Linux][wsl].

As a baseline, it began its development on an original 256MB Rasbperry Pi Model B, and still runs reliably on it.

But its main use is as a micro-PaaS to run applications on cloud servers with both Intel and ARM CPUs, with Debian and Ubuntu Linux as target platforms.

### Supported Runtimes

`piku` currently supports apps written in Python, Node, Clojure, Java and a few other languages (like Go) in the works.

But as a general rule, if it can be invoked from a shell, it can be run inside `piku`.

### Core values

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

[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux