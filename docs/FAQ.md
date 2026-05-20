# FAQ

**Q:** Why `piku`?

**A:** Partly because it's started out on the [Raspberry Pi][pi], because it's Japanese onomatopeia for 'twitch' or 'jolt', and because we knew the name would be cute and amusing.

**Q:** Why Python/why not Go?

**A:** We actually thought about doing this in Go right off the bat, but [click][click] is so cool and we needed to have `uwsgi` running anyway, so we caved in. But possible future directions are likely to take something like [suture](https://github.com/thejerf/suture) and port this across (or just use [Caddy](http://caddyserver.com)), doing away with `uwsgi` altogether.

Go also (at the time) did not have a way to vendor dependencies that we were comfortable with, and that is also why Go support fell behind. Hopefully that will change soon.

**Q:** What Python version does piku require?

**A:** Piku requires Python 3.10 or above to run (it can deploy apps using any Python version). We target the system Python available in the latest two Debian and Ubuntu LTS releases.

**Q:** Why not just use `dokku`?

**A:** We used `dokku` daily for many projects. But it relied on a number of `x64` containers that needed to be completely rebuilt for `ARM`, and when we decided we needed something like this (March 2016) that was barely possible - `docker` itself was not fully baked for `ARM` yet, and people were at the time just starting to get `herokuish` and `buildstep` to build on `ARM`.

[click]: http://click.pocoo.org
[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
