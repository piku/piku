# Configuring Applications

A minimal `piku` app has a root directory structure similar to  this:

```bash
ENV
Procfile
app.py
worker.py
requirements.txt
```

<p class="grid cards" markdown>
    <a href="./env.html" class="card">
    :material-file-key: ENV
    </a>
    <a href="./procfile.html" class="card">
    :material-file-cog: Procfile
    </a>
</p>

## Configuration Files

`piku` relies on two configuration files shipped with your app to determine how to run it: [`ENV`](env.md) and [`Procfile`](procfile.md).

* The [`ENV`](env.md) file contains environment variables that allow you to configure both `piku` and your app, following the [12-factor app](https://12factor.net) approach.
* The [`Procfile`](procfile.md) tells `piku` what kind of workers to run

## Runtime Detection

Besides [`ENV`](env.md) and [`Procfile`](procfile.md), `piku` also looks for runtime-specific files in the root of your app's directory:

* If there's a `requirements.txt` or `pyproject.toml` file at the top level, then the app is assumed to require Python. Installing an app with a `pyproject.toml` will require [poetry](https://python-poetry.org/) or [uv](https://docs.astral.sh/uv/).
* If there's a `Gemfile` at the top level, then the app is assumed to require Ruby.
* If there's a `package.json` file at the top level, then the app is assumed to require Node.js.
* If there's a `pom.xml` or a `build.gradle` file at the top level, then the app is assumed to require Java.
* If there's a `deps.edn` or `project.clj` file at the top level, then the app is assumed to require Clojure.
* If there's a `Godeps` file at the top level, then the app is assumed to require Go.

!!! info
    `go.mod` support is currently in development.

These are not exclusive, however. There is also [a sample Phoenix app](../community/examples.md#phoenix) that demonstrates how to add support for additional runtimes.
