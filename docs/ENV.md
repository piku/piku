# Configuring Piku via ENV

You can configure deployment settings by placing special variables in an `ENV` file deployed with your app.

## Runtime Settings

* `PIKU_AUTO_RESTART` (boolean, defaults to `true`): Piku will restart all workers every time the app is deployed.

### Python

* `PYTHON_VERSION` (int): Forces Python 3

### Node

* `NODE_VERSION`: installs a particular version of node for your app if `nodeenv` is found on the path.

**Note**: you will need to stop and re-deploy the app to change the node version in a running app.

## Network Settings

* `BIND_ADDRESS`: IP address to which your app will bind (typically `127.0.0.1`)
* `PORT`: TCP port for your app to listen in (if deploying your own web listener).

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

## Nginx Settings

* `NGINX_SERVER_NAME`: set the virtual host name associated with your app
* `NGINX_CLOUDFLARE_ACL` (boolean): activate an ACL allowing access only from Cloudflare IPs
* `NGINX_STATIC_PATHS`: set an array of `/url:path` values
* `NGINX_HTTPS_ONLY`: tell nginx to auto-redirect non-SSL traffic to SSL site
* `NGINX_INCLUDE_FILE`: a file in the app's dir to include in nginx config `server` section - useful for including custom nginx directives.
* `NGINX_ALLOW_GIT_FOLDERS`: (boolean) allow access to `.git` folders (default: false, blocked)
