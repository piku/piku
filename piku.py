#!/usr/bin/env python

import os, sys, stat, re, shutil, socket, subprocess
from click import argument, command, group, option, secho as echo
from os.path import abspath, exists, join, dirname

# --- Globals - all tweakable settings are here ---

PIKU_ROOT = os.environ.get('PIKU_ROOT', join(os.environ['HOME'],'.piku'))
APP_ROOT = abspath(join(PIKU_ROOT, "apps"))
GIT_ROOT = abspath(join(PIKU_ROOT, "repos"))
UWSGI_ENABLED = abspath(join(PIKU_ROOT, "uwsgi-enabled"))
UWSGI_AVAILABLE = abspath(join(PIKU_ROOT, "uwsgi-available"))
LOG_ROOT = abspath(join(PIKU_ROOT, "logs"))


# --- Utility functions ---

def sanitize_app_name(app):
    """Sanitize the app name and build matching path"""
    app = "".join(c for c in app if c.isalnum() or c in ('.','_')).rstrip()
    return app


def get_free_port(address=""):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address,0))
    port = s.getsockname()[1]
    s.close()
    return port


def setup_authorized_keys(ssh_fingerprint, script_path, pubkey):
    """Sets up an authorized_keys file to redirect SSH commands"""
    authorized_keys = join(os.environ['HOME'],'.ssh','authorized_keys')
    if not exists(os.dirname(authorized_keys)):
        os.makedirs(os.dirname(authorized_keys))
    # Restrict features and force all SSH commands to go through our script 
    h = open(authorized_keys, 'a')
    h.write("""command="FINGERPRINT=%(ssh_fingerprint)s NAME=default %(script_path)s $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding %(pubkey)s\n""" % locals())
    h.close()


def do_deploy(app):
    """Deploy an app by resetting the work directory"""
    app_path = join(APP_ROOT, app)
    env = {'GIT_WORK_DIR': app_path}
    if exists(app_path):
        echo("-----> Deploying app '%s'" % app, fg='green')
        subprocess.call('git pull --quiet', cwd=app_path, env=env, shell=True)
        subprocess.call('git checkout -f', cwd=app_path, env=env, shell=True)
        # TODO: detect runtime and create uWSGI config
    else:
        echo("Error: app '%s' not found." % app, fg='red')
   

# --- CLI commands ---    
    
@group()
def piku():
    """Initialize paths"""
    for p in [APP_ROOT, GIT_ROOT, UWSGI_AVAILABLE, UWSGI_ENABLED, LOG_ROOT]:
        if not exists(p):
            os.makedirs(p)
    pass

    
@piku.resultcallback()
def cleanup(ctx):
    """Callback from command execution -- currently used for debugging"""
    print sys.argv[1:]
    #print os.environ


# Based on https://github.com/dokku/dokku/blob/master/plugins/git/commands#L103
@piku.command("git-receive-pack")
@argument('app')
def receive(app):
    """Handle git pushes for an app"""
    app = sanitize_app_name(app)
    hook_path = join(GIT_ROOT, app, 'hooks', 'post-receive')
    if not exists(hook_path):
        os.makedirs(dirname(hook_path))
        # Initialize the repository with a hook to this script
        subprocess.call("git init --quiet --bare " + app, cwd=GIT_ROOT, shell=True)
        h = open(hook_path,'w')
        h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="%s" $HOME/piku.py git-hook %s""" % (PIKU_ROOT, app))
        h.close()
        # Make the hook executable by our user
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' after it happens
    subprocess.call('git-shell -c "%s"' % " ".join(sys.argv[1:]), cwd=GIT_ROOT, shell=True)


@piku.command("deploy")
@argument('app')
def deploy_app(app):
    """Deploy an application"""
    app = sanitize_app_name(app)
    do_deploy(app)


@piku.command("ls")
def list_apps():
    """List applications"""
    for a in os.listdir(APP_ROOT):
        echo(a, fg='green')


@piku.command("disable")
@argument('app')
def disable_app(app):
    """Disable an application"""
    app = sanitize_app_name(app)
    config = join(UWSGI_ENABLED, app + '.ini')
    if exists(config):
        echo("Disabling app '%s'..." % app, fg='yellow')
        os.remove(config)


@piku.command("enable")
@argument('app')
def enable_app(app):
    """Enable an application"""
    app = sanitize_app_name(app)
    live_config = join(UWSGI_ENABLED, app + '.ini')
    config = join(UWSGI_AVAILABLE, app + '.ini')
    if exists(join(APP_ROOT, app)):
        if not exists(live_config):
            if exists(config):
                echo("Enabling app '%s'..." % app, fg='yellow')
                shutil.copyfile(config, live_config)
            else:
                echo("Error: app '%s' is not configured.", fg='red')
        else:
           echo("Warning: app '%s' is already enabled, skipping.", fg='yellow')       
    else:
        echo("Error: app '%s' does not exist.", fg='red')

@piku.command("destroy")
@argument('app')
def destroy_app(app):
    """Destroy an application"""
    app = sanitize_app_name(app)
    for p in [join(x, app) for x in [APP_ROOT, GIT_ROOT, LOG_ROOT]]:
        if exists(p):
            echo("Removing folder '%s'" % p, fg='yellow')
            shutil.rmtree(p)
    for p in [join(x, app + '.ini') for x in [UWSGI_AVAILABLE, UWSGI_ENABLED]]:
        if exists(p):
            echo("Removing file '%s'" % p, fg='yellow')
            os.remove(p)
             

@piku.command("git-hook")
@argument('app')
def git_hook(app):
    """Post-receive git hook"""
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
                subprocess.call('git clone --quiet %s %s' % (repo_path, app), cwd=APP_ROOT, shell=True)
            do_deploy(app)
        else:
            # Handle pushes to another branch
            print "receive-branch", app, newrev, refname
    print "hook", app, sys.argv[1:]
 
if __name__ == '__main__':
    piku()