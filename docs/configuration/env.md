# `ENV` Variables

You can configure deployment settings by placing special variables in an `ENV` file deployed with your app. This file should be placed in the root of your app's directory, and can look something like this:

```bash
# variables are global and can be replaced
SETTING1=True
SETTING2=${SETTING1}/Maybe

# addr:port
PORT=9080
BIND_ADDRESS=0.0.0.0

# the max number the worker will process
RANGE=10

# worker sleep interval between prints
INTERVAL=1
```

## Runtime Settings

* `PIKU_AUTO_RESTART` (boolean, defaults to `true`): Piku will restart all workers every time the app is deployed. You can set it to `0`/`false` if you prefer to deploy first and then restart your workers separately.

### Python

* `PYTHON_VERSION` (int): Forces Python 3

!!! warning
    This is mostly deprecated (since `piku` now runs solely on Python 3.x), but is kept around for legacy compatibility.

### Node

* `NODE_VERSION`: installs a particular version of node for your app if `nodeenv` is found on the path. Optional; if not specified, the system-wide node package is used.
* `NODE_PACKAGE_MANAGER`: use an alternate package manager (e.g. set to `yarn` or `pnpm`). The package manager will be installed with `npm install -g`.

!!! note
    you will need to stop and re-deploy the app to change the `node` version in a running app.

## Network Settings

* `BIND_ADDRESS`: IP address to which your app will bind (typically `127.0.0.1`)
* `PORT`: TCP port for your app to listen in (if deploying your own web listener).
* `DISABLE_IPV6` (boolean): if set to `true`, it will remove IPv6-specific items from the `nginx` config, which will accept only IPv4 connections

## uWSGI Settings

* `UWSGI_MAX_REQUESTS` (integer): set the `max-requests` option to determine how many requests a worker will receive before it's recycled.
* `UWSGI_LISTEN` (integer): set the `listen` queue size.
* `UWSGI_PROCESSES` (integer): set the `processes` count.
* `UWSGI_ENABLE_THREADS` (boolean): set the `enable-threads` option.
* `UWSGI_LOG_MAXSIZE` (integer): set the `log-maxsize`.
* `UWSGI_LOG_X_FORWARDED_FOR` (boolean): set the `log-x-forwarded-for` option.
* `UWSGI_GEVENT`: enable the Python 2 `gevent` plugin
* `UWSGI_ASYNCIO` (integer): enable the Python 2/3 `asyncio` plugin and set the number of tasks
* `UWSGI_INCLUDE_FILE`: a uwsgi config file in the app's dir to include - useful for including custom uwsgi directives.
* `UWSGI_IDLE` (integer): set the `cheap`, `idle` and `die-on-idle` options to have workers spawned on demand and killed after _n_ seconds of inactivity. 

!!! note
    `UWSGI_IDLE` applies to _all_ the workers, so if you have `UWSGI_PROCESSES` set to 4, they will all be killed simultaneously. Support for progressive scaling of workers via `cheaper` and similar uWSGI configurations will be added in the future. 

## `nginx` Settings

* `NGINX_SERVER_NAME`: set the virtual host name associated with your app
* `NGINX_STATIC_PATHS` (string, comma separated list): set an array of `/url:path` values that will be served directly by `nginx`
* `NGINX_CLOUDFLARE_ACL` (boolean, defaults to `false`): activate an ACL allowing access only from Cloudflare IPs
* `NGINX_HTTPS_ONLY` (boolean, defaults to `false`): tell `nginx` to auto-redirect non-SSL traffic to SSL site. 

!!! note
    if used with Cloudflare, `NGINX_HTTPS_ONLY` will cause an infinite redirect loop - keep it set to `false`, use `NGINX_CLOUDFLARE_ACL` instead and add a Cloudflare Page Rule to "Always Use HTTPS" for your server (use `domain.name/*` to match all URLs). 

### `nginx` Caching

When `NGINX_CACHE_PREFIXES` is set, `nginx` will cache requests for those URL prefixes to the running application (`uwsgi`-like or `web` workers) and reply on its own for `NGINX_CACHE_TIME` to the outside. This is meant to be used for compute-intensive operations like resizing images or providing large chunks of data that change infrequently (like a sitemap). 

The behavior of the cache can be controlled with the following variables:

* `NGINX_CACHE_PREFIXES` (string, comma separated list): set an array of `/url` values that will be cached by `nginx`
* `NGINX_CACHE_SIZE` (integer, defaults to 1): set the maximum size of the `nginx` cache, in GB
* `NGINX_CACHE_TIME` (integer, defaults to 3600): set the amount of time (in seconds) that valid backend replies (`200 304`) will be cached.
* `NGINX_CACHE_REDIRECTS` (integer, defaults to 3600): set the amount of time (in seconds) that backend redirects (`301 307`) will be cached.
* `NGINX_CACHE_ANY` (integer, defaults to 3600): set the amount of time (in seconds) that any other replies (other than errors) will be cached.
* `NGINX_CACHE_CONTROL` (integer, defaults to 3600): set the amount of time (in seconds) for cache control headers (`Cache-Control "public, max-age=3600"`)
* `NGINX_CACHE_EXPIRY` (integer, defaults to 86400): set the amount of time (in seconds) that cache entries will be kept on disk.
* `NGINX_CACHE_PATH` (string, detaults to `~piku/.piku/<appname>/cache`): location for the `nginx` cache data.

!!! note
    `NGINX_CACHE_PATH` will be _completely managed by `nginx` and cannot be removed by Piku when the application is destroyed_. This is because `nginx` sets the ownership for the cache to be exclusive to itself, and the `piku` user cannot remove that file tree. So you will either need to clean it up manually after destroying the app or store it in a temporary filesystem (or set the `piku` user to the same UID as `www-data`, which is not recommended).

Right now, there is no provision for cache revalidation (i.e., `nginx` asking your backend if the cache entries are still valid), since that requires active application logic that varies depending on the runtime--`nginx` will only ask your backend for new content when `NGINX_CACHE_TIME` elapses. If you require that kind of behavior, that is still possible via `NGINX_INCLUDE_FILE`.

Also, keep in mind that using `nginx` caching with a `static` website worker will _not_ work (and there's no point to it either).

### `nginx` Overrides

* `NGINX_INCLUDE_FILE`: a file in the app's dir to include in nginx config `server` section - useful for including custom `nginx` directives.
* `NGINX_ALLOW_GIT_FOLDERS`: (boolean) allow access to `.git` folders (default: false, blocked)

## Acme Settings

* `ACME_ROOT_CA`: set the certificate authority that Acme should use to generate public ssl certificates (string, default: `letsencrypt.org`)
