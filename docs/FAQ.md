# FAQ

**Q:** Why `piku`?

**A:** Partly because it's started out on the [Raspberry Pi][pi], because it's Japanese onomatopeia for 'twitch' or 'jolt', and because we knew the name would be cute and amusing.

**Q:** Why Python/why not Go?

**A:** We actually thought about doing this in Go right off the bat, but [click][click] is so cool and we needed to have `uwsgi` running anyway, so we caved in. But possible future directions are likely to take something like [suture](https://github.com/thejerf/suture) and port this across (or just use [Caddy](http://caddyserver.com)), doing away with `uwsgi` altogether.

Go also (at the time) did not have a way to vendor dependencies that we were comfortable with, and that is also why Go support fell behind. Hopefully that will change soon.

**Q:** Does it run under Python 3?

**A:** Right now, it _only_ runs on Python 3, even though it can deploy apps written in both major versions. It began its development using 2.7 and using`click` for abstracting the simpler stuff, and we eventually switched over to 3.5 once it was supported in Debian Stretch and Raspbian since we wanted to make installing it on the Raspberry Pi as simple as possible.

**Q:** Why not just use `dokku`?

**A:** We used `dokku` daily for many projects. But it relied on a number of `x64` containers that needed to be completely rebuilt for `ARM`, and when we decided we needed something like this (March 2016) that was barely possible - `docker` itself was not fully baked for `ARM` yet, and people were at the time just starting to get `herokuish` and `buildstep` to build on `ARM`.

[click]: http://click.pocoo.org
[pi]: http://www.raspberrypi.org
[dokku]: https://github.com/dokku/dokku
[raspi-cluster]: https://github.com/rcarmo/raspi-cluster
[cygwin]: http://www.cygwin.com
[uwsgi]: https://github.com/unbit/uwsgi
[wsl]: https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux
