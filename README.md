# piku

The tiniest Heroku/CloudFoundry-like PaaS you've ever seen, inspired by [dokku][dokku].

## Motivation

I kept finding myself wanting an Heroku/CloudFoundry-like way to deploy stuff on a few remote ARM boards and [my Raspberry Pi cluster][raspi-cluster], but since [dokku][dokku] still doesn't work on ARM and even `docker` can be overkill sometimes, I decided to roll my own.

## Project Status/ToDo:

From the bottom up:

- [ ] Support Node deployments (if at all possible in a sane fashion)
- [ ] `chroot`/namespace isolation
- [ ] Proxy deployments to other nodes (build on one box, deploy to many) 
- [ ] Support Clojure/Java deployments
- [ ] Support Go deployments
- [ ] Support barebones binary deployments
- [ ] CLI command documentation
- [ ] Complete installation instructions (see `INSTALL.md` for a working draft)
- [ ] Installation helper/SSH key add
- [x] Worker scaling 
- [x] Remote CLI commands for changing/viewing applied/live settings
- [x] Remote tailing of all logfiles for a single application
- [x] HTTP port selection (and per-app environment variables)
- [x] Sample Python app
- [X] `Procfile` support (`wsgi` and `worker` processes for now, `web` processes being tested)
- [x] Basic CLI commands to manage apps
- [x] `virtualenv` isolation
- [x] Support Python deployments (currently hardcoded until `Procfile` is implemented)
- [x] Repo creation upon first push
- [x] Basic understanding of [how `dokku` works](http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html)

## Workflow

* Set up an SSH `git` remote pointing to `piku` with the app name as repo name (`git remote add paas piku@server:app1`) 
* `git push paas master` your code
* `piku` determines the runtime and installs the dependencies for your app (building whatever's required)
    * For Python, it segregates each app's dependencies into a `virtualenv`
*  It then looks at a `Procfile` and starts the relevant workers using [uWSGI][uwsgi] as a generic process manager

Later on, I intend to do fancier `dokku`-like stuff like reconfiguring `nginx`, but a twist I'm planning on doing is having one `piku` machine act as a build box and deploy the finished product to another.

Might take a while, though.

## Target Platforms

As a baseline, I intend to make sure this runs on the original Rasbperry Pi Model B (which is where I'm testing it).

But since I have an ODROID-U2, [a bunch of Pi 2s][raspi-cluster] and a few more boards on the way, it will be tested on a number of places where running `x64` binaries is unfeasible.

In general, it will likely work in any POSIX-like environment where you have Python and SSH (I'm very likely to test it under [Cygwin][cygwin] at some point).

## Target Runtimes

I intend to support Python, Go, Node and Clojure (Java), but will be focusing on Python first.

## FAQ

**Q:** Why `piku`?

**A:** Partly because it's supposed to run on a [Pi][pi], because it's Japanese onomatopeia for 'twitch' or 'jolt', and because I know the name will annoy some of my friends.

**Q:** Does it run under Python 3?

**A:** It should. `click` goes a long way towards abstracting the simpler stuff, and I tried to avoid most obvious incompatibilities (other than a few differences in `subprocess.call` and the like). However, this targets Python 2.7 first, since that's the default on Raspbian. Pull requests are welcome.

**Q:** Why not just use `dokku`?

**A:** I use `dokku` daily, and for most of my personal stuff. But the `dokku` stack relies on a number of `x64` containers that need to be completely rebuilt for ARM, and when I decided I needed something like this (March 2016) that was barely possible - `docker` itself is not fully baked for ARM yet, and people are still trying to get `herokuish` and `buildstep` to build on ARM.

[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
