
# Manage


## Managing your Piku apps

To make life easier you can also install the `piku` helper into your path (e.g. `~/bin`):

```shell
curl https://raw.githubusercontent.com/piku/piku/master/piku > ~/bin/piku && chmod 755 ~/bin/piku
```

This shell script simplifies working with multiple `piku` remotes and applications:

* If you `cd` into a project folder that has a `git` remote called `piku` the helper will infer the remote server and app name and use them automatically:

```shell
$ piku logs
$ piku config:set MYVAR=12
$ piku stop
$ piku deploy
$ piku destroy
$ piku # <- show available remote and local commands
```

* If you are starting a new project, `piku init` will download example `Procfile` and `ENV` files into the current folder:

```shell
$ piku init
Wrote ./ENV file.
Wrote ./Procfile.
```

* The `piku` helper also lets you pass settings to the underlying SSH command: `-t` to run interactive commands remotely, and `-A` to proxy authentication credentials in order to do remote `git` pulls.

For instance, here's how to use the `-t` flag to obtain a `bash` shell in the app directory of one of your `piku` apps:

```shell
$ piku -t run bash
Piku remote operator.
Server: piku@cloud.mccormickit.com
App: dashboard

piku@piku:~/.piku/apps/dashboard$ ls
data  ENV  index.html  package.json  package-lock.json  Procfile  server.wisp
```

## Monitoring

Besides using the `logs` command, there is a [sample monitoring application](https://github.com/piku/piku-monitoring) to keep tabs on resource usage.