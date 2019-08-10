#!/usr/bin/env python3

"Piku Micro-PaaS"

try:
    from sys import version_info
    assert version_info >= (3,5)
except AssertionError:
    exit("Piku requires Python 3.5 or above")

from click import argument, command, group, get_current_context, option, secho as echo
from collections import defaultdict, deque
from datetime import datetime
from fcntl import fcntl, F_SETFL, F_GETFL
from glob import glob
from hashlib import md5
from json import loads
from multiprocessing import cpu_count
from os import chmod, getgid, getuid, symlink, unlink, remove, stat, listdir, environ, makedirs, O_NONBLOCK
from os.path import abspath, basename, dirname, exists, getmtime, join, realpath, splitext
from re import sub
from shutil import copyfile, rmtree, which
from socket import socket, AF_INET, SOCK_STREAM
from sys import argv, stdin, stdout, stderr, version_info, exit
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import call, check_output, Popen, STDOUT, PIPE 
from tempfile import NamedTemporaryFile
from traceback import format_exc
from time import sleep
from urllib.request import urlopen
from pwd import getpwuid
from grp import getgrgid
from yaml import safe_load

# === Make sure we can access all system binaries ===

if 'sbin' not in environ['PATH']:
    environ['PATH'] = "/usr/local/sbin:/usr/sbin:/sbin:" + environ['PATH']

# === Globals - all tweakable settings are here ===

PIKU_ROOT = environ.get('PIKU_ROOT', join(environ['HOME'],'.piku'))
PIKU_SCRIPT = realpath(__file__)
APP_ROOT = abspath(join(PIKU_ROOT, "apps"))
ENV_ROOT = abspath(join(PIKU_ROOT, "envs"))
GIT_ROOT = abspath(join(PIKU_ROOT, "repos"))
LOG_ROOT = abspath(join(PIKU_ROOT, "logs"))
NGINX_ROOT = abspath(join(PIKU_ROOT, "nginx"))
UWSGI_AVAILABLE = abspath(join(PIKU_ROOT, "uwsgi-available"))
UWSGI_ENABLED = abspath(join(PIKU_ROOT, "uwsgi-enabled"))
UWSGI_ROOT = abspath(join(PIKU_ROOT, "uwsgi"))
UWSGI_LOG_MAXSIZE = '1048576'
ACME_ROOT = environ.get('ACME_ROOT', join(environ['HOME'],'.acme.sh'))
ACME_WWW = abspath(join(PIKU_ROOT, "acme"))

# pylint: disable=anomalous-backslash-in-string
NGINX_TEMPLATE = """
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

$NGINX_COMMON
}
"""

NGINX_HTTPS_ONLY_TEMPLATE = """
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

  return 301 https://$server_name$request_uri;
}

server {
$NGINX_COMMON
}
"""
# pylint: enable=anomalous-backslash-in-string

NGINX_COMMON_FRAGMENT = """
  listen              $NGINX_IPV6_ADDRESS:$NGINX_SSL;
  listen              $NGINX_IPV4_ADDRESS:$NGINX_SSL;
  ssl                 on;
  ssl_certificate     $NGINX_ROOT/$APP.crt;
  ssl_certificate_key $NGINX_ROOT/$APP.key;
  server_name         $NGINX_SERVER_NAME;

  # These are not required under systemd - enable for debugging only
  # access_log        $LOG_ROOT/$APP/access.log;
  # error_log         $LOG_ROOT/$APP/error.log;
  
  # Enable gzip compression
  gzip on;
  gzip_proxied any;
  gzip_types text/plain text/xml text/css application/x-javascript text/javascript application/xml+rss application/atom+xml;
  gzip_comp_level 7;
  gzip_min_length 2048;
  gzip_vary on;
  gzip_disable "MSIE [1-6]\.(?!.*SV1)";
  
  # set a custom header for requests
  add_header X-Deployed-By Piku;

  $NGINX_CUSTOM_CLAUSES

  $INTERNAL_NGINX_STATIC_MAPPINGS

  $NGINX_BLOCK_GIT

  location    / {
    $INTERNAL_NGINX_UWSGI_SETTINGS
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $remote_addr;
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

INTERNAL_NGINX_STATIC_MAPPING = """
  location $static_url {
      sendfile on;
      sendfile_max_chunk 1m;
      tcp_nopush on;
      directio 8m;
      aio threads;
      alias $static_path;
  }
"""

INTERNAL_NGINX_UWSGI_SETTINGS = """
    uwsgi_pass $APP;
    uwsgi_param QUERY_STRING $query_string;
    uwsgi_param REQUEST_METHOD $request_method;
    uwsgi_param CONTENT_TYPE $content_type;
    uwsgi_param CONTENT_LENGTH $content_length;
    uwsgi_param REQUEST_URI $request_uri;
    uwsgi_param PATH_INFO $document_uri;
    uwsgi_param DOCUMENT_ROOT $document_root;
    uwsgi_param SERVER_PROTOCOL $server_protocol;
    uwsgi_param REMOTE_ADDR $remote_addr;
    uwsgi_param REMOTE_PORT $remote_port;
    uwsgi_param SERVER_ADDR $server_addr;
    uwsgi_param SERVER_PORT $server_port;
    uwsgi_param SERVER_NAME $server_name;
"""

# === Utility functions ===

def sanitize_app_name(app):
    """Sanitize the app name and build matching path"""
    
    app = "".join(c for c in app if c.isalnum() or c in ('.','_')).rstrip().lstrip('/')
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
    s.bind((address,0))
    port = s.getsockname()[1]
    s.close()
    return port


def write_config(filename, bag, separator='='):
    """Helper for writing out config files"""
    
    with open(filename, 'w') as h:
        # pylint: disable=unused-variable
        for k, v in bag.items():
            h.write('{k:s}{separator:s}{v}\n'.format(**locals()))


def setup_authorized_keys(ssh_fingerprint, script_path, pubkey):
    """Sets up an authorized_keys file to redirect SSH commands"""
    
    authorized_keys = join(environ['HOME'],'.ssh','authorized_keys')
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
        for line in procfile:
            try:
                kind, command = map(lambda x: x.strip(), line.split(":", 1))
                workers[kind] = command
            except:
                echo("Warning: unrecognized Procfile entry '{}'".format(line), fg='yellow')
    if not len(workers):
        return {}
    # WSGI trumps regular web workers
    if 'wsgi' or 'jwsgi' in workers:
        if 'web' in workers:
            echo("Warning: found both 'wsgi' and 'web' workers, disabling 'web'", fg='yellow')
            del(workers['web'])
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
    except:
        return ""


def parse_settings(filename, env={}):
    """Parses a settings file and returns a dict with environment variables"""
    
    if not exists(filename):
        return {}
        
    with open(filename, 'r') as settings:
        for line in settings:
            if '#' == line[0] or len(line.strip()) == 0: # ignore comments and newlines
                continue
            try:
                k, v = map(lambda x: x.strip(), line.split("=", 1))
                env[k] = expandvars(v, env)
            except:
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
    

def do_deploy(app, deltas={}, newrev=None):
    """Deploy an app by resetting the work directory"""
    
    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    log_path = join(LOG_ROOT, app)
    env_file = join(APP_ROOT, app, 'ENV')
    config_file = join(ENV_ROOT, app, 'ENV')

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
        if workers and len(workers):
            settings = {}
            if exists(join(app_path, 'requirements.txt')):
                echo("-----> Python app detected.", fg='green')
                settings.update(deploy_python(app, deltas))
            elif exists(join(app_path, 'package.json')) and check_requirements(['nodejs', 'npm']):
                echo("-----> Node app detected.", fg='green')
                settings.update(deploy_node(app, deltas))
            elif exists(join(app_path, 'pom.xml')) and check_requirements(['java', 'mvn']):
                echo("-----> Java app detected.", fg='green')
                settings.update(deploy_java(app, deltas))
            elif exists(join(app_path, 'build.gradle')) and check_requirements(['java', 'gradle']):
                echo("-----> Gradle Java app detected.", fg='green')
                settings.update(deploy_java(app, deltas))
            elif (exists(join(app_path, 'Godeps')) or len(glob(join(app_path,'*.go')))) and check_requirements(['go']):
                echo("-----> Go app detected.", fg='green')
                settings.update(deploy_go(app, deltas))
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

def deploy_gradle(app, deltas={}):
    """Deploy a Java application using Gradle"""  
    virtual = join(ENV_ROOT, app)
    target_path = join(APP_ROOT, app, 'build')
    env_file = join(APP_ROOT, app, 'ENV')
    build = join(APP_ROOT, app, 'build.gradle')

    first_time = False
    if not exists(target_path) or first_time == True:
        venv = 'mkdir ' + virtual
        call(venv, cwd=PIKU_ROOT, shell=True)
        env = {
            'VIRTUAL_ENV': virtual,
            "PATH": ':'.join([join(virtual, "bin"), join(app, ".bin"),environ['PATH']])
        }
        if exists(env_file):
            env.update(parse_settings(env_file, env))
            echo("-----> Building Java Application")
            call('gradle build', cwd=join(APP_ROOT, app), env=env, shell=True)
            first_time = True
    else:
            if getmtime(build) > getmtime(target_path):
                echo ("-----> Performing a clean build")
                call('gradle clean build', cwd=join(APP_ROOT, app), env=env, shell=True)
    
    return spawn_app(app, deltas)

def deploy_java(app, deltas={}):
    """Deploy a Java application using Maven"""
    # Check for if pom.xml exists or build.gradle
    # Since gradle can build a variety of projects from scala, clojure etc, I think it is better to add a deploy_gradle function
    # TODO: Use jenv to isolate Java Application environments

    virtual = join(ENV_ROOT, app)
    target_path = join(APP_ROOT, app, 'target')
    env_file = join(APP_ROOT, app, 'ENV')
    pom = join(APP_ROOT, app, 'pom.xml')

    first_time = False
    if not exists(target_path) or first_time == True:
        venv = 'mkdir ' + virtual
        call(venv, cwd=PIKU_ROOT, shell=True)
        env = {
            'VIRTUAL_ENV': virtual,
            "PATH": ':'.join([join(virtual, "bin"), join(app, ".bin"),environ['PATH']])
        }
        if exists(env_file):
            env.update(parse_settings(env_file, env))
            echo("-----> Building Java Application")
            call('mvn compile', cwd=join(APP_ROOT, app), env=env, shell=True)
            # Compiles your java project according to pom.xml
            echo("-----> Running Maven Tests")
            call('mvn test', cwd=join(APP_ROOT, app), env=env, shell=True)
            echo("-----> Tests Completed \n-----> Packaging Compiled Sources ")
            call('mvn package', cwd=join(APP_ROOT, app), env=env, shell=True)
            echo("-----> Finished Packaging && Now Verifying Compiled Packages")
            call('mvn verify', cwd=join(APP_ROOT, app), env=env, shell=True)
            echo("-----> Installing Application on local repository for future usage")
            call('mvn install', cwd=join(APP_ROOT, app), env=env, shell=True)
            echo('----->Successfully deployed your package on Maven Local Repository')
            echo('-----> Deploying App to Maven Central Repository')
            first_time = True
    else:
        if getmtime(pom) > getmtime(target_path):
            
            echo("-----> Destroying previous builds")
            call('mvn clean', cwd=join(APP_ROOT, app), env=env, shell=True)
            echo('-----> Starting new build')
            call('mvn compile && mvn test && mvn package && mvn verify && mvn install && mvn deploy', cwd=join(APP_ROOT, app), env=env, shell=True)
    
    return spawn_app(app, deltas)



def deploy_go(app, deltas={}):
    """Deploy a Go application"""

    go_path = join(ENV_ROOT, app)
    deps = join(APP_ROOT, app, 'Godeps')

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
    return spawn_app(app, deltas)


def deploy_node(app, deltas={}):
    """Deploy a Node  application"""

    virtualenv_path = join(ENV_ROOT, app)
    node_path = join(ENV_ROOT, app, "node_modules")
    node_path_tmp = join(APP_ROOT, app, "node_modules")
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
        'NPM_CONFIG_PREFIX': abspath(join(node_path, "..")),
        "PATH": ':'.join([join(virtualenv_path, "bin"), join(node_path, ".bin"),environ['PATH']])
    }
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    version = env.get("NODE_VERSION")
    node_binary = join(virtualenv_path, "bin", "node")
    installed = check_output("{} -v".format(node_binary), cwd=join(APP_ROOT, app), env=env, shell=True).decode("utf8").rstrip("\n") if exists(node_binary) else ""

    if version and check_requirements(['nodeenv']):
        if not installed.endswith(version):
            started = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))
            if installed and len(started):
                echo("Warning: Can't update node with app running. Stop the app & retry.", fg='yellow')
            else:
                echo("-----> Installing node version '{NODE_VERSION:s}' using nodeenv".format(**env), fg='green')
                call("nodeenv --prebuilt --node={NODE_VERSION:s} --clean-src --force {VIRTUAL_ENV:s}".format(**env), cwd=virtualenv_path, env=env, shell=True)
        else:
            echo("-----> Node is installed at {}.".format(version))

    if exists(deps) and check_requirements(['npm']):
        if first_time or getmtime(deps) > getmtime(node_path):
            echo("-----> Running npm for '{}'".format(app), fg='green')
            symlink(node_path, node_path_tmp)
            call('npm install', cwd=join(APP_ROOT, app), env=env, shell=True)
            unlink(node_path_tmp)
    return spawn_app(app, deltas)


def deploy_python(app, deltas={}):
    """Deploy a Python application"""
    
    virtualenv_path = join(ENV_ROOT, app)
    requirements = join(APP_ROOT, app, 'requirements.txt')
    env_file = join(APP_ROOT, app, 'ENV')
    # Peek at environment variables shipped with repo (if any) to determine version
    env = {}
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    # TODO: improve version parsing
    # pylint: disable=unused-variable
    version = int(env.get("PYTHON_VERSION", "3"))

    first_time = False
    if not exists(virtualenv_path):
        echo("-----> Creating virtualenv for '{}'".format(app), fg='green')
        makedirs(virtualenv_path)
        call('virtualenv --python=python{version:d} {app:s}'.format(**locals()), cwd=ENV_ROOT, shell=True)
        first_time = True

    activation_script = join(virtualenv_path,'bin','activate_this.py')
    exec(open(activation_script).read(), dict(__file__=activation_script))

    if first_time or getmtime(requirements) > getmtime(virtualenv_path):
        echo("-----> Running pip for '{}'".format(app), fg='green')
        call('pip install -r {}'.format(requirements), cwd=virtualenv_path, shell=True)
    return spawn_app(app, deltas)

 
def spawn_app(app, deltas={}):
    """Create all workers for an app"""
    
    # pylint: disable=unused-variable
    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    workers = parse_procfile(procfile)
    workers.pop("release", None)
    ordinals = defaultdict(lambda:1)
    worker_count = {k:1 for k in workers.keys()}

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
        'HOME': environ['HOME'],
        'USER': environ['USER'],
        'PATH': ':'.join([join(virtualenv_path,'bin'),environ['PATH']]),
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
        env["PATH"] = ':'.join([join(node_path, ".bin"),env['PATH']])

    # Load environment variables shipped with repo (if any)
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    # Override with custom settings (if any)
    if exists(settings):
        env.update(parse_settings(settings, env))

    if 'web' in workers or 'wsgi' or 'jwsgi' in workers:
        # Pick a port if none defined
        if 'PORT' not in env:
            env['PORT'] = str(get_free_port())
            echo("-----> picking free port {PORT}".format(**env))

        # Safe defaults for addressing     
        for k, v in safe_defaults.items():
            if k not in env:
                echo("-----> nginx {k:s} set to {v}".format(**locals()))
                env[k] = v
                
        # Set up nginx if we have NGINX_SERVER_NAME set
        if 'NGINX_SERVER_NAME' in env:
            nginx = command_output("nginx -V")
            nginx_ssl = "443 ssl"
            if "--with-http_v2_module" in nginx:
                nginx_ssl += " http2"
            elif "--with-http_spdy_module" in nginx and "nginx/1.6.2" not in nginx: # avoid Raspbian bug
                nginx_ssl += " spdy"
            nginx_conf = join(NGINX_ROOT,"{}.conf".format(app))
        
            env.update({ 
                'NGINX_SSL': nginx_ssl,
                'NGINX_ROOT': NGINX_ROOT,
                'ACME_WWW': ACME_WWW,
            })
            
            # default to reverse proxying to the TCP port we picked
            env['INTERNAL_NGINX_UWSGI_SETTINGS'] = 'proxy_pass http://{BIND_ADDRESS:s}:{PORT:s};'.format(**env)
            if 'wsgi' or 'jwsgi' in workers:
                sock = join(NGINX_ROOT, "{}.sock".format(app))
                env['INTERNAL_NGINX_UWSGI_SETTINGS'] = expandvars(INTERNAL_NGINX_UWSGI_SETTINGS, env)
                env['NGINX_SOCKET'] = env['BIND_ADDRESS'] = "unix://" + sock
                if 'PORT' in env:
                    del env['PORT']
            else:
                env['NGINX_SOCKET'] = "{BIND_ADDRESS:s}:{PORT:s}".format(**env) 
                echo("-----> nginx will look for app '{}' on {}".format(app, env['NGINX_SOCKET']))

        
            domain = env['NGINX_SERVER_NAME'].split()[0]       
            key, crt = [join(NGINX_ROOT, "{}.{}".format(app,x)) for x in ['key','crt']]
            if exists(join(ACME_ROOT, "acme.sh")):
                acme = ACME_ROOT
                www = ACME_WWW
                # if this is the first run there will be no nginx conf yet
                # create a basic conf stub just to serve the acme auth
                if not exists(nginx_conf):
                    echo("-----> writing temporary nginx conf")
                    buffer = expandvars(NGINX_ACME_FIRSTRUN_TEMPLATE, env)
                    with open(nginx_conf, "w") as h:
                        h.write(buffer)
                if not exists(key) or not exists(join(ACME_ROOT, domain, domain + ".key")):
                    echo("-----> getting letsencrypt certificate")
                    call('{acme:s}/acme.sh --issue -d {domain:s} -w {www:s}'.format(**locals()), shell=True)
                    call('{acme:s}/acme.sh --install-cert -d {domain:s} --key-file {key:s} --fullchain-file {crt:s}'.format(**locals()), shell=True)
                    if exists(join(ACME_ROOT, domain)) and not exists(join(ACME_WWW, app)):
                        symlink(join(ACME_ROOT, domain), join(ACME_WWW, app))
                else:
                    echo("-----> letsencrypt certificate already installed")

            # fall back to creating self-signed certificate if acme failed
            if not exists(key) or stat(crt).st_size == 0:
                echo("-----> generating self-signed certificate")
                call('openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=US/ST=NY/L=New York/O=Piku/OU=Self-Signed/CN={domain:s}" -keyout {key:s} -out {crt:s}'.format(**locals()), shell=True)
            
            # restrict access to server from CloudFlare IP addresses
            acl = []
            if env.get('NGINX_CLOUDFLARE_ACL', 'false').lower() == 'true':
                try:
                    cf = loads(urlopen('https://api.cloudflare.com/client/v4/ips').read().decode("utf-8"))
                    if cf['success'] == True:
                        for i in cf['result']['ipv4_cidrs']:
                            acl.append("allow {};".format(i))
                        for i in cf['result']['ipv6_cidrs']:
                            acl.append("allow {};".format(i))
                        # allow access from controlling machine
                        if 'SSH_CLIENT' in environ:
                            remote_ip = environ['SSH_CLIENT'].split()[0]
                            echo("-----> Adding your IP ({}) to nginx ACL".format(remote_ip))
                            acl.append("allow {};".format(remote_ip))
                        acl.extend(["allow 127.0.0.1;","deny all;"])
                except Exception:
                    cf = defaultdict()
                    echo("-----> Could not retrieve CloudFlare IP ranges: {}".format(format_exc()), fg="red")
            env['NGINX_ACL'] = " ".join(acl)

            env['NGINX_BLOCK_GIT'] = "" if env.get('NGINX_ALLOW_GIT_FOLDERS') else "location ~ /\.git { deny all; }"

            env['INTERNAL_NGINX_STATIC_MAPPINGS'] = ''
            
            # Get a mapping of /url:path1,/url2:path2
            static_paths = env.get('NGINX_STATIC_PATHS','')
            if len(static_paths):
                try:
                    items = static_paths.split(',')
                    for item in items:
                        static_url, static_path = item.split(':')
                        if static_path[0] != '/':
                            static_path = join(app_path, static_path)
                        env['INTERNAL_NGINX_STATIC_MAPPINGS'] = env['INTERNAL_NGINX_STATIC_MAPPINGS'] + expandvars(INTERNAL_NGINX_STATIC_MAPPING, locals())
                except Exception as e:
                    echo("Error {} in static path spec: should be /url1:path1[,/url2:path2], ignoring.".format(e))
                    env['INTERNAL_NGINX_STATIC_MAPPINGS'] = ''

            env['NGINX_CUSTOM_CLAUSES'] = expandvars(open(join(app_path, env["NGINX_INCLUDE_FILE"])).read(), env) if env.get("NGINX_INCLUDE_FILE") else ""
            env['NGINX_COMMON'] = expandvars(NGINX_COMMON_FRAGMENT, env)

            echo("-----> nginx will map app '{}' to hostname '{}'".format(app, env['NGINX_SERVER_NAME']))
            if('NGINX_HTTPS_ONLY' in env) or ('HTTPS_ONLY' in env):
                buffer = expandvars(NGINX_HTTPS_ONLY_TEMPLATE, env)
                echo("-----> nginx will redirect all requests to hostname '{}' to HTTPS".format(env['NGINX_SERVER_NAME']))
            else:
                buffer = expandvars(NGINX_TEMPLATE, env)
            with open(nginx_conf, "w") as h:
                h.write(buffer)
            # prevent broken config from breaking other deploys
            try:
                nginx_config_test = str(check_output("nginx -t 2>&1 | grep {}".format(app), env=environ, shell=True))
            except:
                nginx_config_test = None
            if nginx_config_test:
                echo("Error: [nginx config] {}".format(nginx_config_test), fg='red')
                echo("Warning: removing broken nginx config.", fg='yellow')
                unlink(nginx_conf)

    # Configured worker count
    if exists(scaling):
        worker_count.update({k: int(v) for k,v in parse_procfile(scaling).items() if k in workers})
    
    to_create = {}
    to_destroy = {}    
    for k, v in worker_count.items():
        to_create[k] = range(1,worker_count[k] + 1)
        if k in deltas and deltas[k]:
            to_create[k] = range(1, worker_count[k] + deltas[k] + 1)
            if deltas[k] < 0:
                to_destroy[k] = range(worker_count[k], worker_count[k] + deltas[k], -1)
            worker_count[k] = worker_count[k]+deltas[k]

    # Cleanup env
    for k, v in list(env.items()):
        if k.startswith('INTERNAL_'):
            del env[k]

    # Save current settings
    write_config(live, env)
    write_config(scaling, worker_count, ':')
    
    if env.get("AUTO_RESTART", False):
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
        for w in v:
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
        ('chdir',               join(APP_ROOT, app)),
        ('master',              'true'),
        ('project',             app),
        ('max-requests',        env.get('UWSGI_MAX_REQUESTS', '1024')),
        ('listen',              env.get('UWSGI_LISTEN', '16')),
        ('processes',           env.get('UWSGI_PROCESSES', '1')),
        ('procname-prefix',     '{app:s}:{kind:s}'.format(**locals())),
        ('enable-threads',      env.get('UWSGI_ENABLE_THREADS', 'true').lower()),
        ('log-x-forwarded-for', env.get('UWSGI_LOG_X_FORWARDED_FOR', 'false').lower()),
        ('log-maxsize',         env.get('UWSGI_LOG_MAXSIZE', UWSGI_LOG_MAXSIZE)),
        ('logto',               '{log_file:s}.{ordinal:d}.log'.format(**locals())),
        ('log-backupname',      '{log_file:s}.{ordinal:d}.log.old'.format(**locals())),
    ]

    # only add virtualenv to uwsgi if it's a real virtualenv
    if exists(join(env_path, "bin", "activate_this.py")):
        settings.append(('virtualenv', env_path))

    if kind== 'jwsgi':
        settings.extend([
            ('module', command),
            ('threads',     env.get('UWSGI_THREADS','4')),
            ('plugin', 'jvm'),
            ('plugin', 'jwsgi')
        ])

    python_version = int(env.get('PYTHON_VERSION','3'))

    if kind == 'wsgi':
        settings.extend([
            ('module',      command),
            ('threads',     env.get('UWSGI_THREADS','4')),
        ])
        if python_version == 2:
            settings.extend([
                ('plugin',      'python'),
            ])
            if 'UWSGI_GEVENT' in env:
                settings.extend([
                    ('plugin',  'gevent_python'),
                    ('gevent',  env['UWSGI_GEVENT']),
                ])
            elif 'UWSGI_ASYNCIO' in env:
                settings.extend([
                    ('plugin',  'asyncio_python'),
                ])
        elif python_version == 3:
            settings.extend([
                ('plugin',      'python3'),
            ])
            if 'UWSGI_ASYNCIO' in env:
                settings.extend([
                    ('plugin',  'asyncio_python3'),
                ])
            

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
                ('http',        '{BIND_ADDRESS:s}:{PORT:s}'.format(**env)),
                ('http-socket', '{BIND_ADDRESS:s}:{PORT:s}'.format(**env)),
            ])
    elif kind == 'web':
        echo("-----> nginx will talk to the 'web' process via {BIND_ADDRESS:s}:{PORT:s}".format(**env), fg='yellow')
        settings.append(('attach-daemon', command))
    else:
        settings.append(('attach-daemon', command))
        
    if kind in ['wsgi','web']:
        settings.append(('log-format','%%(addr) - %%(user) [%%(ltime)] "%%(method) %%(uri) %%(proto)" %%(status) %%(size) "%%(referer)" "%%(uagent)" %%(msecs)ms'))
        
    # remove unnecessary variables from the env in nginx.ini
    for k in ['NGINX_ACL']:
        if k in env:
            del env[k]
    
    for k, v in env.items():
        settings.append(('env', '{k:s}={v}'.format(**locals())))

    with open(available, 'w') as h:
        h.write('[uwsgi]\n')
        for k, v in settings:
            h.write("{k:s} = {v}\n".format(**locals()))
    
    copyfile(available, enabled)

def do_restart(app):
    config = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))

    if len(config):
        echo("Restarting app '{}'...".format(app), fg='yellow')
        for c in config:
            remove(c)
        spawn_app(app)
    else:
        echo("Error: app '{}' not deployed!".format(app), fg='red')


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
        files[f] = open(f)
        inodes[f] = stat(f).st_ino
        files[f].seek(0, 2)
        
    longest = max(map(len, prefixes.values()))
    
    # Grab a little history (if any) 
    for f in filenames:
        for line in deque(open(f), catch_up):
            yield "{} | {}".format(prefixes[f].ljust(longest), line)

    while True:
        updated = False
        # Check for updates on every file
        for f in filenames:
            line = peek(files[f])
            if not line:
                continue
            else:
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
    
@group()
def piku():
    """The smallest PaaS you've ever seen"""
    pass

    
@piku.resultcallback()
def cleanup(ctx):
    """Callback from command execution -- add debugging to taste"""
    pass


# --- User commands ---

@piku.command("apps")
def list_apps():
    """List apps, e.g.: piku apps"""
    
    for a in listdir(APP_ROOT):
        echo(a, fg='green')


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
    for s in settings:
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            env[k] = v
            echo("Setting {k:s}={v} for '{app:s}'".format(**locals()), fg='white')
        except:
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
    
    for p in [join(x, app) for x in [APP_ROOT, GIT_ROOT, ENV_ROOT, LOG_ROOT]]:
        if exists(p):
            echo("Removing folder '{}'".format(p), fg='yellow')
            rmtree(p)

    for p in [join(x, '{}*.ini'.format(app)) for x in [UWSGI_AVAILABLE, UWSGI_ENABLED]]:
        g = glob(p)
        if len(g):
            for f in g:
                echo("Removing file '{}'".format(f), fg='yellow')
                remove(f)
                
    nginx_files = [join(NGINX_ROOT, "{}.{}".format(app,x)) for x in ['conf','sock','key','crt']]
    for f in nginx_files:
        if exists(f):
            echo("Removing file '{}'".format(f), fg='yellow')
            remove(f)

    acme_link = join(ACME_WWW, app)
    acme_certs = realpath(acme_link)
    if exists(acme_certs):
        echo("Removing folder '{}'".format(acme_certs), fg='yellow')
        rmtree(acme_certs)
        echo("Removing file '{}'".format(acme_link), fg='yellow')
        unlink(acme_link)

    
@piku.command("logs")
@argument('app')
def cmd_logs(app):
    """Tail running logs, e.g: piku logs <app>"""
    
    app = exit_if_invalid(app)

    logfiles = glob(join(LOG_ROOT, app, '*.log'))
    if len(logfiles):
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
    worker_count = {k:int(v) for k, v in parse_procfile(config_file).items()}
    deltas = {}
    for s in settings:
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            c = int(v) # check for integer value
            if c < 0:
                echo("Error: cannot scale type '{}' below 0".format(k), fg='red')
                return
            if k not in worker_count:
                echo("Error: worker type '{}' not present in '{}'".format(k, app), fg='red')
                return
            deltas[k] = c - worker_count[k]
        except:
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
    p = Popen(' '.join(cmd), stdin=stdin, stdout=stdout, stderr=stderr, env=environ, cwd=join(APP_ROOT,app), shell=True)
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

    echo("Running in Python {}".format(".".join(map(str,version_info))))
    
    # Create required paths
    for p in [APP_ROOT, GIT_ROOT, ENV_ROOT, UWSGI_ROOT, UWSGI_AVAILABLE, UWSGI_ENABLED, LOG_ROOT, NGINX_ROOT]:
        if not exists(p):
            echo("Creating '{}'.".format(p), fg='green')
            makedirs(p)
    
    # Set up the uWSGI emperor config
    settings = [
        ('chdir',           UWSGI_ROOT),
        ('emperor',         UWSGI_ENABLED),
        ('log-maxsize',     UWSGI_LOG_MAXSIZE),
        ('logto',           join(UWSGI_ROOT, 'uwsgi.log')),
        ('log-backupname',  join(UWSGI_ROOT, 'uwsgi.old.log')),
        ('socket',          join(UWSGI_ROOT, 'uwsgi.sock')),
        ('uid',             getpwuid(getuid()).pw_name),
        ('gid',             getgrgid(getgid()).gr_name),
        ('enable-threads',  'true'),
        ('threads',         '{}'.format(cpu_count() * 2)),
    ]
    with open(join(UWSGI_ROOT,'uwsgi.ini'), 'w') as h:
        h.write('[uwsgi]\n')
        # pylint: disable=unused-variable
        for k, v in settings:
            h.write("{k:s} = {v}\n".format(**locals()))

    # mark this script as executable (in case we were invoked via interpreter)
    if not(stat(PIKU_SCRIPT).st_mode & S_IXUSR):
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
        elif '-' == public_key_file:
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
    config = glob(join(UWSGI_ENABLED, '{}*.ini'.format(app)))

    if len(config):
        echo("Stopping app '{}'...".format(app), fg='yellow')
        for c in config:
            remove(c)
    else:
        echo("Error: app '{}' not deployed!".format(app), fg='red')
        
        
# --- Internal commands ---

@piku.command("git-hook")
@argument('app')
def cmd_git_hook(app):
    """INTERNAL: Post-receive git hook"""
    
    app = sanitize_app_name(app)
    repo_path = join(GIT_ROOT, app)
    app_path = join(APP_ROOT, app)
    
    for line in stdin:
        # pylint: disable=unused-variable
        oldrev, newrev, refname = line.strip().split(" ")
        # Handle pushes
        if not exists(app_path):
            echo("-----> Creating app '{}'".format(app), fg='green')
            makedirs(app_path)
            call('git clone --quiet {} {}'.format(repo_path, app), cwd=APP_ROOT, shell=True)
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
def cmd_git_receive_pack(app):
    """INTERNAL: Handle git upload pack for an app"""
    app = sanitize_app_name(app)
    env = globals()
    env.update(locals())
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    call('git-shell -c "{}" '.format(argv[1] + " '{}'".format(app)), cwd=GIT_ROOT, shell=True)


if __name__ == '__main__':
    piku()
