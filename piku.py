#!/usr/bin/env python

import os, sys, stat, re, shutil, socket
from click import argument, command, group, option, secho as echo
from collections import defaultdict, deque
from glob import glob
from os.path import abspath, basename, dirname, exists, getmtime, join, realpath, splitext
from subprocess import call, check_output
from time import sleep

# === Globals - all tweakable settings are here ===

PIKU_ROOT = os.environ.get('PIKU_ROOT', join(os.environ['HOME'],'.piku'))

APP_ROOT = abspath(join(PIKU_ROOT, "apps"))
ENV_ROOT = abspath(join(PIKU_ROOT, "envs"))
GIT_ROOT = abspath(join(PIKU_ROOT, "repos"))
LOG_ROOT = abspath(join(PIKU_ROOT, "logs"))
UWSGI_AVAILABLE = abspath(join(PIKU_ROOT, "uwsgi-available"))
UWSGI_ENABLED = abspath(join(PIKU_ROOT, "uwsgi-enabled"))
UWSGI_ROOT = abspath(join(PIKU_ROOT, "uwsgi"))


# === Utility functions ===

def sanitize_app_name(app):
    """Sanitize the app name and build matching path"""
    
    app = "".join(c for c in app if c.isalnum() or c in ('.','_')).rstrip()
    return app


def get_free_port(address=""):
    """Find a free TCP port (entirely at random)"""
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    
    authorized_keys = join(os.environ['HOME'],'.ssh','authorized_keys')
    if not exists(dirname(authorized_keys)):
        os.makedirs(dirname(authorized_keys))
    # Restrict features and force all SSH commands to go through our script 
    with open(authorized_keys, 'a') as h:
        h.write("""command="FINGERPRINT=%(ssh_fingerprint)s NAME=default %(script_path)s $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding %(pubkey)s\n""" % locals())
    os.chmod(authorized_keys, stat.S_IRUSR | stat.S_IWUSR)

        

def parse_procfile(filename):
    """Parses a Procfile and returns the worker types. Only one worker of each type is allowed."""
    
    workers = {}
    if not exists(filename):
        return None
    with open(filename, 'r') as procfile:
        for line in procfile:
            try:
                kind, command = map(lambda x: x.strip(), line.split(":", 1))
                if kind in ['web', 'worker', 'wsgi']:
                    workers[kind] = command
            except:
                echo("Warning: unrecognized Procfile declaration '%s'" % line, fg='yellow')
    if not len(workers):
        return {}
    # WSGI trumps regular web workers
    if 'wsgi' in workers:
        if 'web' in workers:
            del(workers['web'])
    return workers 


def parse_settings(filename, env={}):
    """Parses a settings file and returns a dict with environment variables"""

    def expandvars(buffer, env, default=None, skip_escaped=False):
        def replace_var(match):
            return env.get(match.group(2) or match.group(1), match.group(0) if default is None else default)
        pattern = (r'(?<!\\)' if skip_escaped else '') + r'\$(\w+|\{([^}]*)\})'
        return re.sub(pattern, replace_var, buffer)
    
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
    

def do_deploy(app):
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
            os.makedirs(log_path)
        workers = parse_procfile(procfile)
        if len(workers):
            if exists(join(app_path, 'requirements.txt')):
                echo("-----> Python app detected.", fg='green')
                deploy_python(app)
            # if exists(join(app_path, 'Godeps')) or len(glob(join(app_path),'*.go')):
            # Go deployment
            else:
                echo("-----> Could not detect runtime!", fg='red')
            # TODO: detect other runtimes
        else:
            echo("Error: Invalid Procfile for app '%s'." % app, fg='red')
    else:
        echo("Error: app '%s' not found." % app, fg='red')
        
        
def deploy_python(app):
    """Deploy a Python application"""
    
    virtualenv_path = join(ENV_ROOT, app)
    requirements = join(APP_ROOT, app, 'requirements.txt')

    first_time = False
    if not exists(virtualenv_path):
        echo("-----> Creating virtualenv for '%s'" % app, fg='green')
        os.makedirs(virtualenv_path)
        call('virtualenv %s' % app, cwd=ENV_ROOT, shell=True)
        first_time = True

    if first_time or getmtime(requirements) > getmtime(virtualenv_path):
        echo("-----> Running pip for '%s'" % app, fg='green')
        activation_script = join(virtualenv_path,'bin','activate_this.py')
        execfile(activation_script, dict(__file__=activation_script))
        call('pip install -r %s' % requirements, cwd=virtualenv_path, shell=True)
    spawn_app(app)

 
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
        'PATH': os.environ['PATH'],
        'VIRTUAL_ENV': virtualenv_path,
        'PORT': str(get_free_port()),
        'PWD': dirname(env_file),
    }
    
    # Load environment variables shipped with repo (if any)
    if exists(env_file):
        env.update(parse_settings(env_file, env))
    
    # Override with custom settings (if any)
    if exists(settings):
        env.update(parse_settings(settings, env))
    
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
                os.unlink(enabled)
    

