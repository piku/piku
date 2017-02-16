#!/usr/bin/env python

from click import argument, command, group, option, secho as echo
from collections import defaultdict, deque
from datetime import datetime
from fcntl import fcntl, F_SETFL, F_GETFL
from glob import glob
from hashlib import md5
from json import loads
from multiprocessing import cpu_count
from os import chmod, unlink, remove, stat, listdir, environ, makedirs, O_NONBLOCK
from os.path import abspath, basename, dirname, exists, getmtime, join, realpath, splitext
from re import sub
from shutil import copyfile, rmtree
from socket import socket, AF_INET, SOCK_STREAM
from sys import argv, stdin, stdout, stderr
from stat import S_IRUSR, S_IWUSR, S_IXUSR
from subprocess import call, check_output, Popen, STDOUT, PIPE 
from time import sleep
from urllib2 import urlopen

# === Globals - all tweakable settings are here ===

PIKU_ROOT = environ.get('PIKU_ROOT', join(environ['HOME'],'.piku'))

APP_ROOT = abspath(join(PIKU_ROOT, "apps"))
ENV_ROOT = abspath(join(PIKU_ROOT, "envs"))
GIT_ROOT = abspath(join(PIKU_ROOT, "repos"))
LOG_ROOT = abspath(join(PIKU_ROOT, "logs"))
NGINX_ROOT = abspath(join(PIKU_ROOT, "nginx"))
UWSGI_AVAILABLE = abspath(join(PIKU_ROOT, "uwsgi-available"))
UWSGI_ENABLED = abspath(join(PIKU_ROOT, "uwsgi-enabled"))
UWSGI_ROOT = abspath(join(PIKU_ROOT, "uwsgi"))
UWSGI_LOG_MAXSIZE = '1048576'
NGINX_TEMPLATE = """
upstream $APP {
  server $NGINX_SOCKET;
}
server {
  listen              [::]:80;
  listen              80;

  listen              [::]:$NGINX_SSL;
  listen              $NGINX_SSL;
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

  $NGINX_STATIC_MAPPINGS

  location    / {
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
}
"""

NGINX_STATIC_MAPPING = """
  location %(url)s {
      sendfile on;
      sendfile_max_chunk 1m;
      tcp_nopush on;
      directio 8m;
      aio threads;
      alias %(path)s;
  }
"""

# === Utility functions ===

def sanitize_app_name(app):
    """Sanitize the app name and build matching path"""
    
    app = "".join(c for c in app if c.isalnum() or c in ('.','_')).rstrip()
    return app


def exit_if_invalid(app):
    """Utility function for error checking upon command startup."""

    app = sanitize_app_name(app)
    if not exists(join(APP_ROOT, app)):
        echo("Error: app '%s' not found." % app, fg='red')
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
        for k, v in bag.iteritems():
            h.write('%s%s%s\n' % (k,separator,str(v)))


def setup_authorized_keys(ssh_fingerprint, script_path, pubkey):
    """Sets up an authorized_keys file to redirect SSH commands"""
    
    authorized_keys = join(environ['HOME'],'.ssh','authorized_keys')
    if not exists(dirname(authorized_keys)):
        makedirs(dirname(authorized_keys))
    # Restrict features and force all SSH commands to go through our script 
    with open(authorized_keys, 'a') as h:
        h.write("""command="FINGERPRINT=%(ssh_fingerprint)s NAME=default %(script_path)s $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding %(pubkey)s\n""" % locals())
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
                echo("Warning: unrecognized Procfile entry '%s'" % line, fg='yellow')
    if not len(workers):
        return {}
    # WSGI trumps regular web workers
    if 'wsgi' in workers:
        if 'web' in workers:
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
        if 'sbin' not in env['PATH']:
            env['PATH'] = env['PATH'] + ":/usr/sbin:/usr/local/sbin"
        return check_output(cmd, stderr=STDOUT, env=env, shell=True)
    except:
        return ""


def parse_settings(filename, env={}):
    """Parses a settings file and returns a dict with environment variables"""
    
    if not exists(filename):
        return {}
        
    with open(filename, 'r') as settings:
        for line in settings:
            if '#' == line[0]: # allow for comments
                continue
            try:
                k, v = map(lambda x: x.strip(), line.split("=", 1))
                env[k] = expandvars(v, env)
            except:
                echo("Error: malformed setting '%s', ignoring file." % line, fg='red')
                return {}
    return env
    

def do_deploy(app, deltas={}):
    """Deploy an app by resetting the work directory"""
    
    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    log_path = join(LOG_ROOT, app)

    env = {'GIT_WORK_DIR': app_path}
    if exists(app_path):
        echo("-----> Deploying app '%s'" % app, fg='green')
        call('git pull --quiet', cwd=app_path, env=env, shell=True)
        call('git checkout -f', cwd=app_path, env=env, shell=True)
        if not exists(log_path):
            makedirs(log_path)
        workers = parse_procfile(procfile)
        if workers and len(workers):
            if exists(join(app_path, 'requirements.txt')):
                echo("-----> Python app detected.", fg='green')
                deploy_python(app, deltas)
            elif exists(join(app_path, 'Godeps')) or len(glob(join(app_path,'*.go'))):
                echo("-----> Go app detected.", fg='green')
                deploy_go(app, deltas)
            else:
                echo("-----> Could not detect runtime!", fg='red')
            # TODO: detect other runtimes
        else:
            echo("Error: Invalid Procfile for app '%s'." % app, fg='red')
    else:
        echo("Error: app '%s' not found." % app, fg='red')
        
        
def deploy_go(app, deltas={}):
    """Deploy a Go application"""

    go_path = join(ENV_ROOT, app)
    deps = join(APP_ROOT, app, 'Godeps')

    first_time = False
    if not exists(go_path):
        echo("-----> Creating GOPATH for '%s'" % app, fg='green')
        makedirs(go_path)
        # copy across a pre-built GOPATH to save provisioning time 
        call('cp -a $HOME/gopath %s' % app, cwd=ENV_ROOT, shell=True)
        first_time = True

    if exists(deps):
        if first_time or getmtime(deps) > getmtime(go_path):
            echo("-----> Running godep for '%s'" % app, fg='green')
            env = {
                'GOPATH': '$HOME/gopath',
                'GOROOT': '$HOME/go',
                'PATH': '$PATH:$HOME/go/bin',
                'GO15VENDOREXPERIMENT': '1'
            }
            call('godep update ...', cwd=join(APP_ROOT, app), env=env, shell=True)
    spawn_app(app, deltas)


def deploy_python(app, deltas={}):
    """Deploy a Python application"""
    
    virtualenv_path = join(ENV_ROOT, app)
    requirements = join(APP_ROOT, app, 'requirements.txt')
    env_file = join(APP_ROOT, app, 'ENV')
    # Peek at environment variables shipped with repo (if any) to determine version
    env = {}
    if exists(env_file):
        env.update(parse_settings(env_file, env))

    version = int(env.get("PYTHON_VERSION", "2")) # implicit flooring of 3.6

    first_time = False
    if not exists(virtualenv_path):
        echo("-----> Creating virtualenv for '%s'" % app, fg='green')
        makedirs(virtualenv_path)
        call('virtualenv --python=python%d %s' % (version, app), cwd=ENV_ROOT, shell=True)
        first_time = True

    activation_script = join(virtualenv_path,'bin','activate_this.py')
    execfile(activation_script, dict(__file__=activation_script))

    if first_time or getmtime(requirements) > getmtime(virtualenv_path):
        echo("-----> Running pip for '%s'" % app, fg='green')
        call('pip install -r %s' % requirements, cwd=virtualenv_path, shell=True)
    spawn_app(app, deltas)

 
def spawn_app(app, deltas={}):
    """Create all workers for an app"""
    
    app_path = join(APP_ROOT, app)
    procfile = join(app_path, 'Procfile')
    workers = parse_procfile(procfile)
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
        'PATH': environ['PATH'],
        'PWD': dirname(env_file),
        'VIRTUAL_ENV': virtualenv_path,
    }
    
    # Load environment variables shipped with repo (if any)
    if exists(env_file):
        env.update(parse_settings(env_file, env))
    
    # Override with custom settings (if any)
    if exists(settings):
        env.update(parse_settings(settings, env))

    if 'web' in workers or 'wsgi' in workers:
        # Pick a port if none defined and we're not running under nginx
        if 'PORT' not in env and 'NGINX_SERVER_NAME' not in env:
            env['PORT'] = str(get_free_port())

        # Safe default for bind address            
        if 'BIND_ADDRESS' not in env:
            env['BIND_ADDRESS'] = '127.0.0.1'
                
        # Set up nginx if we have NGINX_SERVER_NAME set
        if 'NGINX_SERVER_NAME' in env:
            nginx = command_output("nginx -V")
            nginx_ssl = "443 ssl"
            if "--with-http_v2_module" in nginx:
                nginx_ssl += " http2"
            elif "--with-http_spdy_module" in nginx and "nginx/1.6.2" not in nginx: # avoid Raspbian bug
                nginx_ssl += " spdy"
        
            env.update({ 
                'NGINX_SSL': nginx_ssl,
                'NGINX_ROOT': NGINX_ROOT,
            })
            
            if 'wsgi' in workers:
                sock = join(NGINX_ROOT, "%s.sock" % app)
                env['NGINX_SOCKET'] = env['BIND_ADDRESS'] = "unix://" + sock
                if 'PORT' in env:
                    del env['PORT']
            else:
                env['NGINX_SOCKET'] = "%(BIND_ADDRESS)s:%(PORT)s" % env 
        
            domain = env['NGINX_SERVER_NAME'].split()[0]       
            key, crt = [join(NGINX_ROOT,'%s.%s' % (app,x)) for x in ['key','crt']]
            if not exists(key):
                call('openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj "/C=US/ST=NY/L=New York/O=Piku/OU=Self-Signed/CN=%(domain)s" -keyout %(key)s -out %(crt)s' % locals(), shell=True)
            
            # restrict access to server from CloudFlare IP addresses
            acl = []
            if env.get('NGINX_CLOUDFLARE_ACL', 'false').lower() == 'true':
                try:
                    cf = loads(urlopen('https://api.cloudflare.com/client/v4/ips').read())
                except Exception, e:
                    cf = defaultdict()
                    echo("-----> Could not retrieve CloudFlare IP ranges: %s" % e.text, fg="red")
                if cf['success'] == True:
                    for i in cf['result']['ipv4_cidrs']:
                        acl.append("allow %s;" % i)
                    for i in cf['result']['ipv6_cidrs']:
                        acl.append("allow %s;" % i)
                    # allow access from controlling machine
                    if 'SSH_CLIENT' in environ:
                        remote_ip = environ['SSH_CLIENT'].split()[0]
                        echo("-----> Adding your IP (%s) to nginx ACL" % remote_ip)
                        acl.append("allow %s;" % remote_ip)
                    acl.extend(["allow 127.0.0.1;","deny all;"])
            env['NGINX_ACL'] = " ".join(acl)

            env['NGINX_STATIC_MAPPINGS'] = ''
            
            # Get a mapping of /url:path1,/url2:path2
            static_paths = env.get('NGINX_STATIC_PATHS','')
            if len(static_paths):
                try:
                    items = static_paths.split(',')
                    for item in items:
                        static_url, static_path = item.split(':')
                        if static_path[0] != '/':
                            static_path = join(app_path, static_path)
                        env['NGINX_STATIC_MAPPINGS'] = env['NGINX_STATIC_MAPPINGS'] + NGINX_STATIC_MAPPING % {'url': static_url, 'path': static_path}
                except Exception as e:
                    print "Error %s in static path spec: should be /url1:path1[,/url2:path2], ignoring." % e
                    env['NGINX_STATIC_MAPPINGS'] = ''

            buffer = expandvars(NGINX_TEMPLATE, env)
            echo("-----> Setting up nginx for '%s:%s'" % (app, env['NGINX_SERVER_NAME']))
            with open(join(NGINX_ROOT,"%s.conf" % app), "w") as h:
                h.write(buffer)            

    # Configured worker count
    if exists(scaling):
        worker_count.update({k: int(v) for k,v in parse_procfile(scaling).iteritems()})
    
    to_create = {}
    to_destroy = {}    
    for k, v in worker_count.iteritems():
        to_create[k] = range(1,worker_count[k] + 1)
        if k in deltas and deltas[k]:
            to_create[k] = range(1, worker_count[k] + deltas[k] + 1)
            if deltas[k] < 0:
                to_destroy[k] = range(worker_count[k], worker_count[k] + deltas[k], -1)
            worker_count[k] = worker_count[k]+deltas[k]

    # Save current settings
    write_config(live, env)
    write_config(scaling, worker_count, ':')
    
    # Create new workers
    for k, v in to_create.iteritems():
        for w in v:
            enabled = join(UWSGI_ENABLED, '%s_%s.%d.ini' % (app, k, w))
            if not exists(enabled):
                echo("-----> Spawning '%s:%s.%d'" % (app, k, w), fg='green')
                spawn_worker(app, k, workers[k], env, w)
        
    # Remove unnecessary workers (leave logfiles)
    for k, v in to_destroy.iteritems():
        for w in v:
            enabled = join(UWSGI_ENABLED, '%s_%s.%d.ini' % (app, k, w))
            if exists(enabled):
                echo("-----> Terminating '%s:%s.%d'" % (app, k, w), fg='yellow')
                unlink(enabled)
    

