# ![](img/logo.svg)

`piku`, inspired by `dokku`, allows you do `git push` deployments to your own servers, no matter how small they are.

<p class="grid cards" markdown>
    <a href="install/index.html" class="card">
    :fontawesome-solid-download: Installing
    </a>
    <a href="features.html" class="card">
    :material-gesture-tap-hold: Using/Features
    </a>
    <a href="manage.html" class="card">
    :octicons-tools-16: Managing and Monitoring
    </a>
    <a href="community/examples.html" class="card">
    :material-application-outline: Examples
    </a>
    <a href="https://github.com/piku/webapp-tutorial" class="card">
    :fontawesome-solid-graduation-cap: Web App Tutorial
    </a>
</p>

## Demo

![asciicast](img/demo.svg)

## Workflow

`piku` supports a Heroku-like workflow:

* Create a `git` SSH remote pointing to your `piku` server with the app name as repo name:
  `git remote add piku piku@yourserver:appname`.
* Push your code: `git push piku master` (or if you want to push a different branch than the current one use `git push piku release-branch-name`).
* `piku` determines the runtime and installs the dependencies for your app (building whatever's required).
* It then looks at a [`Procfile`](configuration/procfile.md) and starts matching worker processes.
  * You can optionally also specify a `release` worker which is run once when the app is deployed.
* You can then remotely change application settings (`config:set`) or scale up/down worker processes (`ps:scale`).
* You can also bake application and `nginx` settings into an [`ENV` configuration file](configuration/env.md). 

You can also deploy a `gh-pages` style static site using a `static` worker type, with the root path as the argument, and run a `release` task to do some processing on the server after `git push`.

## Project Activity

**`piku` is considered STABLE**. It is actively maintained, but "actively" here means the feature set is pretty much done, so it is only updated when new language runtimes are added or reproducible bugs crop up.

It currently requires Python 3.8 or above, which is the baseline in Ubuntu LTS 20.04 while Debian 11 has already moved on to 3.9. Sometime in 2025 this will be changed according to the next section.

## Deprecation Notices

Since most of its users run it on LTS distributions, there is no rush to introduce disruption. The current plan is to throw up a warning for older runtimes and do regression testing for 3.10-3.12 (replacing the current bracket of tests from 3.8 to 3.12), and make sure we also cover Ubuntu 22.04, Debian 11 and Fedora 39+.
