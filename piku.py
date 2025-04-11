#!/usr/bin/env python3

"Piku Micro-PaaS"

try:
    from sys import version_info
    assert version_info >= (3, 8)
except AssertionError:
    exit("Piku requires Python 3.8 or above")

from importlib import import_module
from collections import defaultdict, deque
from fcntl import fcntl, F_SETFL, F_GETFL
from glob import glob
from json import loads
from multiprocessing import cpu_count
from os import chmod, getgid, getuid, symlink, unlink, remove, stat, listdir, environ, makedirs, O_NONBLOCK
from os.path import abspath, basename, dirname, exists, getmtime, join, realpath, splitext, isdir
from pwd import getpwuid
from grp import getgrgid
from re import sub, match
from shlex import split as shsplit
from shutil import copyfile, rmtree, which
from socket import socket, AF_INET, SOCK_STREAM
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import call, check_output, Popen, STDOUT
from sys import argv, stdin, stdout, stderr, version_info, exit, path as sys_path
from tempfile import NamedTemporaryFile
from time import sleep
from traceback import format_exc
from urllib.request import urlopen

from click import argument, group, secho as echo, pass_context, CommandCollection

# === Make sure we can access all system and user binaries ===

if 'sbin' not in environ['PATH']:
    environ['PATH'] = "/usr/local/sbin:/usr/sbin:/sbin:" + environ['PATH']
if '.local' not in environ['PATH']:
    environ['PATH'] = environ['HOME'] + "/.local/bin:" + environ['PATH']

# === Globals - all tweakable settings are here ===

PIKU_RAW_SOURCE_URL = "https://raw.githubusercontent.com/piku/piku/master/piku.py"
PIKU_ROOT = environ.get('PIKU_ROOT', join(environ['HOME'], '.piku'))
PIKU_BIN = join(environ['HOME'], 'bin')
PIKU_SCRIPT = realpath(__file__)
PIKU_PLUGIN_ROOT = abspath(join(PIKU_ROOT, "plugins"))
APP_ROOT = abspath(join(PIKU_ROOT, "apps"))
DATA_ROOT = abspath(join(PIKU_ROOT, "data"))
ENV_ROOT = abspath(join(PIKU_ROOT, "envs"))
GIT_ROOT = abspath(join(PIKU_ROOT, "repos"))
LOG_ROOT = abspath(join(PIKU_ROOT, "logs"))
NGINX_ROOT = abspath(join(PIKU_ROOT, "nginx"))
CACHE_ROOT = abspath(join(PIKU_ROOT, "cache"))
UWSGI_AVAILABLE = abspath(join(PIKU_ROOT, "uwsgi-available"))
UWSGI_ENABLED = abspath(join(PIKU_ROOT, "uwsgi-enabled"))
UWSGI_ROOT = abspath(join(PIKU_ROOT, "uwsgi"))
UWSGI_LOG_MAXSIZE = '1048576'
ACME_ROOT = environ.get('ACME_ROOT', join(environ['HOME'], '.acme.sh'))
ACME_WWW = abspath(join(PIKU_ROOT, "acme"))
ACME_ROOT_CA = environ.get('ACME_ROOT_CA', 'letsencrypt.org')

# === Make sure we can access piku user-installed binaries === #

if PIKU_BIN not in environ['PATH']:
    environ['PATH'] = PIKU_BIN + ":" + environ['PATH']

# pylint: disable=anomalous-backslash-in-string
NGINX_TEMPLATE = """
$PIKU_INTERNAL_PROXY_CACHE_PATH
upstream $APP {
  server $NGINX_SOCKET;
}
server {
  listen              $NGINX_IPV6_ADDRESS:80;
  listen              $NGINX_IPV4_ADDRESS:80;

  location ^~ /.well-known/acme-challenge {
    allow all;
    root ${ACME_WWW};
  }
$PIKU_INTERNAL_NGINX_COMMON
}
"""

NGINX_HTTPS_ONLY_TEMPLATE = """
$PIKU_INTERNAL_PROXY_CACHE_PATH
upstream $APP {
  server $NGINX_SOCKET;
}
server {
  listen              $NGINX_IPV6_ADDRESS:80;
  listen              $NGINX_IPV4_ADDRESS:80;
  server_name         $NGINX_SERVER_NAME;

  location ^~ /.well-known/acme-challenge {
    allow all;
    root ${ACME_WWW};
  }

  location / {
    return 301 https://$server_name$request_uri;
  }
}

server {
$PIKU_INTERNAL_NGINX_COMMON
}
"""
# pylint: enable=anomalous-backslash-in-string

NGINX_COMMON_FRAGMENT = r"""
  listen              $NGINX_IPV6_ADDRESS:$NGINX_SSL;
  listen              $NGINX_IPV4_ADDRESS:$NGINX_SSL;
  ssl_certificate     $NGINX_ROOT/$APP.crt;
  ssl_certificate_key $NGINX_ROOT/$APP.key;
  server_name         $NGINX_SERVER_NAME;
  # These are not required under systemd - enable for debugging only
  # access_log        $LOG_ROOT/$APP/access.log;
  # error_log         $LOG_ROOT/$APP/error.log;

  # Enable gzip compression
  gzip on;
  gzip_proxied any;
  gzip_types text/plain text/xml text/css text/javascript text/js application/x-javascript application/javascript application/json application/xml+rss application/atom+xml image/svg+xml;
  gzip_comp_level 7;
  gzip_min_length 2048;
  gzip_vary on;
  gzip_disable "MSIE [1-6]\.(?!.*SV1)";
  # set a custom header for requests
  add_header X-Deployed-By Piku;

  $PIKU_INTERNAL_NGINX_CUSTOM_CLAUSES
  $PIKU_INTERNAL_NGINX_STATIC_MAPPINGS
  $PIKU_INTERNAL_NGINX_CACHE_MAPPINGS
  $PIKU_INTERNAL_NGINX_BLOCK_GIT
  $PIKU_INTERNAL_NGINX_PORTMAP
"""

NGINX_PORTMAP_FRAGMENT = """
  location    / {
    $PIKU_INTERNAL_NGINX_UWSGI_SETTINGS
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Remote-Address $remote_addr;
    proxy_set_header X-Forwarded-Port $server_port;
    proxy_set_header X-Request-Start $msec;
    $NGINX_ACL
  }
"""

NGINX_ACME_FIRSTRUN_TEMPLATE = """
server {
  listen              $NGINX_IPV6_ADDRESS:80;
  listen              $NGINX_IPV4_ADDRESS:80;
  server_name         $NGINX_SERVER_NAME;
  location ^~ /.well-known/acme-challenge {
    allow all;
    root ${ACME_WWW};
  }
}
"""

PIKU_INTERNAL_NGINX_STATIC_MAPPING = """
  location $static_url {
      sendfile on;
      sendfile_max_chunk 1m;
      tcp_nopush on;
      directio 8m;
      aio threads;
      alias $static_path;
      try_files $uri $uri.html $uri/ $catch_all =404;
  }
"""

PIKU_INTERNAL_PROXY_CACHE_PATH = """
uwsgi_cache_path $cache_path levels=1:2 keys_zone=$app:20m inactive=$cache_time_expiry max_size=$cache_size use_temp_path=off;
"""

PIKU_INTERNAL_NGINX_CACHE_MAPPING = """
    location ~* ^/($cache_prefixes) {
        uwsgi_cache $APP;
        uwsgi_cache_min_uses 1;
        uwsgi_cache_key $host$request_uri;
        uwsgi_cache_valid 200 304 $cache_time_content;
        uwsgi_cache_valid 301 307 $cache_time_redirects;
        uwsgi_cache_valid 500 502 503 504 0s;
        uwsgi_cache_valid any $cache_time_any;
        uwsgi_hide_header Cache-Control;
        add_header Cache-Control "public, max-age=$cache_time_control";
        add_header X-Cache $upstream_cache_status;
        $PIKU_INTERNAL_NGINX_UWSGI_SETTINGS
    }
"""

PIKU_INTERNAL_NGINX_UWSGI_SETTINGS = """
    uwsgi_pass $APP;
    uwsgi_param QUERY_STRING $query_string;
    uwsgi_param REQUEST_METHOD $request_method;
    uwsgi_param CONTENT_TYPE $content_type;
    uwsgi_param CONTENT_LENGTH $content_length;
    uwsgi_param REQUEST_URI $request_uri;
    uwsgi_param PATH_INFO $document_uri;
    uwsgi_param DOCUMENT_ROOT $document_root;
    uwsgi_param SERVER_PROTOCOL $server_protocol;
    uwsgi_param X_FORWARDED_FOR $proxy_add_x_forwarded_for;
    uwsgi_param REMOTE_ADDR $remote_addr;
    uwsgi_param REMOTE_PORT $remote_port;
    uwsgi_param SERVER_ADDR $server_addr;
    uwsgi_param SERVER_PORT $server_port;
    uwsgi_param SERVER_NAME $server_name;
"""

CRON_REGEXP = r"^((?:(?:\*\/)?\d+)|\*) ((?:(?:\*\/)?\d+)|\*) ((?:(?:\*\/)?\d+)|\*) ((?:(?:\*\/)?\d+)|\*) ((?:(?:\*\/)?\d+)|\*) (.*)$"

# === Utility functions ===


def sanitize_app_name(app):
    """Sanitize the app name and build matching path"""

    app = "".join(c for c in app if c.isalnum() or c in ('.', '_', '-')).rstrip().lstrip('/')
    return app


def exit_if_invalid(app):
    """Utility function for error checking upon command startup."""

    app = sanitize_app_name(app)
    if not exists(join(APP_ROOT, app)):
        echo("Error: app '{}' not found.".format(app), fg='red')
        exit(1)
    return app


def get_free_port(address=""):
    """Find a free TCP port (entirely at random)"""

    s = socket(AF_INET, SOCK_STREAM)
    s.bind((address, 0))  # lgtm [py/bind-socket-all-network-interfaces]
    port = s.getsockname()[1]
    s.close()
    return port


def get_boolean(value):
    """Convert a boolean-ish string to a boolean."""

    return value.lower() in ['1', 'on', 'true', 'enabled', 'yes', 'y']


def write_config(filename, bag, separator='='):
    """Helper for writing out config files"""

    with open(filename, 'w') as h:
        # pylint: disable=unused-variable
        for k, v in bag.items():
            h.write('{k:s}{separator:s}{v}\n'.format(**locals()))


def setup_authorized_keys(ssh_fingerprint, script_path, pubkey):
    """Sets up an authorized_keys file to redirect SSH commands"""

    authorized_keys = join(environ['HOME'], '.ssh', 'authorized_keys')
    if not exists(dirname(authorized_keys)):
        makedirs(dirname(authorized_keys))
    # Restrict features and force all SSH commands to go through our script
    with open(authorized_keys, 'a') as h:
        h.write("""command="FINGERPRINT={ssh_fingerprint:s} NAME=default {script_path:s} $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding {pubkey:s}\n""".format(**locals()))
    chmod(dirname(authorized_keys), S_IRUSR | S_IWUSR | S_IXUSR)
    chmod(authorized_keys, S_IRUSR | S_IWUSR)


def parse_procfile(filename):
    """Parses a Procfile and returns the worker types. Only one worker of each type is allowed."""

    workers = {}
    if not exists(filename):
        return None

    with open(filename, 'r') as procfile:
        for line_number, line in enumerate(procfile):
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            try:
                kind, command = map(lambda x: x.strip(), line.split(":", 1))
                # Check for cron patterns
                if kind.startswith("cron"):
                    limits = [59, 24, 31, 12, 7]
                    res = match(CRON_REGEXP, command)
                    if res:
                        matches = res.groups()
                        for i in range(len(limits)):
                            if int(matches[i].replace("*/", "").replace("*", "1")) > limits[i]:
                                raise ValueError
                workers[kind] = command
            except Exception:
                echo("Warning: misformatted Procfile entry '{}' at line {}".format(line, line_number), fg='yellow')
    if len(workers) == 0:
        return {}
    # WSGI trumps regular web workers
    if 'wsgi' in workers or 'jwsgi' in workers or 'rwsgi' in workers:
        if 'web' in workers:
            echo("Warning: found both 'wsgi' and 'web' workers, disabling 'web'", fg='yellow')
            del workers['web']
    return workers


def expandvars(buffer, env, default=None, skip_escaped=False):
    """expand shell-style environment variables in a buffer"""

    def replace_var(match):
        return env.get(match.group(2) or match.group(1), match.group(0) if default is None else default)

    pattern = (r'(?<!\\)' if skip_escaped else '') + r'\$(\w+|\{([^}]*)\})'
    return sub(pattern, replace_var, buffer)


def command_output(cmd):
    """executes a command and grabs its output, if any"""
    try:
        env = environ
        return str(check_output(cmd, stderr=STDOUT, env=env, shell=True))
    except Exception:
        return ""


def parse_settings(filename, env={}):
    """Parses a settings file and returns a dict with environment variables"""

    if not exists(filename):
        return {}

    with open(filename, 'r') as settings:
        for line in settings:
            if line[0] == '#' or len(line.strip()) == 0:  # ignore comments and newlines
                continue
            try:
                k, v = map(lambda x: x.strip(), line.split("=", 1))
                env[k] = expandvars(v, env)
            except Exception:
                echo("Error: malformed setting '{}', ignoring file.".format(line), fg='red')
                return {}
    return env


def check_requirements(binaries):
    """Checks if all the binaries exist and are executable"""

    echo("-----> Checking requirements: {}".format(binaries), fg='green')
    requirements = list(map(which, binaries))
    echo(str(requirements))

    if None in requirements:
        return False
    return True


def found_app(kind):
    """Helper function to output app detected"""
    echo("-----> {} app detected.".format(kind), fg='green')
    return True


def do_deploy(app, deltas={}, newrev=None):
    """Deploy an app by resetting the work directory"""

    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    log_path = join(LOG_ROOT, app)

    env = {'GIT_WORK_DIR': app_path}
    if exists(app_path):
        echo("-----> Deploying app '{}'".format(app), fg='green')
        call('git fetch --quiet', cwd=app_path, env=env, shell=True)
        if newrev:
            call('git reset --hard {}'.format(newrev), cwd=app_path, env=env, shell=True)
        call('git submodule init', cwd=app_path, env=env, shell=True)
        call('git submodule update', cwd=app_path, env=env, shell=True)
        if not exists(log_path):
            makedirs(log_path)
        workers = parse_procfile(procfile)
        if workers and len(workers) > 0:
            settings = {}
            if "preflight" in workers:
                echo("-----> Running preflight.", fg='green')
                retval = call(workers["preflight"], cwd=app_path, env=settings, shell=True)
                if retval:
                    echo("-----> Exiting due to preflight command error value: {}".format(retval))
                    exit(retval)
                workers.pop("preflight", None)
            if exists(join(app_path, 'requirements.txt')) and found_app("Python"):
                settings.update(deploy_python(app, deltas))
            elif exists(join(app_path, 'pyproject.toml')) and which('poetry') and found_app("Python"):
                settings.update(deploy_python_with_poetry(app, deltas))
            elif exists(join(app_path, 'pyproject.toml')) and which('uv') and found_app("Python (uv)"):
                settings.update(deploy_python_with_uv(app, deltas))
            elif exists(join(app_path, 'Gemfile')) and found_app("Ruby Application") and check_requirements(['ruby', 'gem', 'bundle']):
                settings.update(deploy_ruby(app, deltas))
            elif exists(join(app_path, 'package.json')) and found_app("Node") and (
                    check_requirements(['nodejs', 'npm']) or check_requirements(['node', 'npm']) or check_requirements(['nodeenv'])):
                settings.update(deploy_node(app, deltas))
            elif exists(join(app_path, 'pom.xml')) and found_app("Java Maven") and check_requirements(['java', 'mvn']):
                settings.update(deploy_java_maven(app, deltas))
            elif exists(join(app_path, 'build.gradle')) and found_app("Java Gradle") and check_requirements(['java', 'gradle']):
                settings.update(deploy_java_gradle(app, deltas))
            elif (exists(join(app_path, 'Godeps')) or exists(join(app_path, 'go.mod')) or len(glob(join(app_path, '*.go')))) and found_app("Go") and check_requirements(['go']):
                settings.update(deploy_go(app, deltas))
            elif exists(join(app_path, 'deps.edn')) and found_app("Clojure CLI") and check_requirements(['java', 'clojure']):
                settings.update(deploy_clojure_cli(app, deltas))
            elif exists(join(app_path, 'project.clj')) and found_app("Clojure Lein") and check_requirements(['java', 'lein']):
                settings.update(deploy_clojure_leiningen(app, deltas))
            elif 'php' in workers:
                if check_requirements(['uwsgi_php']):
                    echo("-----> PHP app detected.", fg='green')
                    settings.update(deploy_identity(app, deltas))
                else:
                    echo("-----> PHP app detected but uwsgi-plugin-php was not found", fg='red')
            elif exists(join(app_path, 'Cargo.toml')) and exists(join(app_path, 'rust-toolchain.toml')) and found_app("Rust") and check_requirements(['rustc', 'cargo']):
                settings.update(deploy_rust(app, deltas))
            elif 'release' in workers and 'web' in workers:
                echo("-----> Generic app detected.", fg='green')
                settings.update(deploy_identity(app, deltas))
            elif 'static' in workers:
                echo("-----> Static app detected.", fg='green')
                settings.update(deploy_identity(app, deltas))
            else:
                echo("-----> Could not detect runtime!", fg='red')
            # TODO: detect other runtimes
            if "release" in workers:
                echo("-----> Releasing", fg='green')
                retval = call(workers["release"], cwd=app_path, env=settings, shell=True)
                if retval:
                    echo("-----> Exiting due to release command error value: {}".format(retval))
                    exit(retval)
                workers.pop("release", None)
        else:
            echo("Error: Invalid Procfile for app '{}'.".format(app), fg='red')
    else:
        echo("Error: app '{}' not found.".format(app), fg='red')


def deploy_java_gradle(app, deltas={}):
    """Deploy a Java application using Gradle"""
    java_path = join(ENV_ROOT, app)
    build_path = join(APP_ROOT, app, 'build')
    env_file = join(APP_ROOT, app, 'ENV')

    env = {
        'VIRTUAL_ENV': java_path,
        "PATH": ':'.join([join(java_path, "bin"), join(app, ".bin"), environ['PATH']])
    }

    if exists(env_file):
        env.update(parse_settings(env_file, env))

    if not exists(java_path):
        makedirs(java_path)

    if not exists(build_path):
        echo("-----> Building Java Application")
        call('gradle build', cwd=join(APP_ROOT, app), env=env, shell=True)

    else:
        echo("-----> Removing previous builds")
        echo("-----> Rebuilding Java Application")
        call('gradle clean build', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_java_maven(app, deltas={}):
    """Deploy a Java application using Maven"""
    # TODO: Use jenv to isolate Java Application environments

    java_path = join(ENV_ROOT, app)
    target_path = join(APP_ROOT, app, 'target')
    env_file = join(APP_ROOT, app, 'ENV')

    env = {
        'VIRTUAL_ENV': java_path,
        "PATH": ':'.join([join(java_path, "bin"), join(app, ".bin"), environ['PATH']])
    }

    if exists(env_file):
        env.update(parse_settings(env_file, env))

    if not exists(java_path):
        makedirs(java_path)

    if not exists(target_path):
        echo("-----> Building Java Application")
        call('mvn package', cwd=join(APP_ROOT, app), env=env, shell=True)

    else:
        echo("-----> Removing previous builds")
        echo("-----> Rebuilding Java Application")
        call('mvn clean package', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_clojure_cli(app, deltas={}):
    """Deploy a Clojure Application"""

    virtual = join(ENV_ROOT, app)
    target_path = join(APP_ROOT, app, 'target')
    env_file = join(APP_ROOT, app, 'ENV')

    if not exists(target_path):
        makedirs(virtual)
    env = {
        'VIRTUAL_ENV': virtual,
        "PATH": ':'.join([join(virtual, "bin"), join(app, ".bin"), environ['PATH']]),
        "CLJ_CONFIG": environ.get('CLJ_CONFIG', join(environ['HOME'], '.clojure')),
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))
    echo("-----> Building Clojure Application")
    call('clojure -T:build release', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_clojure_leiningen(app, deltas={}):
    """Deploy a Clojure Application"""

    virtual = join(ENV_ROOT, app)
    target_path = join(APP_ROOT, app, 'target')
    env_file = join(APP_ROOT, app, 'ENV')

    if not exists(target_path):
        makedirs(virtual)
    env = {
        'VIRTUAL_ENV': virtual,
        "PATH": ':'.join([join(virtual, "bin"), join(app, ".bin"), environ['PATH']]),
        "LEIN_HOME": environ.get('LEIN_HOME', join(environ['HOME'], '.lein')),
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))
    echo("-----> Building Clojure Application")
    call('lein clean', cwd=join(APP_ROOT, app), env=env, shell=True)
    call('lein uberjar', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_ruby(app, deltas={}):
    """Deploy a Ruby Application"""

    virtual = join(ENV_ROOT, app)
    env_file = join(APP_ROOT, app, 'ENV')

    env = {
        'VIRTUAL_ENV': virtual,
        "PATH": ':'.join([join(virtual, "bin"), join(app, ".bin"), environ['PATH']]),
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    if not exists(virtual):
        echo("-----> Building Ruby Application")
        makedirs(virtual)
        call('bundle config set --local path $VIRTUAL_ENV', cwd=join(APP_ROOT, app), env=env, shell=True)
    else:
        echo("------> Rebuilding Ruby Application")

    call('bundle install', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_go(app, deltas={}):
    """Deploy a Go application"""

    go_path = join(ENV_ROOT, app)
    deps = join(APP_ROOT, app, 'Godeps')
    go_mod = join(APP_ROOT, app, 'go.mod')

    first_time = False
    if not exists(go_path):
        echo("-----> Creating GOPATH for '{}'".format(app), fg='green')
        makedirs(go_path)
        # copy across a pre-built GOPATH to save provisioning time
        call('cp -a $HOME/gopath {}'.format(app), cwd=ENV_ROOT, shell=True)
        first_time = True

    if exists(deps):
        if first_time or getmtime(deps) > getmtime(go_path):
            echo("-----> Running godep for '{}'".format(app), fg='green')
            env = {
                'GOPATH': '$HOME/gopath',
                'GOROOT': '$HOME/go',
                'PATH': '$PATH:$HOME/go/bin',
                'GO15VENDOREXPERIMENT': '1'
            }
            call('godep update ...', cwd=join(APP_ROOT, app), env=env, shell=True)

    if exists(go_mod):
        echo("-----> Running go mod tidy for '{}'".format(app), fg='green')
        call('go mod tidy', cwd=join(APP_ROOT, app), shell=True)

    return spawn_app(app, deltas)


def deploy_rust(app, deltas={}):
    """Deploy a Rust application"""

    app_path = join(APP_ROOT, app)
    echo("-----> Running cargo build for '{}'".format(app), fg='green')
    call('cargo build', cwd=app_path, shell=True)
    return spawn_app(app, deltas)


def deploy_node(app, deltas={}):
    """Deploy a Node application"""

    virtualenv_path = join(ENV_ROOT, app)
    node_path = join(ENV_ROOT, app, "node_modules")
    node_modules_symlink = join(APP_ROOT, app, "node_modules")
    npm_prefix = abspath(join(node_path, ".."))
    env_file = join(APP_ROOT, app, 'ENV')
    deps = join(APP_ROOT, app, 'package.json')

    first_time = False
    if not exists(node_path):
        echo("-----> Creating node_modules for '{}'".format(app), fg='green')
        makedirs(node_path)
        first_time = True

    env = {
        'VIRTUAL_ENV': virtualenv_path,
        'NODE_PATH': node_path,
        'NPM_CONFIG_PREFIX': npm_prefix,
        "PATH": ':'.join([join(virtualenv_path, "bin"), join(node_path, ".bin"), environ['PATH']])
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    package_manager_command = env.get("NODE_PACKAGE_MANAGER", "npm --package-lock=false")
    package_manager = package_manager_command.split(" ")[0]

    # include node binaries on our path
    environ["PATH"] = env["PATH"]

    version = env.get("NODE_VERSION")
    node_binary = join(virtualenv_path, "bin", "node")
    installed = check_output("{} -v".format(node_binary), cwd=join(APP_ROOT, app), env=env, shell=True).decode("utf8").rstrip(
        "\n") if exists(node_binary) else ""

    if version and check_requirements(['nodeenv']):
        if not installed.endswith(version):
            started = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))
            if installed and len(started):
                echo("Warning: Can't update node with app running. Stop the app & retry.", fg='yellow')
            else:
                echo("-----> Installing node version '{NODE_VERSION:s}' using nodeenv".format(**env), fg='green')
                call("nodeenv --prebuilt --node={NODE_VERSION:s} --clean-src --force {VIRTUAL_ENV:s}".format(**env),
                     cwd=virtualenv_path, env=env, shell=True)
        else:
            echo("-----> Node is installed at {}.".format(version))

    if exists(deps) and check_requirements(['npm']):
        if first_time or getmtime(deps) > getmtime(node_path):
            copyfile(join(APP_ROOT, app, 'package.json'), join(ENV_ROOT, app, 'package.json'))
            if not exists(node_modules_symlink):
                symlink(node_path, node_modules_symlink)
            if package_manager != "npm":
                echo("-----> Installing package manager {} with npm".format(package_manager))
                call("npm install -g {}".format(package_manager), cwd=join(APP_ROOT, app), env=env, shell=True)
            echo("-----> Running {} for '{}'".format(package_manager_command, app), fg='green')
            call('{} install --prefix {}'.format(package_manager_command, npm_prefix), cwd=join(APP_ROOT, app), env=env, shell=True)
    return spawn_app(app, deltas)


def deploy_python(app, deltas={}):
    """Deploy a Python application"""

    virtualenv_path = join(ENV_ROOT, app)
    requirements = join(APP_ROOT, app, 'requirements.txt')
    env_file = join(APP_ROOT, app, 'ENV')
    # Set unbuffered output and readable UTF-8 mapping
    env = {
        'PYTHONUNBUFFERED': '1',
        'PYTHONIOENCODING': 'UTF_8:replace'
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    # TODO: improve version parsing
    # pylint: disable=unused-variable
    version = int(env.get("PYTHON_VERSION", "3"))

    first_time = False
    if not exists(join(virtualenv_path, "bin", "activate")):
        echo("-----> Creating virtualenv for '{}'".format(app), fg='green')
        try:
            makedirs(virtualenv_path)
        except FileExistsError:
            echo("-----> Env dir already exists: '{}'".format(app), fg='yellow')
        call('virtualenv --python=python{version:d} {app:s}'.format(**locals()), cwd=ENV_ROOT, shell=True)
        first_time = True

    activation_script = join(virtualenv_path, 'bin', 'activate_this.py')
    exec(open(activation_script).read(), dict(__file__=activation_script))

    if first_time or getmtime(requirements) > getmtime(virtualenv_path):
        echo("-----> Running pip for '{}'".format(app), fg='green')
        call('pip install -r {}'.format(requirements), cwd=virtualenv_path, shell=True)
    return spawn_app(app, deltas)


def deploy_python_with_poetry(app, deltas={}):
    """Deploy a Python application using Poetry"""

    echo("=====> Starting EXPERIMENTAL poetry deployment for '{}'".format(app), fg='red')
    virtualenv_path = join(ENV_ROOT, app)
    requirements = join(APP_ROOT, app, 'pyproject.toml')
    env_file = join(APP_ROOT, app, 'ENV')
    symlink_path = join(APP_ROOT, app, '.venv')
    if not exists(symlink_path):
        echo("-----> Creating .venv symlink '{}'".format(app), fg='green')
        symlink(virtualenv_path, symlink_path, target_is_directory=True)
    # Set unbuffered output and readable UTF-8 mapping
    env = {
        **environ,
        'POETRY_VIRTUALENVS_IN_PROJECT': '1',
        'PYTHONUNBUFFERED': '1',
        'PYTHONIOENCODING': 'UTF_8:replace'
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    first_time = False
    if not exists(join(virtualenv_path, "bin", "activate")):
        echo("-----> Creating virtualenv for '{}'".format(app), fg='green')
        try:
            makedirs(virtualenv_path)
        except FileExistsError:
            echo("-----> Env dir already exists: '{}'".format(app), fg='yellow')
        first_time = True

    if first_time or getmtime(requirements) > getmtime(virtualenv_path):
        echo("-----> Running poetry for '{}'".format(app), fg='green')
        call('poetry install', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_python_with_uv(app, deltas={}):
    """Deploy a Python application using Astral uv"""

    echo("=====> Starting EXPERIMENTAL uv deployment for '{}'".format(app), fg='red')
    env_file = join(APP_ROOT, app, 'ENV')
    virtualenv_path = join(ENV_ROOT, app)
    # Set unbuffered output and readable UTF-8 mapping
    env = {
        **environ,
        'PYTHONUNBUFFERED': '1',
        'PYTHONIOENCODING': 'UTF_8:replace',
        'UV_PROJECT_ENVIRONMENT': virtualenv_path
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    echo("-----> Calling uv sync", fg='green')
    call('uv sync --python-preference only-system', cwd=join(APP_ROOT, app), env=env, shell=True)

    return spawn_app(app, deltas)


def deploy_identity(app, deltas={}):
    env_path = join(ENV_ROOT, app)
    if not exists(env_path):
        makedirs(env_path)
    return spawn_app(app, deltas)


def spawn_app(app, deltas={}):
    """Create all workers for an app"""

    # pylint: disable=unused-variable
    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    workers = parse_procfile(procfile)
    workers.pop("preflight", None)
    workers.pop("release", None)
    ordinals = defaultdict(lambda: 1)
    worker_count = {k: 1 for k in workers.keys()}

    # the Python virtualenv
    virtualenv_path = join(ENV_ROOT, app)
    # Settings shipped with the app
    env_file = join(APP_ROOT, app, 'ENV')
    # Custom overrides
    settings = join(ENV_ROOT, app, 'ENV')
    # Live settings
    live = join(ENV_ROOT, app, 'LIVE_ENV')
    # Scaling
    scaling = join(ENV_ROOT, app, 'SCALING')

    # Bootstrap environment
    env = {
        'APP': app,
        'LOG_ROOT': LOG_ROOT,
        'DATA_ROOT': join(DATA_ROOT, app),
        'HOME': environ['HOME'],
        'USER': environ['USER'],
        'PATH': ':'.join([join(virtualenv_path, 'bin'), environ['PATH']]),
        'PWD': dirname(env_file),
        'VIRTUAL_ENV': virtualenv_path,
    }

    safe_defaults = {
        'NGINX_IPV4_ADDRESS': '0.0.0.0',
        'NGINX_IPV6_ADDRESS': '[::]',
        'BIND_ADDRESS': '127.0.0.1',
    }

    # add node path if present
    node_path = join(virtualenv_path, "node_modules")
    if exists(node_path):
        env["NODE_PATH"] = node_path
        env["PATH"] = ':'.join([join(node_path, ".bin"), env['PATH']])

    # Load environment variables shipped with repo (if any)
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    # Override with custom settings (if any)
    if exists(settings):
        env.update(parse_settings(settings, env))  # lgtm [py/modification-of-default-value]

    if 'web' in workers or 'wsgi' in workers or 'jwsgi' in workers or 'static' in workers or 'rwsgi' in workers or 'php' in workers:
        # Pick a port if none defined
        if 'PORT' not in env:
            env['PORT'] = str(get_free_port())
            echo("-----> picking free port {PORT}".format(**env))

        if get_boolean(env.get('DISABLE_IPV6', 'false')):
            safe_defaults.pop('NGINX_IPV6_ADDRESS', None)
            echo("-----> nginx will NOT use IPv6".format(**locals()))

        # Safe defaults for addressing
        for k, v in safe_defaults.items():
            if k not in env:
                echo("-----> nginx {k:s} will be set to {v}".format(**locals()))
                env[k] = v

        # Set up nginx if we have NGINX_SERVER_NAME set
        if 'NGINX_SERVER_NAME' in env:
            # Hack to get around ClickCommand
            env['NGINX_SERVER_NAME'] = env['NGINX_SERVER_NAME'].split(',')
            env['NGINX_SERVER_NAME'] = ' '.join(env['NGINX_SERVER_NAME'])

            nginx = command_output("nginx -V")
            nginx_ssl = "443 ssl"
            if "--with-http_v2_module" in nginx:
                nginx_ssl += " http2"
            elif "--with-http_spdy_module" in nginx and "nginx/1.6.2" not in nginx:  # avoid Raspbian bug
                nginx_ssl += " spdy"
            nginx_conf = join(NGINX_ROOT, "{}.conf".format(app))

            env.update({  # lgtm [py/modification-of-default-value]
                'NGINX_SSL': nginx_ssl,
                'NGINX_ROOT': NGINX_ROOT,
                'ACME_WWW': ACME_WWW,
            })

            # default to reverse proxying to the TCP port we picked
            env['PIKU_INTERNAL_NGINX_UWSGI_SETTINGS'] = 'proxy_pass http://{BIND_ADDRESS:s}:{PORT:s};'.format(**env)
            if 'wsgi' in workers or 'jwsgi' in workers:
                sock = join(NGINX_ROOT, "{}.sock".format(app))
                env['PIKU_INTERNAL_NGINX_UWSGI_SETTINGS'] = expandvars(PIKU_INTERNAL_NGINX_UWSGI_SETTINGS, env)
                env['NGINX_SOCKET'] = env['BIND_ADDRESS'] = "unix://" + sock
                if 'PORT' in env:
                    del env['PORT']
            else:
                env['NGINX_SOCKET'] = "{BIND_ADDRESS:s}:{PORT:s}".format(**env)
                echo("-----> nginx will look for app '{}' on {}".format(app, env['NGINX_SOCKET']))

            domains = env['NGINX_SERVER_NAME'].split()
            domain = domains[0]
            issuefile = join(ACME_ROOT, domain, "issued-" + "-".join(domains))
            key, crt = [join(NGINX_ROOT, "{}.{}".format(app, x)) for x in ['key', 'crt']]
            if exists(join(ACME_ROOT, "acme.sh")):
                acme = ACME_ROOT
                www = ACME_WWW
                root_ca = ACME_ROOT_CA
                # if this is the first run there will be no nginx conf yet
                # create a basic conf stub just to serve the acme auth
                if not exists(nginx_conf):
                    echo("-----> writing temporary nginx conf")
                    buffer = expandvars(NGINX_ACME_FIRSTRUN_TEMPLATE, env)
                    with open(nginx_conf, "w") as h:
                        h.write(buffer)
                if not exists(key) or not exists(issuefile):
                    echo("-----> getting letsencrypt certificate")
                    certlist = " ".join(["-d {}".format(d) for d in domains])
                    call('{acme:s}/acme.sh --issue {certlist:s} -w {www:s} --server {root_ca:s}'.format(**locals()), shell=True)
                    call('{acme:s}/acme.sh --install-cert {certlist:s} --key-file {key:s} --fullchain-file {crt:s}'.format(
                        **locals()), shell=True)
                    if exists(join(ACME_ROOT, domain)) and not exists(join(ACME_WWW, app)):
                        symlink(join(ACME_ROOT, domain), join(ACME_WWW, app))
                    try:
                        symlink("/dev/null", issuefile)
                    except Exception:
                        pass
                else:
                    echo("-----> letsencrypt certificate already installed")

            # fall back to creating self-signed certificate if acme failed
            if not exists(key) or stat(crt).st_size == 0:
                echo("-----> generating self-signed certificate")
                call(
                    'openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=US/ST=NY/L=New York/O=Piku/OU=Self-Signed/CN={domain:s}" -keyout {key:s} -out {crt:s}'.format(
                        **locals()), shell=True)

            # restrict access to server from CloudFlare IP addresses
            acl = []
            if get_boolean(env.get('NGINX_CLOUDFLARE_ACL', 'false')):
                try:
                    cf = loads(urlopen('https://api.cloudflare.com/client/v4/ips').read().decode("utf-8"))
                    if cf['success'] is True:
                        for i in cf['result']['ipv4_cidrs']:
                            acl.append("allow {};".format(i))
                        if get_boolean(env.get('DISABLE_IPV6', 'false')):
                            for i in cf['result']['ipv6_cidrs']:
                                acl.append("allow {};".format(i))
                        # allow access from controlling machine
                        if 'SSH_CLIENT' in environ:
                            remote_ip = environ['SSH_CLIENT'].split()[0]
                            echo("-----> nginx ACL will include your IP ({})".format(remote_ip))
                            acl.append("allow {};".format(remote_ip))
                        acl.extend(["allow 127.0.0.1;", "deny all;"])
                except Exception:
                    cf = defaultdict()
                    echo("-----> Could not retrieve CloudFlare IP ranges: {}".format(format_exc()), fg="red")

            env['NGINX_ACL'] = " ".join(acl)

            env['PIKU_INTERNAL_NGINX_BLOCK_GIT'] = "" if env.get('NGINX_ALLOW_GIT_FOLDERS') else r"location ~ /\.git { deny all; }"

            env['PIKU_INTERNAL_PROXY_CACHE_PATH'] = ''
            env['PIKU_INTERNAL_NGINX_CACHE_MAPPINGS'] = ''

            # Get a mapping of /prefix1,/prefix2
            default_cache_path = join(CACHE_ROOT, app)
            if not exists(default_cache_path):
                makedirs(default_cache_path)
            try:
                cache_size = int(env.get('NGINX_CACHE_SIZE', '1'))
            except Exception:
                echo("=====> Invalid cache size, defaulting to 1GB")
                cache_size = 1
            cache_size = str(cache_size) + "g"
            try:
                cache_time_control = int(env.get('NGINX_CACHE_CONTROL', '3600'))
            except Exception:
                echo("=====> Invalid time for cache control, defaulting to 3600s")
                cache_time_control = 3600
            cache_time_control = str(cache_time_control)
            try:
                cache_time_content = int(env.get('NGINX_CACHE_TIME', '3600'))
            except Exception:
                echo("=====> Invalid cache time for content, defaulting to 3600s")
                cache_time_content = 3600
            cache_time_content = str(cache_time_content) + "s"
            try:
                cache_time_redirects = int(env.get('NGINX_CACHE_REDIRECTS', '3600'))
            except Exception:
                echo("=====> Invalid cache time for redirects, defaulting to 3600s")
                cache_time_redirects = 3600
            cache_time_redirects = str(cache_time_redirects) + "s"
            try:
                cache_time_any = int(env.get('NGINX_CACHE_ANY', '3600'))
            except Exception:
                echo("=====> Invalid cache expiry fallback, defaulting to 3600s")
                cache_time_any = 3600
            cache_time_any = str(cache_time_any) + "s"
            try:
                cache_time_expiry = int(env.get('NGINX_CACHE_EXPIRY', '86400'))
            except Exception:
                echo("=====> Invalid cache expiry, defaulting to 86400s")
                cache_time_expiry = 86400
            cache_time_expiry = str(cache_time_expiry) + "s"
            cache_prefixes = env.get('NGINX_CACHE_PREFIXES', '')
            cache_path = env.get('NGINX_CACHE_PATH', default_cache_path)
            if not exists(cache_path):
                echo("=====> Cache path {} does not exist, using default {}, be aware of disk usage.".format(cache_path, default_cache_path))
                cache_path = env.get(default_cache_path)
            if len(cache_prefixes):
                prefixes = []  # this will turn into part of /(path1|path2|path3)
                try:
                    items = cache_prefixes.split(',')
                    for item in items:
                        if item[0] == '/':
                            prefixes.append(item[1:])
                        else:
                            prefixes.append(item)
                    cache_prefixes = "|".join(prefixes)
                    echo("-----> nginx will cache /({}) prefixes up to {} or {} of disk space, with the following timings:".format(cache_prefixes, cache_time_expiry, cache_size))
                    echo("-----> nginx will cache content for {}.".format(cache_time_content))
                    echo("-----> nginx will cache redirects for {}.".format(cache_time_redirects))
                    echo("-----> nginx will cache everything else for {}.".format(cache_time_any))
                    echo("-----> nginx will send caching headers asking for {} seconds of public caching.".format(cache_time_control))
                    env['PIKU_INTERNAL_PROXY_CACHE_PATH'] = expandvars(
                        PIKU_INTERNAL_PROXY_CACHE_PATH, locals())
                    env['PIKU_INTERNAL_NGINX_CACHE_MAPPINGS'] = expandvars(
                        PIKU_INTERNAL_NGINX_CACHE_MAPPING, locals())
                    env['PIKU_INTERNAL_NGINX_CACHE_MAPPINGS'] = expandvars(
                        env['PIKU_INTERNAL_NGINX_CACHE_MAPPINGS'], env)
                except Exception as e:
                    echo("Error {} in cache path spec: should be /prefix1:[,/prefix2], ignoring.".format(e))
                    env['PIKU_INTERNAL_NGINX_CACHE_MAPPINGS'] = ''

            env['PIKU_INTERNAL_NGINX_STATIC_MAPPINGS'] = ''

            # Get a mapping of /prefix1:path1,/prefix2:path2
            static_paths = env.get('NGINX_STATIC_PATHS', '')
            # prepend static worker path if present
            if 'static' in workers:
                stripped = workers['static'].strip("/").rstrip("/")
                static_paths = ("/" if stripped[0:1] == ":" else "/:") + (stripped if stripped else ".") + "/" + ("," if static_paths else "") + static_paths
            if len(static_paths):
                try:
                    # pylint: disable=unused-variable
                    catch_all = env.get('NGINX_CATCH_ALL', '')
                    items = static_paths.split(',')
                    for item in items:
                        static_url, static_path = item.split(':')
                        if static_path[0] != '/':
                            static_path = join(app_path, static_path).rstrip("/") + "/"
                        echo("-----> nginx will map {} to {}.".format(static_url, static_path))
                        env['PIKU_INTERNAL_NGINX_STATIC_MAPPINGS'] = env['PIKU_INTERNAL_NGINX_STATIC_MAPPINGS'] + expandvars(
                            PIKU_INTERNAL_NGINX_STATIC_MAPPING, locals())
                except Exception as e:
                    echo("Error {} in static path spec: should be /prefix1:path1[,/prefix2:path2], ignoring.".format(e))
                    env['PIKU_INTERNAL_NGINX_STATIC_MAPPINGS'] = ''

            env['PIKU_INTERNAL_NGINX_CUSTOM_CLAUSES'] = expandvars(open(join(app_path, env["NGINX_INCLUDE_FILE"])).read(), env) if env.get("NGINX_INCLUDE_FILE") else ""
            env['PIKU_INTERNAL_NGINX_PORTMAP'] = ""
            if 'web' in workers or 'wsgi' in workers or 'jwsgi' in workers or 'rwsgi' in workers or 'php' in workers:
                env['PIKU_INTERNAL_NGINX_PORTMAP'] = expandvars(NGINX_PORTMAP_FRAGMENT, env)
            env['PIKU_INTERNAL_NGINX_COMMON'] = expandvars(NGINX_COMMON_FRAGMENT, env)

            echo("-----> nginx will map app '{}' to hostname(s) '{}'".format(app, env['NGINX_SERVER_NAME']))
            if get_boolean(env.get('NGINX_HTTPS_ONLY', 'false')):
                buffer = expandvars(NGINX_HTTPS_ONLY_TEMPLATE, env)
                echo("-----> nginx will redirect all requests to hostname(s) '{}' to HTTPS".format(env['NGINX_SERVER_NAME']))
            else:
                buffer = expandvars(NGINX_TEMPLATE, env)

            # remove all references to IPv6 listeners (for enviroments where it's disabled)
            if get_boolean(env.get('DISABLE_IPV6', 'false')):
                buffer = '\n'.join([line for line in buffer.split('\n') if 'NGINX_IPV6' not in line])
            # change any unecessary uWSGI specific directives to standard proxy ones
            if 'wsgi' not in workers and 'jwsgi' not in workers:
                buffer = buffer.replace("uwsgi_", "proxy_")

            # map Cloudflare connecting IP to REMOTE_ADDR
            if get_boolean(env.get('NGINX_CLOUDFLARE_ACL', 'false')):
                buffer = buffer.replace("REMOTE_ADDR $remote_addr", "REMOTE_ADDR $http_cf_connecting_ip")

            with open(nginx_conf, "w") as h:
                h.write(buffer)
            # prevent broken config from breaking other deploys
            try:
                nginx_config_test = str(check_output(r"nginx -t 2>&1 | grep -E '{}\.conf:[0-9]+$'".format(app), env=environ, shell=True))
            except Exception:
                nginx_config_test = None
            if nginx_config_test:
                echo("Error: [nginx config] {}".format(nginx_config_test), fg='red')
                echo("Warning: removing broken nginx config.", fg='yellow')
                unlink(nginx_conf)

    # Configured worker count
    if exists(scaling):
        worker_count.update({k: int(v) for k, v in parse_procfile(scaling).items() if k in workers})

    to_create = {}
    to_destroy = {}
    for k, v in worker_count.items():
        to_create[k] = range(1, worker_count[k] + 1)
        if k in deltas and deltas[k]:
            to_create[k] = range(1, worker_count[k] + deltas[k] + 1)
            if deltas[k] < 0:
                to_destroy[k] = range(worker_count[k], worker_count[k] + deltas[k], -1)
            worker_count[k] = worker_count[k] + deltas[k]

    # Cleanup env
    for k, v in list(env.items()):
        if k.startswith('PIKU_INTERNAL_'):
            del env[k]

    # Save current settings
    write_config(live, env)
    write_config(scaling, worker_count, ':')

    if get_boolean(env.get('PIKU_AUTO_RESTART', 'true')):
        config = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))
        if len(config):
            echo("-----> Removing uwsgi configs to trigger auto-restart.")
            for c in config:
                remove(c)

    # Create new workers
    for k, v in to_create.items():
        for w in v:
            enabled = join(UWSGI_ENABLED, '{app:s}_{k:s}.{w:d}.ini'.format(**locals()))
            if not exists(enabled):
                echo("-----> spawning '{app:s}:{k:s}.{w:d}'".format(**locals()), fg='green')
                spawn_worker(app, k, workers[k], env, w)

    # Remove unnecessary workers (leave logfiles)
    for k, v in to_destroy.items():
        for w in v:  # lgtm [py/unused-loop-variable]
            enabled = join(UWSGI_ENABLED, '{app:s}_{k:s}.{w:d}.ini'.format(**locals()))
            if exists(enabled):
                echo("-----> terminating '{app:s}:{k:s}.{w:d}'".format(**locals()), fg='yellow')
                unlink(enabled)

    return env


def spawn_worker(app, kind, command, env, ordinal=1):
    """Set up and deploy a single worker of a given kind"""

    # pylint: disable=unused-variable
    env['PROC_TYPE'] = kind
    env_path = join(ENV_ROOT, app)
    available = join(UWSGI_AVAILABLE, '{app:s}_{kind:s}.{ordinal:d}.ini'.format(**locals()))
    enabled = join(UWSGI_ENABLED, '{app:s}_{kind:s}.{ordinal:d}.ini'.format(**locals()))
    log_file = join(LOG_ROOT, app, kind)

    settings = [
        ('chdir', join(APP_ROOT, app)),
        ('uid', getpwuid(getuid()).pw_name),
        ('gid', getgrgid(getgid()).gr_name),
        ('master', 'true'),
        ('project', app),
        ('max-requests', env.get('UWSGI_MAX_REQUESTS', '1024')),
        ('listen', env.get('UWSGI_LISTEN', '16')),
        ('processes', env.get('UWSGI_PROCESSES', '1')),
        ('procname-prefix', '{app:s}:{kind:s}:'.format(**locals())),
        ('enable-threads', env.get('UWSGI_ENABLE_THREADS', 'true').lower()),
        ('log-x-forwarded-for', env.get('UWSGI_LOG_X_FORWARDED_FOR', 'false').lower()),
        ('log-maxsize', env.get('UWSGI_LOG_MAXSIZE', UWSGI_LOG_MAXSIZE)),
        ('logfile-chown', '%s:%s' % (getpwuid(getuid()).pw_name, getgrgid(getgid()).gr_name)),
        ('logfile-chmod', '640'),
        ('logto2', '{log_file:s}.{ordinal:d}.log'.format(**locals())),
        ('log-backupname', '{log_file:s}.{ordinal:d}.log.old'.format(**locals())),
    ]

    # only add virtualenv to uwsgi if it's a real virtualenv
    if exists(join(env_path, "bin", "activate_this.py")):
        settings.append(('virtualenv', env_path))

    if 'UWSGI_IDLE' in env:
        try:
            idle_timeout = int(env['UWSGI_IDLE'])
            settings.extend([
                ('idle', str(idle_timeout)),
                ('cheap', 'True'),
                ('die-on-idle', 'True')
            ])
            echo("-----> uwsgi will start workers on demand and kill them after {}s of inactivity".format(idle_timeout), fg='yellow')
        except Exception:
            echo("Error: malformed setting 'UWSGI_IDLE', ignoring it.".format(), fg='red')
            pass

    if kind.startswith("cron"):
        settings.extend([
            ['cron', command.replace("*/", "-").replace("*", "-1")],
        ])

    if kind == 'jwsgi':
        settings.extend([
            ('module', command),
            ('threads', env.get('UWSGI_THREADS', '4')),
            ('plugin', 'jvm'),
            ('plugin', 'jwsgi')
        ])

    # could not come up with a better kind for ruby, web would work but that means loading the rack plugin in web.
    if kind == 'rwsgi':
        settings.extend([
            ('module', command),
            ('threads', env.get('UWSGI_THREADS', '4')),
            ('plugin', 'rack'),
            ('plugin', 'rbrequire'),
            ('plugin', 'post-buffering')
        ])

    python_version = int(env.get('PYTHON_VERSION', '3'))

    if kind == 'wsgi':
        settings.extend([
            ('module', command),
            ('threads', env.get('UWSGI_THREADS', '4')),
        ])

        if python_version == 2:
            settings.extend([
                ('plugin', 'python'),
            ])
            if 'UWSGI_GEVENT' in env:
                settings.extend([
                    ('plugin', 'gevent_python'),
                    ('gevent', env['UWSGI_GEVENT']),
                ])
            elif 'UWSGI_ASYNCIO' in env:
                try:
                    tasks = int(env['UWSGI_ASYNCIO'])
                    settings.extend([
                        ('plugin', 'asyncio_python'),
                        ('async', tasks),
                    ])
                    echo("-----> uwsgi will support {} async tasks".format(tasks), fg='yellow')
                except ValueError:
                    echo("Error: malformed setting 'UWSGI_ASYNCIO', ignoring it.".format(), fg='red')

        elif python_version == 3:
            settings.extend([
                ('plugin', 'python3'),
            ])
            if 'UWSGI_ASYNCIO' in env:
                try:
                    tasks = int(env['UWSGI_ASYNCIO'])
                    settings.extend([
                        ('plugin', 'asyncio_python3'),
                        ('async', tasks),
                    ])
                    echo("-----> uwsgi will support {} async tasks".format(tasks), fg='yellow')
                except ValueError:
                    echo("Error: malformed setting 'UWSGI_ASYNCIO', ignoring it.".format(), fg='red')

        # If running under nginx, don't expose a port at all
        if 'NGINX_SERVER_NAME' in env:
            sock = join(NGINX_ROOT, "{}.sock".format(app))
            echo("-----> nginx will talk to uWSGI via {}".format(sock), fg='yellow')
            settings.extend([
                ('socket', sock),
                ('chmod-socket', '664'),
            ])
        else:
            echo("-----> nginx will talk to uWSGI via {BIND_ADDRESS:s}:{PORT:s}".format(**env), fg='yellow')
            settings.extend([
                ('http', '{BIND_ADDRESS:s}:{PORT:s}'.format(**env)),
                ('http-use-socket', '{BIND_ADDRESS:s}:{PORT:s}'.format(**env)),
                ('http-socket', '{BIND_ADDRESS:s}:{PORT:s}'.format(**env)),
            ])
    elif kind == 'php':
        docroot = join(APP_ROOT, app, command.strip("/").rstrip("/"))
        settings.extend([
            ('plugin', 'http,0:php'),
            ('http', ':{}'.format(env['PORT'])),
            ('check-static', docroot),
            ('static-skip-ext', '.php'),
            ('static-skip-ext', '.inc'),
            ('static-index', 'index.html'),
            ('php-docroot', docroot),
            ('php-allowed-ext', '.php'),
            ('php-index', 'index.php')
        ])
    elif kind == 'web':
        echo("-----> nginx will talk to the 'web' process via {BIND_ADDRESS:s}:{PORT:s}".format(**env), fg='yellow')
        settings.append(('attach-daemon', command))
    elif kind == 'static':
        echo("-----> nginx serving static files only".format(**env), fg='yellow')
    elif kind.startswith("cron"):
        echo("-----> uwsgi scheduled cron for {command}".format(**locals()), fg='yellow')
    else:
        settings.append(('attach-daemon', command))

    if kind in ['wsgi', 'web']:
        settings.append(('log-format',
                         '%%(addr) - %%(user) [%%(ltime)] "%%(method) %%(uri) %%(proto)" %%(status) %%(size) "%%(referer)" "%%(uagent)" %%(msecs)ms'))

    # remove unnecessary variables from the env in nginx.ini
    for k in ['NGINX_ACL']:
        if k in env:
            del env[k]

    # insert user defined uwsgi settings if set
    settings += parse_settings(join(APP_ROOT, app, env.get("UWSGI_INCLUDE_FILE"))).items() if env.get("UWSGI_INCLUDE_FILE") else []

    for k, v in env.items():
        settings.append(('env', '{k:s}={v}'.format(**locals())))

    if kind != 'static':
        with open(available, 'w') as h:
            h.write('[uwsgi]\n')
            for k, v in settings:
                h.write("{k:s} = {v}\n".format(**locals()))

        copyfile(available, enabled)


def do_stop(app):
    config = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))

    if len(config) > 0:
        echo("Stopping app '{}'...".format(app), fg='yellow')
        for c in config:
            remove(c)
    else:
        echo("Error: app '{}' not deployed!".format(app), fg='red')  # TODO app could be already stopped. Need to able to tell the difference.


def do_restart(app):
    """Restarts a deployed app"""
    # This must work even if the app is stopped when called. At the end, the app should be running.
    echo("restarting app '{}'...".format(app), fg='yellow')
    do_stop(app)
    spawn_app(app)


def multi_tail(app, filenames, catch_up=20):
    """Tails multiple log files"""

    # Seek helper
    def peek(handle):
        where = handle.tell()
        line = handle.readline()
        if not line:
            handle.seek(where)
            return None
        return line

    inodes = {}
    files = {}
    prefixes = {}

    # Set up current state for each log file
    for f in filenames:
        prefixes[f] = splitext(basename(f))[0]
        files[f] = open(f, "rt", encoding="utf-8", errors="ignore")
        inodes[f] = stat(f).st_ino
        files[f].seek(0, 2)

    longest = max(map(len, prefixes.values()))

    # Grab a little history (if any)
    for f in filenames:
        for line in deque(open(f, "rt", encoding="utf-8", errors="ignore"), catch_up):
            yield "{} | {}".format(prefixes[f].ljust(longest), line)

    while True:
        updated = False
        # Check for updates on every file
        for f in filenames:
            line = peek(files[f])
            if line:
                updated = True
                yield "{} | {}".format(prefixes[f].ljust(longest), line)

        if not updated:
            sleep(1)
            # Check if logs rotated
            for f in filenames:
                if exists(f):
                    if stat(f).st_ino != inodes[f]:
                        files[f] = open(f)
                        inodes[f] = stat(f).st_ino
                else:
                    filenames.remove(f)


# === CLI commands ===

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@group(context_settings=CONTEXT_SETTINGS)
def piku():
    """The smallest PaaS you've ever seen"""
    pass


piku.rc = getattr(piku, "result_callback", None) or getattr(piku, "resultcallback", None)


@piku.rc()
def cleanup(ctx):
    """Callback from command execution -- add debugging to taste"""
    pass

# --- User commands ---


@piku.command("apps")
def cmd_apps():
    """List apps, e.g.: piku apps"""
    apps = listdir(APP_ROOT)
    if not apps:
        echo("There are no applications deployed.")
        return

    for a in apps:
        running = len(glob(join(UWSGI_ENABLED, '{}*.ini'.format(a)))) != 0
        echo(('*' if running else ' ') + a, fg='green')


@piku.command("config")
@argument('app')
def cmd_config(app):
    """Show config, e.g.: piku config <app>"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    else:
        echo("Warning: app '{}' not deployed, no config found.".format(app), fg='yellow')


@piku.command("config:get")
@argument('app')
@argument('setting')
def cmd_config_get(app, setting):
    """e.g.: piku config:get <app> FOO"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        env = parse_settings(config_file)
        if setting in env:
            echo("{}".format(env[setting]), fg='white')
    else:
        echo("Warning: no active configuration for '{}'".format(app))


@piku.command("config:set")
@argument('app')
@argument('settings', nargs=-1)
def cmd_config_set(app, settings):
    """e.g.: piku config:set <app> FOO=bar BAZ=quux"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'ENV')
    env = parse_settings(config_file)
    for s in shsplit(" ".join(settings)):
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            env[k] = v
            echo("Setting {k:s}={v} for '{app:s}'".format(**locals()), fg='white')
        except Exception:
            echo("Error: malformed setting '{}'".format(s), fg='red')
            return
    write_config(config_file, env)
    do_deploy(app)


@piku.command("config:unset")
@argument('app')
@argument('settings', nargs=-1)
def cmd_config_unset(app, settings):
    """e.g.: piku config:unset <app> FOO"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'ENV')
    env = parse_settings(config_file)
    for s in settings:
        if s in env:
            del env[s]
            echo("Unsetting {} for '{}'".format(s, app), fg='white')
    write_config(config_file, env)
    do_deploy(app)


@piku.command("config:live")
@argument('app')
def cmd_config_live(app):
    """e.g.: piku config:live <app>"""

    app = exit_if_invalid(app)

    live_config = join(ENV_ROOT, app, 'LIVE_ENV')
    if exists(live_config):
        echo(open(live_config).read().strip(), fg='white')
    else:
        echo("Warning: app '{}' not deployed, no config found.".format(app), fg='yellow')


@piku.command("deploy")
@argument('app')
def cmd_deploy(app):
    """e.g.: piku deploy <app>"""

    app = exit_if_invalid(app)
    do_deploy(app)


@piku.command("destroy")
@argument('app')
def cmd_destroy(app):
    """e.g.: piku destroy <app>"""

    app = exit_if_invalid(app)

    # leave DATA_ROOT, since apps may create hard to reproduce data,
    # and CACHE_ROOT, since `nginx` will set permissions to protect it
    for p in [join(x, app) for x in [APP_ROOT, GIT_ROOT, ENV_ROOT, LOG_ROOT]]:
        if exists(p):
            echo("--> Removing folder '{}'".format(p), fg='yellow')
            rmtree(p)

    for p in [join(x, '{}*.ini'.format(app)) for x in [UWSGI_AVAILABLE, UWSGI_ENABLED]]:
        g = glob(p)
        if len(g) > 0:
            for f in g:
                echo("--> Removing file '{}'".format(f), fg='yellow')
                remove(f)

    nginx_files = [join(NGINX_ROOT, "{}.{}".format(app, x)) for x in ['conf', 'sock', 'key', 'crt']]
    for f in nginx_files:
        if exists(f):
            echo("--> Removing file '{}'".format(f), fg='yellow')
            remove(f)

    acme_link = join(ACME_WWW, app)
    acme_certs = realpath(acme_link)
    if exists(acme_certs):
        echo("--> Removing folder '{}'".format(acme_certs), fg='yellow')
        rmtree(acme_certs)
        echo("--> Removing file '{}'".format(acme_link), fg='yellow')
        unlink(acme_link)

    # These come last to make sure they're visible
    for p in [join(x, app) for x in [DATA_ROOT, CACHE_ROOT]]:
        if exists(p):
            echo("==> Preserving folder '{}'".format(p), fg='red')


@piku.command("logs")
@argument('app')
@argument('process', nargs=1, default='*')
def cmd_logs(app, process):
    """Tail running logs, e.g: piku logs <app> [<process>]"""

    app = exit_if_invalid(app)

    logfiles = glob(join(LOG_ROOT, app, process + '.*.log'))
    if len(logfiles) > 0:
        for line in multi_tail(app, logfiles):
            echo(line.strip(), fg='white')
    else:
        echo("No logs found for app '{}'.".format(app), fg='yellow')


@piku.command("ps")
@argument('app')
def cmd_ps(app):
    """Show process count, e.g: piku ps <app>"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'SCALING')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    else:
        echo("Error: no workers found for app '{}'.".format(app), fg='red')


@piku.command("ps:scale")
@argument('app')
@argument('settings', nargs=-1)
def cmd_ps_scale(app, settings):
    """e.g.: piku ps:scale <app> <proc>=<count>"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'SCALING')
    worker_count = {k: int(v) for k, v in parse_procfile(config_file).items()}
    deltas = {}
    for s in settings:
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            c = int(v)  # check for integer value
            if c < 0:
                echo("Error: cannot scale type '{}' below 0".format(k), fg='red')
                return
            if k not in worker_count:
                echo("Error: worker type '{}' not present in '{}'".format(k, app), fg='red')
                return
            deltas[k] = c - worker_count[k]
        except Exception:
            echo("Error: malformed setting '{}'".format(s), fg='red')
            return
    do_deploy(app, deltas)


@piku.command("run")
@argument('app')
@argument('cmd', nargs=-1)
def cmd_run(app, cmd):
    """e.g.: piku run <app> ls -- -al"""

    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'LIVE_ENV')
    environ.update(parse_settings(config_file))
    for f in [stdout, stderr]:
        fl = fcntl(f, F_GETFL)
        fcntl(f, F_SETFL, fl | O_NONBLOCK)
    p = Popen(' '.join(cmd), stdin=stdin, stdout=stdout, stderr=stderr, env=environ, cwd=join(APP_ROOT, app), shell=True)
    p.communicate()


@piku.command("restart")
@argument('app')
def cmd_restart(app):
    """Restart an app: piku restart <app>"""

    app = exit_if_invalid(app)

    do_restart(app)


@piku.command("setup")
def cmd_setup():
    """Initialize environment"""

    echo("Running in Python {}".format(".".join(map(str, version_info))))

    # Create required paths
    for p in [APP_ROOT, CACHE_ROOT, DATA_ROOT, GIT_ROOT, ENV_ROOT, UWSGI_ROOT, UWSGI_AVAILABLE, UWSGI_ENABLED, LOG_ROOT, NGINX_ROOT]:
        if not exists(p):
            echo("Creating '{}'.".format(p), fg='green')
            makedirs(p)

    # Set up the uWSGI emperor config
    settings = [
        ('chdir', UWSGI_ROOT),
        ('emperor', UWSGI_ENABLED),
        ('log-maxsize', UWSGI_LOG_MAXSIZE),
        ('logto', join(UWSGI_ROOT, 'uwsgi.log')),
        ('log-backupname', join(UWSGI_ROOT, 'uwsgi.old.log')),
        ('socket', join(UWSGI_ROOT, 'uwsgi.sock')),
        ('uid', getpwuid(getuid()).pw_name),
        ('gid', getgrgid(getgid()).gr_name),
        ('enable-threads', 'true'),
        ('threads', '{}'.format(cpu_count() * 2)),
    ]
    with open(join(UWSGI_ROOT, 'uwsgi.ini'), 'w') as h:
        h.write('[uwsgi]\n')
        # pylint: disable=unused-variable
        for k, v in settings:
            h.write("{k:s} = {v}\n".format(**locals()))

    # mark this script as executable (in case we were invoked via interpreter)
    if not (stat(PIKU_SCRIPT).st_mode & S_IXUSR):
        echo("Setting '{}' as executable.".format(PIKU_SCRIPT), fg='yellow')
        chmod(PIKU_SCRIPT, stat(PIKU_SCRIPT).st_mode | S_IXUSR)


@piku.command("setup:ssh")
@argument('public_key_file')
def cmd_setup_ssh(public_key_file):
    """Set up a new SSH key (use - for stdin)"""

    def add_helper(key_file):
        if exists(key_file):
            try:
                fingerprint = str(check_output('ssh-keygen -lf ' + key_file, shell=True)).split(' ', 4)[1]
                key = open(key_file, 'r').read().strip()
                echo("Adding key '{}'.".format(fingerprint), fg='white')
                setup_authorized_keys(fingerprint, PIKU_SCRIPT, key)
            except Exception:
                echo("Error: invalid public key file '{}': {}".format(key_file, format_exc()), fg='red')
        elif public_key_file == '-':
            buffer = "".join(stdin.readlines())
            with NamedTemporaryFile(mode="w") as f:
                f.write(buffer)
                f.flush()
                add_helper(f.name)
        else:
            echo("Error: public key file '{}' not found.".format(key_file), fg='red')

    add_helper(public_key_file)


@piku.command("stop")
@argument('app')
def cmd_stop(app):
    """Stop an app, e.g: piku stop <app>"""
    app = exit_if_invalid(app)
    do_stop(app)


# --- Internal commands ---

@piku.command("git-hook")
@argument('app')
def cmd_git_hook(app):
    """INTERNAL: Post-receive git hook"""

    app = sanitize_app_name(app)
    repo_path = join(GIT_ROOT, app)
    app_path = join(APP_ROOT, app)
    data_path = join(DATA_ROOT, app)

    for line in stdin:
        # pylint: disable=unused-variable
        oldrev, newrev, refname = line.strip().split(" ")
        # Handle pushes
        if not exists(app_path):
            echo("-----> Creating app '{}'".format(app), fg='green')
            makedirs(app_path)
            # The data directory may already exist, since this may be a full redeployment (we never delete data since it may be expensive to recreate)
            if not exists(data_path):
                makedirs(data_path)
            call("git clone --quiet {} {}".format(repo_path, app), cwd=APP_ROOT, shell=True)
        do_deploy(app, newrev=newrev)


@piku.command("git-receive-pack")
@argument('app')
def cmd_git_receive_pack(app):
    """INTERNAL: Handle git pushes for an app"""

    app = sanitize_app_name(app)
    hook_path = join(GIT_ROOT, app, 'hooks', 'post-receive')
    env = globals()
    env.update(locals())

    if not exists(hook_path):
        makedirs(dirname(hook_path))
        # Initialize the repository with a hook to this script
        call("git init --quiet --bare " + app, cwd=GIT_ROOT, shell=True)
        with open(hook_path, 'w') as h:
            h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="{PIKU_ROOT:s}" {PIKU_SCRIPT:s} git-hook {app:s}""".format(**env))
        # Make the hook executable by our user
        chmod(hook_path, stat(hook_path).st_mode | S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    call('git-shell -c "{}" '.format(argv[1] + " '{}'".format(app)), cwd=GIT_ROOT, shell=True)


@piku.command("git-upload-pack")
@argument('app')
def cmd_git_upload_pack(app):
    """INTERNAL: Handle git upload pack for an app"""
    app = sanitize_app_name(app)
    env = globals()
    env.update(locals())
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    call('git-shell -c "{}" '.format(argv[1] + " '{}'".format(app)), cwd=GIT_ROOT, shell=True)


@piku.command("scp", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@pass_context
def cmd_scp(ctx):
    """Simple wrapper to allow scp to work."""
    call(" ".join(["scp"] + ctx.args), cwd=GIT_ROOT, shell=True)


def _get_plugin_commands(path):
    sys_path.append(abspath(path))

    cli_commands = []
    if isdir(path):
        for item in listdir(path):
            module_path = join(path, item)
            if isdir(module_path):
                try:
                    module = import_module(item)
                except Exception:
                    module = None
                if hasattr(module, 'cli_commands'):
                    cli_commands.append(module.cli_commands())

    return cli_commands


@piku.command("help")
@pass_context
def cmd_help(ctx):
    """display help for piku"""
    echo(ctx.parent.get_help())


@piku.command("update")
def cmd_update():
    """Update the piku cli"""
    echo("Updating piku...")

    with NamedTemporaryFile(mode="w") as f:
        tempfile = f.name
        cmd = """curl -sL -w %{{http_code}} {} -o {}""".format(PIKU_RAW_SOURCE_URL, tempfile)
        response = check_output(cmd.split(' '), stderr=STDOUT)
        http_code = response.decode('utf8').strip()
        if http_code == "200":
            copyfile(tempfile, PIKU_SCRIPT)
            echo("Update successful.")
        else:
            echo("Error updating piku - please check if {} is accessible from this machine.".format(PIKU_RAW_SOURCE_URL))
    echo("Done.")


if __name__ == '__main__':
    cli_commands = _get_plugin_commands(path=PIKU_PLUGIN_ROOT)
    cli_commands.append(piku)
    cli = CommandCollection(sources=cli_commands)
    cli()