def spawn_worker(app, kind, command, env, ordinal=1):
    """Set up and deploy a single worker of a given kind"""
    
    env['PROC_TYPE'] = kind
    env_path = join(ENV_ROOT, app)
    available = join(UWSGI_AVAILABLE, '%s_%s.%d.ini' % (app, kind, ordinal))
    enabled = join(UWSGI_ENABLED, '%s_%s.%d.ini' % (app, kind, ordinal))

    settings = [
        ('virtualenv',          join(ENV_ROOT, app)),
        ('chdir',               join(APP_ROOT, app)),
        ('master',              'true'),
        ('project',             app),
        ('max-requests',        env.get('UWSGI_MAX_REQUESTS', '1024')),
        ('listen',              env.get('UWSGI_LISTEN', '16')),
        ('processes',           env.get('UWSGI_PROCESSES', '1')),
        ('procname-prefix',     '%s:%s:' % (app, kind)),
        ('enable-threads',      env.get('UWSGI_ENABLE_THREADS', 'true').lower()),
        ('log-x-forwarded-for', env.get('UWSGI_LOG_X_FORWARDED_FOR', 'false').lower()),
        ('log-maxsize',         env.get('UWSGI_LOG_MAXSIZE', UWSGI_LOG_MAXSIZE)),
        ('logto',               '%s.%d.log' % (join(LOG_ROOT, app, kind), ordinal)),
        ('log-backupname',      '%s.%d.log.old' % (join(LOG_ROOT, app, kind), ordinal)),
    ]

    python_version = int(env.get('PYTHON_VERSION','2'))

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
            sock = join(NGINX_ROOT, "%s.sock" % app)
            echo("-----> Binding uWSGI to %s" % sock , fg='yellow')
            settings.extend([
                ('socket', sock),
                ('chmod-socket', '664'),
            ])
        else:
            echo("-----> Setting HTTP to listen on %(BIND_ADDRESS)s:%(PORT)s" % env, fg='yellow')
            settings.extend([
                ('http',        '%(BIND_ADDRESS)s:%(PORT)s' % env),
                ('http-socket', '%(BIND_ADDRESS)s:%(PORT)s' % env),
            ])
    elif kind == 'web':
        echo("-----> Setting HTTP to listen on %(BIND_ADDRESS)s:%(PORT)s" % env, fg='yellow')
        settings.extend([
            ('http',        '%(BIND_ADDRESS)s:%(PORT)s' % env),
            ('http-socket', '%(BIND_ADDRESS)s:%(PORT)s' % env),
        ])
    else:
        settings.append(('attach-daemon', command))
        
    if kind in ['wsgi','web']:
        settings.append(('log-format','%%(addr) - %%(user) [%%(ltime)] "%%(method) %%(uri) %%(proto)" %%(status) %%(size) "%%(referer)" "%%(uagent)" %%(msecs)ms'))
        
    # remove unnecessary variables from the env in nginx.ini
    for k in ['NGINX_ACL']:
        if k in env:
            del env[k]
    
    for k, v in env.iteritems():
        settings.append(('env', '%s=%s' % (k,v)))

    with open(available, 'w') as h:
        h.write('[uwsgi]\n')
        for k, v in settings:
            h.write("%s = %s\n" % (k, v))
    
    copyfile(available, enabled)


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
            yield "%s | %s" % (prefixes[f].ljust(longest), line)

    while True:
        updated = False
        # Check for updates on every file
        for f in filenames:
            line = peek(files[f])
            if not line:
                continue
            else:
                updated = True
                yield "%s | %s" % (prefixes[f].ljust(longest), line)
                
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
    """List applications"""
    
    for a in listdir(APP_ROOT):
        echo(a, fg='green')


@piku.command("config")
@argument('app')
def deploy_app(app):
    """Show application configuration"""
    
    app = exit_if_invalid(app)
    
    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    else:
        echo("Warning: app '%s' not deployed, no config found." % app, fg='yellow')


@piku.command("config:get")
@argument('app')
@argument('setting')
def deploy_app(app, setting):
    """Retrieve a configuration setting"""
    
    app = exit_if_invalid(app)
    
    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        env = parse_settings(config_file)
        if setting in env:
            echo("%s" % env[setting], fg='white')
    else:
        echo("Warning: no active configuration for '%s'" % app)


