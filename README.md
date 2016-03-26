# piku

The tiniest Heroku-like PaaS you've ever seen, inspired on [dokku][dokku].

## Motivation

I kept finding myself wanting an Heroku-like way to deploy stuff on [my Raspberry Pi cluster][raspi-cluster], but since [dokku][dokku] still doesn't work on ARM and even `docker` can be overkill sometimes, I decided to roll my own.

## Project Status/ToDo:

From the bottom up:

- [ ] Support Java deployments
- [ ] Support Go deployments
- [ ] `chroot` isolation
- [ ] Support barebones binary deployments
- [ ] Installation instructions
- [ ] `virtualenv` isolation
- [ ] Support Python deployments
- [x] Repo creation upon first push
- [x] Basic understanding of [how `dokku` works](http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html)

## Target Workflow:

* `git push` your code over SSH
* `piku` determines the runtime and installs dependencies
*  It then looks at a `Procfile` and starts the relevant workers

Later on, I intend to do fancier `dokku`-like stuff like reconfiguring `nginx`, but a twist I'm planning on doing is having one `piku` machine act as a build box and deploy the finished product to another.

Might take a while, though.

## Target Runtimes:

I intend to support Python, Go and Java, but will be focusing on Python first, moving from shared runtime to `virtualenv` (and later, if feasible, `pyenv` support).

## FAQ

**Q:** Why `piku`?

**A:** Partly because it's supposed to run on a [Pi][pi], and because it's Japanese onomatopeia for 'twitch' or 'jolt'.

**Q:** Why not just use `dokku`?

**A:** Oh, I do that daily. The thing is, the entire `dokku` stack relies on a number of x64 containers that need to be completely rebuilt for ARM, and when I decided I needed something like this (March 2016) that was barely possible -- `docker` itself is not fully baked for ARM yet, and people are still trying to get `herokuish` and `buildstep` to build on ARM...)

[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster