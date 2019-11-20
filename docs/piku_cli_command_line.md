# Piku CLI command line reference
These are the help texts for each of the core Piku CLI commands. You can also see this text in your terminal with piku help, piku --help, or piku -h.

```
Usage: piku.py [OPTIONS] COMMAND [ARGS]...

  The smallest PaaS you've ever seen

Options:
  -h, --help  Show this message and exit.

Commands:
  apps          List apps, e.g.: piku apps
  config        Show config, e.g.: piku config <app>
  config:get    e.g.: piku config:get <app> FOO
  config:live   e.g.: piku config:live <app>
  config:set    e.g.: piku config:set <app> FOO=bar BAZ=quux
  config:unset  e.g.: piku config:unset <app> FOO
  deploy        e.g.: piku deploy <app>
  destroy       e.g.: piku destroy <app>
  help          display help for piku
  logs          Tail running logs, e.g: piku logs <app> [<process>]
  ps            Show process count, e.g: piku ps <app>
  ps:scale      e.g.: piku ps:scale <app> <proc>=<count>
  restart       Restart an app: piku restart <app>
  run           e.g.: piku run <app> ls -- -al
  setup         Initialize environment
  setup:ssh     Set up a new SSH key (use - for stdin)
  stop          Stop an app, e.g: piku stop <app>
```



## piku.py apps 
List apps hosted on piku. Running instances will show with an asterisk * 

```
Usage: piku.py apps

```

## piku.py config
Show app config key values

```
Usage: piku.py config <app>

```
Config are stored outside the application at `$ENV_ROOT/app/ENV`

## piku.py config:get
Returns the value of `FOO` if is a config key
```
Usage: piku.py config:get <app> FOO

```

## piku.py config:set
Store the pair `FOO=bar` config
```
Usage: piku.py config <app> FOO=bar

```

## piku.py config:unset
Remove the config key `FOO` at ENV file and deploy the app
```
Usage: piku.py config:unset <app> FOO

```

## piku.py config:live
Show config stored as LIVE configuration. That are created when application is spawned
```
Usage: piku.py config:live <app>

```
Config are stored outside the application at `$ENV_ROOT/app/LIVE_ENV`
Live config settings are loaded when executes `piku.py cmd`


## piku.py deploy
Fetch app from git repository, update submodoles and deploy it 
```
Usage: piku.py deploy <app>

```
If there is a `release` worker at `Procfile` will be executed before other workers.
This worker it's used to make stuff to success the starting up.


## piku.py destroy
Remove application, and associated files
```
Usage: piku.py destroy <app>

```

## piku.py logs
Tail all app logs
```
Usage: piku.py logs <app>

```

## piku.py ps
Show workers process count

```
Usage: piku.py ps <app>

```

## piku.py ps:scale
Adjust the workers process number and deploy the app

```
Usage: piku.py ps:scale <app> WORKER=count

```

## piku.py run
Executes a command at app space piku run <app> ls -- -al

```
Usage: piku.py run <app> command [-- -arguemnt]

```
Command arguments must be passed before a double dash '--', e.g.:
`piku run <app> ls -- -al`

## piku.py restart
Stop and start app
```
Usage: piku.py restart <app>

```

## piku.py setup
Creates all needed files and directories to host the app
```
Usage: piku.py setup <app>

```

## piku.py setup:ssh
Add an uploaded ssh credetials to access to manage piku
```
Usage: piku.py setup:ssh (ssh_key_filename |- ssh_key )

```
The ssh_key_filename must be a server path filename
Optionally a key can be passed as an argument. e.g. `piku.py setup:ssh - $(cat ~/.ssh/id_rsa.pub)`

## piku.py stop
Stop an app
```
Usage: piku.py stop <app>

```

