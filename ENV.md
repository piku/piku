## Configuriing Piku via ENV

You can configure deployment settings by placing special variables in an `ENV` file deployed with your app.

## Runtime Settings

* `PYTHON_VERSION` (int): Forces Python 3

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
* `UWSGI_ASYNCIO`: enable the Python 2/3 `asyncio` plugin

## Nginx Settings

* `NGINX_SERVER_NAME`: set the virtual host name associated with your app

