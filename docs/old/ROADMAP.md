# Roadmap

This was the original roadmap, filed here in 2019-11-21 for future reference:

- [ ] Prebuilt Raspbian image with everything baked in
- [ ] `chroot`/namespace isolation (tentative)
- [ ] Relay commands to other nodes
- [ ] Proxy deployments to other nodes (build on one box, deploy to many)
- [ ] Support Clojure/Java deployments through `boot` or `lein`
- [ ] Sample Go app
- [ ] Support Go deployments (in progress)
- [ ] nginx SSL optimization/cypher suites, own certificates
- [ ] Review deployment messages
- [ ] WIP: Review docs/CLI command documentation (short descriptions done, need `help <cmd>` and better descriptions)
- [ ] Lua/WSAPI support
- [x] Support for Java Apps with maven/gradle (in progress through jwsgi, by @matrixjnr)
- [x] Django and Wisp examples (by @chr15m)
- [x] Project logo (by @chr15m)
- [x] Various release/deployment improvements (by @chr15m)
- [x] Support Node deployments (by @chr15m)
- [x] Let's Encrypt support (by @chr15m)
- [x] Allow setting `nginx` IP bindings in `ENV` file (`NGINX_IPV4_ADDRESS` and `NGINX_IPV6_ADDRESS`)
- [x] Cleanups to remove 2.7 syntax internally
- [x] Change to Python 3 runtime as default, with `PYTHON_VERSION = 2` as fallback
- [x] Run in Python 3 only
- [x] (experimental) REPL in `feature/repl`
- [x] Python 3 support through `PYTHON_VERSION = 3`
- [x] static URL mapping to arbitrary paths (hat tip to @carlosefr for `nginx` tuning)
- [x] remote CLI (requires `ssh -t`)
- [x] saner uWSGI logging
- [x] `gevent` activated when `UWSGI_GEVENT = <integer>`
- [x] enable CloudFlare ACL when `NGINX_CLOUDFLARE_ACL = True`
- [x] Autodetect SPDY/HTTPv2 support and activate it
- [x] Basic nginx SSL config with self-signed certificates and UNIX domain socket connection
- [x] nginx support - creates an nginx config file if `NGINX_SERVER_NAME` is defined
- [x] Testing with pre-packaged [uWSGI][uwsgi] versions on Debian Jessie (yes, it was painful)
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

[click]: http://click.pocoo.org
[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
