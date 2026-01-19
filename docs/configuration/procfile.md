
# `Procfile` format

`piku` supports a Heroku-like `Procfile` that you provide to indicate how to run one or more application processes (what Heroku calls "dynos"):

```bash
web: embedded_server --port $PORT
worker: background_worker
```

## Worker Types

`piku` supports different kinds of worker processes:

```bash
# A module to be loaded by uwsgi to serve HTTP requests
wsgi: module.submodule:app
# Background workers - you can define multiple workers with different names
worker: python long_running_script.py
fetcher: python fetcher.py
worker-email: python email_processor.py
# Simple cron expression: minute [0-59], hour [0-23], day [0-31], month [1-12], weekday [1-7] (starting Monday, no ranges allowed on any field)
cron: 0 0 * * * python midnight_cleanup.py
release: python initial_cleanup.py
```
Each of these has slightly different features:

### `wsgi`

`wsgi` workers are Python-specific and must be specified in the format `dotted.module:entry_point`. `uwsgi` will load the specified module and call the `entry_point` function to start the application, handling all the HTTP requests directly (your Python code will run the handlers, but will run as a part of the `uwsgi` process).

`uwsgi` will automatically spawn multiple workers for you, and you can control the number of workers via the `UWSGI_PROCESSES` environment variable.

Also, in this mode `uwsgi` will talk to `nginx` via a Unix socket, so you don't need to worry about the HTTP server at all.

### `php`

`php` workers will execute PHP code in files with the `.php` extension and serve other files. For security reasons, files with the '.inc' extension are not executed.

!!! note
You will need to install the [uwsgi-plugin-php](https://packages.debian.org/stable/web/uwsgi-plugin-php) package for Debian-based systems, such as Ubuntu, or the equivalent for your distro. This package is available for Ubuntu [20.04](https://packages.ubuntu.com/focal/uwsgi-plugin-php) and [24.04](https://packages.ubuntu.com/noble/uwsgi-plugin-php), but seems to have been withdrawn from 22.04.
!!! note
If you place a `php.ini` file in the root of your app, the PHP interpreter for this app will ignore the default system `php.ini`. If your distro is configured to include additional files from an auxiliary directory, those files will continue to be processed.

### `web`

`web` workers can be literally any executable that `uwsgi` can run and that will serve HTTP requests. They must (by convention) honor the `PORT` environment variable, so that the `nginx` reverse proxy can talk to them.

### `worker`

`worker` processes are just standard processes that run in the background. They can perform any tasks your app requires that isn't directly related to serving web pages.

You can have multiple `worker` processes by giving them unique names. Each worker process can have an arbitrary name as long as it doesn't conflict with the reserved worker types (`wsgi`, `web`, `php`, `static`, `cron`, `preflight`, `release`).

For example, this Procfile defines multiple worker processes:

```bash
worker: python default_worker.py
worker-host: python host_worker.py  
worker-proxy: node proxy.js
data-processor: python process_data.py
```

This allows you to run different background tasks and filter logs for specific workers using `piku logs worker-host` or `piku logs data-processor`.

### `static`

`static` workers are simply a way to direct `nginx` to mount the first argument as a static path and serve it directly. This is useful for serving (and caching) static files directly from your app, without having to go through application code.

!!! note
    See [`nginx` caching](env.md#nginx-caching) for more information on how to configure `nginx` to serve static files.

### `cron`

A `cron` worker is a process that runs at a specific time (or intervals), using a simplified `crontab` expression preceding the command to be run (e.g. `cron: */5 * * * * python batch.py` to run a batch every 5 minutes)

Multiple crons can be scheduled by simply adding multiple entries with `cron` prefix.

```
...
cron1: */5 * * * * python batch.py
cron2: 0 * * * * python batch.py
...
```

!!! warning
    `crontab` expressions are simplified and do not support ranges or lists, only single values, splits and `*` (wildcard).

#### alternatives
```Python```
[apscheduler](https://github.com/agronholm/apscheduler) - Provides it's own library for scheduling jobs, and honors the full regex of crontab.


### `preflight`

`preflight`  is a special "worker" that is run once _before_ the app is deployed _and_ dependencies are installed (can be useful for cleanups, like resetting caches, removing older versions of files, etc).

### `release`

`release` which is a special worker that is run once when the app is deployed, _after_ installing dependencies (can be useful for build steps).



Any worker will be automatically respawned upon failure ([uWSGI][uwsgi] will automatically shun/throttle crashy workers).