def spawn_worker(app, kind, command, env, ordinal=1):
    """Set up and deploy a single worker of a given kind"""
    
    env_path = join(ENV_ROOT, app)
    available = join(UWSGI_AVAILABLE, '%s_%s.%d.ini' % (app, kind, ordinal))
    enabled = join(UWSGI_ENABLED, '%s_%s.%d.ini' % (app, kind, ordinal))

    settings = [
        ('virtualenv',      join(ENV_ROOT, app)),
        ('chdir',           join(APP_ROOT, app)),
        ('master',          'true'),
        ('project',         app),
        ('max-requests',    '1000'),
        ('processes',       '1'),
        ('procname-prefix', '%s:%s:' % (app, kind)),
        ('enable-threads',  'true'),
        ('log-maxsize',     '1048576'),
        ('logto',           '%s.%d.log' % (join(LOG_ROOT, app, kind), ordinal)),
        ('log-backupname',  '%s.%d.log.old' % (join(LOG_ROOT, app, kind), ordinal)),
    ]
    for k, v in env.iteritems():
        settings.append(('env', '%s=%s' % (k,v)))
        
    if kind == 'wsgi':
        echo("-----> Setting HTTP port to %s" % env['PORT'], fg='yellow')
        settings.extend([
            ('module', command),
            ('threads', '4'),
            ('http', ':%s' % env['PORT'])
        ])
    else:
        settings.append(('attach-daemon', command))
        
    with open(available, 'w') as h:
        h.write('[uwsgi]\n')
        for k, v in settings:
            h.write("%s = %s\n" % (k, v))
    
    shutil.copyfile(available, enabled)


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
        inodes[f] = os.stat(f).st_ino
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
                    if os.stat(f).st_ino != inodes[f]:
                        files[f] = open(f)
                        inodes[f] = os.stat(f).st_ino
                else:
                    filenames.remove(f)


# === CLI commands ===    
    
@group()
def piku():
    """The smallest PaaS you've ever seen"""
    pass

    
@piku.resultcallback()
def cleanup(ctx):
    """Callback from command execution -- currently used for debugging"""
    pass
    #print sys.argv[1:]
    #print os.environ


# --- User commands ---

@piku.command("config")
@argument('app')
def deploy_app(app):
    """Show application configuration"""
    
    app = sanitize_app_name(app)
    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    # no output if file is missing, for scripting purposes


@piku.command("config:get")
@argument('app')
@argument('setting')
def deploy_app(app, setting):
    """Retrieve a configuration setting"""
    
    app = sanitize_app_name(app)
    config_file = join(ENV_ROOT, app, 'ENV')
    if exists(config_file):
        env = parse_settings(config_file)
        if setting in env:
            echo("%s" % env[setting], fg='white')
    # no output if file or setting is missing, for scripting purposes


@piku.command("config:set")
@argument('app')
@argument('settings', nargs=-1)
def deploy_app(app, settings):
    """Set a configuration setting"""
    
    app = sanitize_app_name(app)
    config_file = join(ENV_ROOT, app, 'ENV')
    env = parse_settings(config_file)
    items = {}
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


@piku.command("config:live")
@argument('app')
def deploy_app(app):
    """Show live configuration settings"""
    
    app = sanitize_app_name(app)
    live_config = join(ENV_ROOT, app, 'LIVE_ENV')
    if exists(live_config):
        echo(open(live_config).read().strip(), fg='white')
    # no output if file or app is missing, for scripting purposes


@piku.command("deploy")
@argument('app')
def deploy_app(app):
    """Deploy an application"""
    
    app = sanitize_app_name(app)
    do_deploy(app)


@piku.command("destroy")
@argument('app')
def destroy_app(app):
    """Destroy an application"""
    
    app = sanitize_app_name(app)
    
    for p in [join(x, app) for x in [APP_ROOT, GIT_ROOT, ENV_ROOT, LOG_ROOT]]:
        if exists(p):
            echo("Removing folder '%s'" % p, fg='yellow')
            shutil.rmtree(p)

    for p in [join(x, '%s*.ini' % app) for x in [UWSGI_AVAILABLE, UWSGI_ENABLED]]:
        g = glob(p)
        if len(g):
            for f in g:
                echo("Removing file '%s'" % f, fg='yellow')
                os.remove(f)


@piku.command("disable")
@argument('app')
def disable_app(app):
    """Disable an application"""
    
    app = sanitize_app_name(app)
    config = glob(join(UWSGI_ENABLED, '%s*.ini' % app))
    
    if len(config):
        echo("Disabling app '%s'..." % app, fg='yellow')
        for c in config:
            os.remove(c)
    else:
        echo("Error: app '%s' not deployed!" % app, fg='red')


