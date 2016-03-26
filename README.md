# piku

The tiniest Heroku-like PaaS you've ever seen, inspired on [dokku][dokku].

## Motivation

I kept finding myself wanting an Heroku-like way to deploy stuff on a few remote ARM boards and [my Raspberry Pi cluster][raspi-cluster], but since [dokku][dokku] still doesn't work on ARM and even `docker` can be overkill sometimes, I decided to roll my own.

## Project Status/ToDo:

From the bottom up:

- [ ] Support Java deployments
- [ ] Support Go deployments
- [ ] `chroot` isolation
- [ ] Support barebones binary deployments
- [ ] Installation instructions
- [ ] Basic CLI commands to manage apps
- [ ] `virtualenv` isolation
- [ ] Support Python deployments
- [x] Repo creation upon first push
- [x] Basic understanding of [how `dokku` works](http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html)

## Target Workflow:

* Set up an SSH `git` remote pointing to `piku` with the app name as repo name (`git remote add paas piku@server:app1`) 
* `git push paas master` your code
* `piku` determines the runtime and installs dependencies
*  It then looks at a `Procfile` and starts the relevant workers

Later on, I intend to do fancier `dokku`-like stuff like reconfiguring `nginx`, but a twist I'm planning on doing is having one `piku` machine act as a build box and deploy the finished product to another.

Might take a while, though.

## Target Platforms:

As a baseline, I intend to make sure this runs on the original Rasbperry Pi Model B (which is where I'm testing it).

But since I have an ODROID-U2, [a bunch of Pi 2s][raspi-cluster] and a few more boards on the way, it will be tested on a number of places where running `x64` binaries is unfeasible.

In general, it will likely work in any POSIX-like environment where you have Python and SSH (I'm very likely to test it under [Cygwin][cygwin] at some point).

## Target Runtimes:

I intend to support Python, Go and Java, but will be focusing on Python first, moving from shared runtime to `virtualenv` (and later, if feasible, `pyenv` support).

## FAQ

**Q:** Why `piku`?

**A:** Partly because it's supposed to run on a [Pi][pi], because it's Japanese onomatopeia for 'twitch' or 'jolt', and because I know the name will annoy some of my friends.

**Q:** Why not just use `dokku`?

**A:** I use `dokku` daily, and for most of my personal stuff. But the `dokku` stack relies on a number of `x64` containers that need to be completely rebuilt for ARM, and when I decided I needed something like this (March 2016) that was barely possible - `docker` itself is not fully baked for ARM yet, and people are still trying to get `herokuish` and `buildstep` to build on ARM...)

[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com