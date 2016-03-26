#!/usr/bin/env python

import os, sys, stat, re, socket, subprocess
from click import argument, command, group, option

APP_ROOT = os.environ.get('APP_ROOT', os.path.join(os.environ['HOME'],'.piku'))

# http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html

def app_name_and_path(app):
    """Sanitize the app name and build matching path"""
    app = "".join(c for c in app if c.isalnum() or c in ('.','_')).rstrip()
    return app, os.path.abspath(os.path.join(APP_ROOT, app))


def get_free_port(address=""):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address,0))
    port = s.getsockname()[1]
    s.close()
    return port


def setup_authorized_keys(ssh_fingerprint, script_path, pubkey):
    """Sets up an authorized_keys file to redirect SSH commands"""
    authorized_keys = os.path.join(os.environ['HOME'],'.ssh','authorized_keys')
    if not os.path.exists(os.dirname(authorized_keys)):
        os.makedirs(os.dirname(authorized_keys))
    # Restrict features and force all SSH commands to go through our script 
    h = open(authorized_keys, 'a')
    h.write("""command="FINGERPRINT=%(ssh_fingerprint)s NAME=default %(script_path)s $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding %(pubkey)s\n""" % locals())
    h.close()
    
    
@group(invoke_without_command=True)
def piku():
    pass
    
@piku.resultcallback()
def cleanup(ctx):
    """Callback from command execution -- currently used for debugging"""
    print sys.argv[1:]
    print os.environ

# https://github.com/dokku/dokku/blob/master/plugins/git/commands#L103
@piku.command("git-receive-pack")
@argument('app')
def receive(app):
    """Handle git pushes for an app, initializing the local repo if necessary"""
    app, app_path = app_name_and_path(app)
    hook_path = os.path.join(app_path, 'hooks', 'pre-receive')
    if not os.path.exists(app_path):
        os.makedirs(os.path.dirname(hook_path))
        os.chdir(os.path.dirname(app_path))
        # Initialize the repository with a hook to this script
        subprocess.call("git init --bare " + app + " > /dev/null", shell=True)
        h = open(hook_path,'w')
        h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="$PIKU_ROOT" $HOME/piku.py git-hook """ + app)
        h.close()
        # Make the hook executable by our user
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' while it happens
    os.chdir(os.path.dirname(app_path))
    subprocess.call('git-shell -c "%s"' % " ".join(sys.argv[1:]) , shell=True)
    print "receive", app


@piku.command("git-hook")
@argument('app')
def git_hook(app):
    """Pre-receive git hook"""
    app, app_path = app_name_and_path(app)
    for line in sys.stdin:
        oldrev, newrev, refname = line.strip().split(" ")
        if refname == "refs/heads/master":
            # Handle pushes to master branch
            print "receive", app, newrev
        else:
            # Handle pushes to another branch
            print "receive-branch", app, newrev, refname
    print "hook", app
    

@piku.command("git-upload-pack", help="handle Git receive")
@argument('app')
def pass_through(app):
    app, app_path = app_name_and_path(app)
    os.chdir(os.path.dirname(app_path))
    subprocess.call('git-shell -c "%s"' % " ".join(sys.argv[1:]) , shell=True)
    print "upload", app


if __name__ == '__main__':
    piku()