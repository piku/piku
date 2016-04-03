# piku

The tiniest Heroku/CloudFoundry-like PaaS you've ever seen, inspired by [dokku][dokku].

## Motivation

I kept finding myself wanting an Heroku/CloudFoundry-like way to deploy stuff on a few remote ARM boards and [my Raspberry Pi cluster][raspi-cluster], but since [dokku][dokku] still doesn't work on ARM and even `docker` can be overkill sometimes, I decided to roll my own.

## Project Status/ToDo:

From the bottom up:

- [ ] Prebuilt Raspbian image with everything baked in
- [ ] `chroot`/namespace isolation (tentative)
- [ ] Proxy deployments to other nodes (build on one box, deploy to many) 
- [ ] Support Node deployments
- [ ] Support Clojure/Java deployments
- [ ] Sample Go app
- [ ] Support Go deployments
- [ ] CLI command documentation
- [x] Support barebones binary deployments
- [x] Complete installation instructions (see `INSTALL.md`, which also has a draft of Go installation steps)
- [x] Installation helper/SSH key setup
- [x] Worker scaling 
- [x] Remote CLI commands for changing/viewing applied/live settings
- [x] Remote tailing of all logfiles for a single application
- [x] HTTP port selection (and per-app environment variables)
- [x] Sample Python app
- [X] `Procfile` support (`wsgi` and `worker` processes for now, `web` processes being tested)
- [x] Basic CLI commands to manage apps
- [x] `virtualenv` isolation
- [x] Support Python deployments
- [x] Repo creation upon first push
- [x] Basic understanding of [how `dokku` works](http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html)

## Using `piku``

`piku` supports a Heroku-like workflow, like so:

* Create a `git` SSH remote pointing to `piku` with the app name as repo name (`git remote add paas piku@server:app1`) 
* `git push paas master` your code
* `piku` determines the runtime and installs the dependencies for your app (building whatever's required)
    * For Python, it segregates each app's dependencies into a `virtualenv`
    * For Go, it defines a separate `GOPATH` for each app
* It then looks at a `Procfile` and starts the relevant workers using [uWSGI][uwsgi] as a generic process manager
* You can then remotely change application settings (`config:set`) or scale up/down worker processes (`ps:scale`) at will.

Later on, I intend to do fancier `dokku`-like stuff like reconfiguring `nginx`, but a twist I'm planning on doing is having one `piku` machine act as a build box and deploy the finished product to another.

## Supported Platforms

`piku` is intended to work in any POSIX-like environment where you have Python, [uWSGI][uwsgi] and SSH, i.e.: 
Linux, FreeBSD, [Cygwin][cygwin] and the [Windows Subsystem for Linux][wsl].

As a baseline, this is currently being developed an original, 256MB Rasbperry Pi Model B.

Since I have an ODROID-U2, [a bunch of Pi 2s][raspi-cluster] and a few more ARM boards on the way, it will be tested on a number of places where running `x64` binaries is unfeasible.

## Supported Runtimes

`piku` will support deploying apps written in Python, Go, Clojure (Java) and Node (see [above](#project-statustodo)).

## FAQ

**Q:** Why `piku`?

**A:** Partly because it's supposed to run on a [Pi][pi], because it's Japanese onomatopeia for 'twitch' or 'jolt', and because I know the name will annoy some of my friends.

**Q:** Why Python/why not Go?

**A:** I actually thought about doing this in Go right off the bat, but [click][click] is so cool and I needed to have [uWSGI][uwsgi] running anyway, so I caved in. But I'm very likely to take something like [suture](https://github.com/thejerf/suture) and port this across, doing away with [uWSGI][uwsgi] altogether.

**Q:** Does it run under Python 3?

**A:** It should. `click` goes a long way towards abstracting the simpler stuff, and I tried to avoid most obvious incompatibilities (other than a few differences in `subprocess.call` and the like). However, this targets Python 2.7 first, since that's the default on Raspbian. Pull requests are welcome.

**Q:** Why not just use `dokku`?

**A:** I use `dokku` daily, and for most of my personal stuff. But the `dokku` stack relies on a number of `x64` containers that need to be completely rebuilt for ARM, and when I decided I needed something like this (March 2016) that was barely possible - `docker` itself is not fully baked for ARM yet, and people are still trying to get `herokuish` and `buildstep` to build on ARM.

[click]: http://click.poocoo.org
[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