@piku.command("enable")
@argument('app')
def enable_app(app):
    """Enable an application"""
    app = sanitize_app_name(app)
    enabled = glob(join(UWSGI_ENABLED, '%s*.ini' % app))
    available = glob(join(UWSGI_AVAILABLE, '%s*.ini' % app))
    
    if exists(join(APP_ROOT, app)):
        if len(enabled):
            if len(available):
                echo("Enabling app '%s'..." % app, fg='yellow')
                for a in available:
                    shutil.copy(a, join(UWSGI_ENABLED, app))
            else:
                echo("Error: app '%s' is not configured.", fg='red')
        else:
           echo("Warning: app '%s' is already enabled, skipping.", fg='yellow')       
    else:
        echo("Error: app '%s' does not exist.", fg='red')


@piku.command("apps")
def list_apps():
    """List applications"""
    
    for a in os.listdir(APP_ROOT):
        echo(a, fg='green')


@piku.command("restart")
@argument('app')
def restart_app(app):
    """Restart an application"""
    
    app = sanitize_app_name(app)
    config = glob(join(UWSGI_ENABLED, '%s*.ini' % app))

    if len(config):
        echo("Restarting app '%s'..." % app, fg='yellow')
        for c in config:
            os.remove(c)
        do_deploy(app)
    else:
        echo("Error: app '%s' not deployed!" % app, fg='red')


@piku.command("ps")
@argument('app')
def deploy_app(app):
    """Show application worker count"""
    
    app = sanitize_app_name(app)
    config_file = join(ENV_ROOT, app, 'SCALING')
    if exists(config_file):
        echo(open(config_file).read().strip(), fg='white')
    # no output if file is missing, for scripting purposes


@piku.command("ps:scale")
@argument('app')
@argument('settings', nargs=-1)
def deploy_app(app, settings):
    """Show application configuration"""
    
    app = sanitize_app_name(app)
    if not exists(join(APP_ROOT, app)):
        return
    config_file = join(ENV_ROOT, app, 'SCALING')
    worker_count = {k:int(v) for k, v in parse_procfile(config_file).iteritems()}
    items = {}
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
    spawn_app(app, deltas)


@piku.command("setup")
def init_paths():
    """Initialize paths"""
    
    for p in [APP_ROOT, GIT_ROOT, ENV_ROOT, UWSGI_ROOT, UWSGI_AVAILABLE, UWSGI_ENABLED, LOG_ROOT]:
        if not exists(p):
            echo("Creating '%s'." % p, fg='green')
            os.makedirs(p)
    # mark this script as executable (in case we were invoked via interpreter)
    if not(os.stat(__file__).st_mode & stat.S_IXUSR):
        echo("Setting '%s' as executable." % this_script, fg='yellow')
        os.chmod(realpath(this_script), os.stat(this_script).st_mode | stat.S_IXUSR)         


@piku.command("setup:ssh")
@argument('public_key_file')
def add_key(public_key_file):
    """Set up a new SSH key"""
    
    if exists(public_key_file):
        try:
            fingerprint = check_output('ssh-keygen -lf %s' % public_key_file, shell=True).split(' ',4)[1]
            if re.match('(([0-9a-f]{2}\:){16})', '%s:' % fingerprint):
                key = open(public_key_file).read().strip()
                echo("Adding key '%s'." % fingerprint, fg='white')
                this_script = realpath(__file__)
                setup_authorized_keys(fingerprint, this_script, key)
        except:
            echo("Error: invalid public key file '%s'" % public_key_file, fg='red')
    

@piku.command("logs")
@argument('app')
def tail_logs(app):
    """Tail an application log"""
    
    app = sanitize_app_name(app)
    logfiles = glob(join(LOG_ROOT, app, '*.log'))
    if len(logfiles):
        for line in multi_tail(app, logfiles):
            echo(line.strip(), fg='white')
    else:
        echo("No logs found for app '%s'." % app, fg='yellow')


# --- Internal commands ---

@piku.command("git-hook")
@argument('app')
def git_hook(app):
    """INTERNAL: Post-receive git hook"""
    
    app = sanitize_app_name(app)
    repo_path = join(GIT_ROOT, app)
    app_path = join(APP_ROOT, app)
    
    for line in sys.stdin:
        oldrev, newrev, refname = line.strip().split(" ")
        #print "refs:", oldrev, newrev, refname
        if refname == "refs/heads/master":
            # Handle pushes to master branch
            if not exists(app_path):
                echo("-----> Creating app '%s'" % app, fg='green')
                os.makedirs(app_path)
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
        os.makedirs(dirname(hook_path))
        # Initialize the repository with a hook to this script
        call("git init --quiet --bare " + app, cwd=GIT_ROOT, shell=True)
        with open(hook_path,'w') as h:
            h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="%s" %s git-hook %s""" % (PIKU_ROOT, realpath(__file__), app))
        # Make the hook executable by our user
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    call('git-shell -c "%s"' % " ".join(sys.argv[1:]), cwd=GIT_ROOT, shell=True)
 
 
if __name__ == '__main__':
    piku()