@piku.command("config:set")
@argument('app')
@argument('settings', nargs=-1)
def deploy_app(app, settings):
    """Set a configuration setting"""
    
    app = exit_if_invalid(app)
    
    config_file = join(ENV_ROOT, app, 'ENV')
    env = parse_settings(config_file)
    for s in settings:
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            env[k] = v
            echo("Setting %s=%s for '%s'" % (k, v, app), fg='white')
        except:
            echo("Error: malformed setting '%s'" % s, fg='red')
            return
    write_config(config_file, env)
    do_deploy(app)


@piku.command("config:unset")
@argument('app')
@argument('settings', nargs=-1)
def deploy_app(app, settings):
    """Set a configuration setting"""
    
    app = exit_if_invalid(app)
    
    config_file = join(ENV_ROOT, app, 'ENV')
    env = parse_settings(config_file)
    for s in settings:
        if s in env:
            del env[s]
            echo("Unsetting %s for '%s'" % (s, app), fg='white')
    write_config(config_file, env)
    do_deploy(app)


@piku.command("config:live")
@argument('app')
def deploy_app(app):
    """Show live configuration settings"""
    
    app = exit_if_invalid(app)

    live_config = join(ENV_ROOT, app, 'LIVE_ENV')
    if exists(live_config):
        echo(open(live_config).read().strip(), fg='white')
    else:
        echo("Warning: app '%s' not deployed, no config found." % app, fg='yellow')


@piku.command("deploy")
@argument('app')
def deploy_app(app):
    """Deploy an application"""
    
    app = exit_if_invalid(app)
    do_deploy(app)


@piku.command("destroy")
@argument('app')
def destroy_app(app):
    """Destroy an application"""
    
    app = exit_if_invalid(app)
    
    for p in [join(x, app) for x in [APP_ROOT, GIT_ROOT, ENV_ROOT, LOG_ROOT]]:
        if exists(p):
            echo("Removing folder '%s'" % p, fg='yellow')
            rmtree(p)

    for p in [join(x, '%s*.ini' % app) for x in [UWSGI_AVAILABLE, UWSGI_ENABLED]]:
        g = glob(p)
        if len(g):
            for f in g:
                echo("Removing file '%s'" % f, fg='yellow')
                remove(f)
                
    nginx_files = [join(NGINX_ROOT, "%s.%s" % (app,x)) for x in ['conf','sock','key','crt']]
    for f in nginx_files:
        if exists(f):
            echo("Removing file '%s'" % f, fg='yellow')
            remove(f)

    
@piku.command("logs")
@argument('app')
def tail_logs(app):
    """Tail an application log"""
    
    app = exit_if_invalid(app)

    logfiles = glob(join(LOG_ROOT, app, '*.log'))
    if len(logfiles):
        for line in multi_tail(app, logfiles):
            echo(line.strip(), fg='white')
    else:
        echo("No logs found for app '%s'." % app, fg='yellow')


@piku.command("ps")
@argument('app')
def deploy_app(app):
    """Show application worker count"""
    
    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'SCALING')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    else:
        echo("Error: no workers found for app '%s'." % app, fg='red')


@piku.command("ps:scale")
@argument('app')
@argument('settings', nargs=-1)
def deploy_app(app, settings):
    """Show application configuration"""
    
    app = exit_if_invalid(app)

    config_file = join(ENV_ROOT, app, 'SCALING')
    worker_count = {k:int(v) for k, v in parse_procfile(config_file).iteritems()}
    deltas = {}
    for s in settings:
        try:
            k, v = map(lambda x: x.strip(), s.split("=", 1))
            c = int(v) # check for integer value
            if c < 0:
                echo("Error: cannot scale type '%s' below 0" % k, fg='red')
                return
            if k not in worker_count:
                echo("Error: worker type '%s' not present in '%s'" % (k, app), fg='red')
                return
            deltas[k] = c - worker_count[k]
        except:
            echo("Error: malformed setting '%s'" % s, fg='red')
            return
    do_deploy(app, deltas)


@piku.command("run")
@argument('app')
@argument('cmd', nargs=-1)
def deploy_app(app, cmd):
    """Run a command inside the app, e.g.: ls -- -al"""

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
def restart_app(app):
    """Restart an application"""
    
    app = exit_if_invalid(app)
    
    config = glob(join(UWSGI_ENABLED, '%s*.ini' % app))

    if len(config):
        echo("Restarting app '%s'..." % app, fg='yellow')
        for c in config:
            remove(c)
        do_deploy(app)
    else:
        echo("Error: app '%s' not deployed!" % app, fg='red')


@piku.command("setup")
def init_paths():
    """Initialize environment"""
    
    # Create required paths
    for p in [APP_ROOT, GIT_ROOT, ENV_ROOT, UWSGI_ROOT, UWSGI_AVAILABLE, UWSGI_ENABLED, LOG_ROOT, NGINX_ROOT]:
        if not exists(p):
            echo("Creating '%s'." % p, fg='green')
            makedirs(p)
    
    # Set up the uWSGI emperor config
    settings = [
        ('chdir',           UWSGI_ROOT),
        ('emperor',         UWSGI_ENABLED),
        ('log-maxsize',     UWSGI_LOG_MAXSIZE),
        ('logto',           join(UWSGI_ROOT, 'uwsgi.log')),
        ('log-backupname',  join(UWSGI_ROOT, 'uwsgi.old.log')),
        ('socket',          join(UWSGI_ROOT, 'uwsgi.sock')),
        ('enable-threads',  'true'),
        ('threads',         '%d' % (cpu_count() * 2)),
    ]
    with open(join(UWSGI_ROOT,'uwsgi.ini'), 'w') as h:
        h.write('[uwsgi]\n')
        for k, v in settings:
            h.write("%s = %s\n" % (k, v))

    # mark this script as executable (in case we were invoked via interpreter)
    this_script = realpath(__file__)
    if not(stat(this_script).st_mode & S_IXUSR):
        echo("Setting '%s' as executable." % this_script, fg='yellow')
        chmod(this_script, stat(this_script).st_mode | S_IXUSR)         


@piku.command("setup:ssh")
@argument('public_key_file')
def add_key(public_key_file):
    """Set up a new SSH key"""
    
    if exists(public_key_file):
        try:
            fingerprint = check_output('ssh-keygen -lf %s' % public_key_file, shell=True).split(' ',4)[1]
            key = open(public_key_file).read().strip()
            echo("Adding key '%s'." % fingerprint, fg='white')
            setup_authorized_keys(fingerprint, realpath(__file__), key)
        except:
            echo("Error: invalid public key file '%s'" % public_key_file, fg='red')
    else:
        echo("Error: public key file '%s' not found." % public_key_file, fg='red')


@piku.command("stop")
@argument('app')
def stop_app(app):
    """Stop an application"""
    
    app = exit_if_invalid(app)
    
    config = glob(join(UWSGI_ENABLED, '%s*.ini' % app))

    if len(config):
        echo("Stopping app '%s'..." % app, fg='yellow')
        for c in config:
            remove(c)
    else:
        echo("Error: app '%s' not deployed!" % app, fg='red')
        
        
# --- Internal commands ---

@piku.command("git-hook")
@argument('app')
def git_hook(app):
    """INTERNAL: Post-receive git hook"""
    
    app = sanitize_app_name(app)
    repo_path = join(GIT_ROOT, app)
    app_path = join(APP_ROOT, app)
    
    for line in stdin:
        oldrev, newrev, refname = line.strip().split(" ")
        #print "refs:", oldrev, newrev, refname
        if refname == "refs/heads/master":
            # Handle pushes to master branch
            if not exists(app_path):
                echo("-----> Creating app '%s'" % app, fg='green')
                makedirs(app_path)
                call('git clone --quiet %s %s' % (repo_path, app), cwd=APP_ROOT, shell=True)
            do_deploy(app)
        else:
            # TODO: Handle pushes to another branch
            echo("receive-branch '%s': %s, %s" % (app, newrev, refname))


@piku.command("git-receive-pack")
@argument('app')
def receive(app):
    """INTERNAL: Handle git pushes for an app"""
    
    app = sanitize_app_name(app)
    hook_path = join(GIT_ROOT, app, 'hooks', 'post-receive')
    
    if not exists(hook_path):
        makedirs(dirname(hook_path))
        # Initialize the repository with a hook to this script
        call("git init --quiet --bare " + app, cwd=GIT_ROOT, shell=True)
        with open(hook_path,'w') as h:
            h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="%s" %s git-hook %s""" % (PIKU_ROOT, realpath(__file__), app))
        # Make the hook executable by our user
        chmod(hook_path, stat(hook_path).st_mode | S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    call('git-shell -c "%s"' % " ".join(argv[1:]), cwd=GIT_ROOT, shell=True)
 
 
if __name__ == '__main__':
    piku()
