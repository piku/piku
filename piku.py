#!/usr/bin/env python

import os, sys, stat, re, socket, subprocess
from click import argument, command, group, option

PIKU_ROOT = os.environ.get('PIKU_ROOT', os.path.join(os.environ['HOME'],'.piku'))
APP_ROOT = os.path.abspath(os.path.join(PIKU_ROOT, "apps"))
GIT_ROOT = os.path.abspath(os.path.join(PIKU_ROOT, "repos")) 

# http://off-the-stack.moorman.nu/2013-11-23-how-dokku-works.html

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
    #print os.environ

# https://github.com/dokku/dokku/blob/master/plugins/git/commands#L103
@piku.command("git-receive-pack")
@argument('app')
def receive(app):
    """Handle git pushes for an app, initializing the local repo if necessary"""
    app = sanitize_app_name(app)
    hook_path = os.path.join(GIT_ROOT, app, 'hooks', 'post-receive')
    if not os.path.exists(hook_path):
        os.makedirs(os.path.dirname(hook_path))
        # Initialize the repository with a hook to this script
        subprocess.call("git init --quiet --bare " + app, cwd=GIT_ROOT, shell=True)
        h = open(hook_path,'w')
        h.write("""#!/usr/bin/env bash
set -e; set -o pipefail;
cat | PIKU_ROOT="%s" $HOME/piku.py git-hook %s""" % (PIKU_ROOT, app))
        h.close()
        # Make the hook executable by our user
        os.chmod(hook_path, os.stat(hook_path).st_mode | stat.S_IXUSR)
    # Handle the actual receive. We'll be called with 'git-hook' while it happens
    subprocess.call('git-shell -c "%s"' % " ".join(sys.argv[1:]), cwd=GIT_ROOT, shell=True)


@piku.command("deploy")
@argument('app')
def deploy_app(app):
    app = sanitize_app_name(app)
    do_deploy(app)
    
def do_deploy(app):
    app_path = os.path.join(APP_ROOT, app)
    if os.path.exists(app_path):
        print "-----> Deploying", app
        subprocess.call('git checkout -q -f',cwd=app_path, env={'GIT_DIR':app_path,'GIT_WORK_TREE':app_path}, shell=True)
    else:
        print "Error: app %s not found." % app
   

@piku.command("git-hook")
@argument('app')
def git_hook(app):
    """Post-receive git hook"""
    app = sanitize_app_name(app)
    repo_path = os.path.join(GIT_ROOT, app)
    app_path = os.path.join(APP_ROOT, app)
    for line in sys.stdin:
        oldrev, newrev, refname = line.strip().split(" ")
        #print "refs:", oldrev, newrev, refname
        if refname == "refs/heads/master":
            # Handle pushes to master branch
            if not os.path.exists(app_path):
                print "-----> Creating", app
                os.makedirs(app_path)
                subprocess.call('git clone %s %s' % (repo_path, app), cwd=APP_ROOT, shell=True)
            else:
                print "-----> Updating", app
                subprocess.call('git pull %s' % repo_path, env={'GIT_DIR':repo_path,'GIT_WORK_TREE':app_path}, cwd=app_path, shell=True)
            do_deploy(app)
        else:
            # Handle pushes to another branch
            print "receive-branch", app, newrev, refname
    print "hook", app, sys.argv[1:]
 
if __name__ == '__main__':
    piku()