# Features

## Workflow

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
* It then looks at a [`Procfile`](configuration/procfile.md) and starts the relevant workers using `uwsgi` as a generic process manager.
* You can optionally also specify a `release` worker which is run once when the app is deployed.
* You can then remotely change application settings (`config:set`) or scale up/down worker processes (`ps:scale`).
* You can also bake application and `nginx` settings into an [`ENV` configuration file](configuration/env.md).

You can also deploy a `gh-pages` style static site using a `static` worker type, with the root path as the argument, and run a `release` task to do some processing on the server after `git push`.


## Virtual Hosts and SSL

`piku` has full virtual host support - i.e., you can host multiple apps on the same VPS and use DNS aliases to access them via different hostnames. 

`piku`  will also set up either a private certificate or obtain one via [Let's Encrypt](https://letsencrypt.org/) to enable SSL.

If you are on a LAN and are accessing `piku` from macOS/iOS/Linux clients, you can try using [`piku/avahi-aliases`](https://github.com/piku/avahi-aliases) to announce different hosts for the same IP address via Avahi/mDNS/Bonjour.

## Caching and Static Paths

Besides static sites, `piku` also supports directly mapping specific URL prefixes to filesystem paths (to serve static assets) or caching back-end responses (to remove load from applications).

These features are configured by setting appropriate values in the [`ENV`](configuration/env.md) file.

## Supported Platforms

`piku` is intended to work in any POSIX-like environment where you have Python, `nginx`, `uwsgi` and `ssh`: it has been deployed on Linux, FreeBSD, [Cygwin][cygwin] and the [Windows Subsystem for Linux][wsl].

As a baseline, it began its development on an original 256MB Rasbperry Pi Model B, and still runs reliably on it.

But its main use is as a micro-PaaS to run applications on cloud servers with both Intel and ARM CPUs, with either Debian or Ubuntu Linux as target platforms.

## Supported Runtimes

`piku` currently supports apps written in Python, Node, Clojure, Java and a few other languages (like Go) in the works.

But as a general rule, if it can be invoked from a shell, it can be run inside `piku`.