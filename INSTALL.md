# Installation

These installation notes should cover most Debian Linux variants (on any architecture). Very minor changes should be required to deploy on RHEL variants like CentOS, and there is specific emphasis on Raspbian because that's the typical deployment target.

You can, however, run `piku` on any POSIX-like environment where you have Python, [uWSGI][uwsgi] and SSH.

For installation, you only require `root`/`sudo` access and the following two files:

* `piku.py`
* `uwsgi-piku.dist` (this one should only be necessary on older systems)

Copy them across to the machine you'll be using as a server before you get started with the rest.

## Setting up the `piku` user (Debian Linux, any architecture)

`piku` requires a separate user account to run. To create a new user with the right group membership (we're using the built-in `www-data` group because it's generally thought of as a less-privileged group), enter the following command:

```bash
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data piku
```

This user _is not supposed to login to your system_. Instead, you'll interact with `piku` via SSH, and set things up by using `su`:

```bash
sudo su - piku
mkdir ~/.ssh
chmod 700 ~/.ssh
# now copy the piku script to this user account
cp /tmp/piku.py ~/piku.py
```

## Dependencies

Before running `piku` for the first time, you need to install the following Python packages at the system level:

### Raspbian Jessie, Debian 8, Ubuntu

```bash
sudo apt-get install python-virtualenv python-pip
sudo pip install -U click
```

### Raspbian Wheezy
```bash
sudo easy_install pip
sudo pip install -U click virtualenv
```

These may or may not be installed already (`click` usually isn't). For Raspbian Wheezy this is the preferred approach, since current `apt` packages are fairly outdated.

## Setting up SSH access

If you don't have an SSH public key (or never used one before), you need to create one. The following instructions assume you're running some form of UNIX on your own machine (Windows users should check the documentation for their SSH client, unless you have [Cygwin][cygwin] installed).

**On your own machine**, issue the `ssh-keygen` command and follow the prompts:

```bash
$ ssh-keygen 
Generating public/private rsa key pair.
Enter file in which to save the key (/home/youruser/.ssh/id_rsa): 
Created directory '/home/youruser/.ssh'.
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in /home/youruser/.ssh/id_rsa.
Your public key has been saved in /home/youruser/.ssh/id_rsa.pub.
The key fingerprint is:
85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff youruser@yourlaptop.lan
The key's randomart image is:
+--[ RSA 2048]----+
<...>
+-----------------+
```

## Adding the key to `piku`

Copy the resulting `id_rsa.pub` (or equivalent, just make sure it's the _public_ file) to your `piku` server and do the following:

```bash
su - piku
python piku.py setup:ssh /tmp/id_rsa.pub
Adding key '85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff'.
Setting '/home/piku/piku.py' as executable.
```

Now if you look at `.ssh/authorized_keys`, you should see something like this:

```bash
cat .ssh/authorized_keys 
command="FINGERPRINT=85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff NAME=default /home/piku/piku.py $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDhTYZi/qeJBKgU3naI8FNjQgeMYnMsEtqrOmUc4lJoPNH2qBUTNkzwThGqsBm2HNLPURWMiEifBqF+kRixMud67Co7Zs9ys7pwFXkJB9bbZasd2JCGfVZ4UYXHnvgejSWkLAV/4bObhsbP2vWOmbbm91Cwn+PGJgoiW08yrd45lsDmgv9cUAJS3e8LkgVELvIDg49yM5ArB88oxwMEoUgWU2OniHmH0o1zw5I8WXHRhHOjb8cGsdTYfXEizRKKRTM2Mu6dKRt1GNL0UbWi8iS3uJHGD3AcQ4ApdMl5X0gTixKHponStOrSMy19/ltuIy8Sjr7KKPxz07ikMYr7Vpcp youruser@yourlaptop.lan
```

This line is what enables you to SSH (and perform `git` over SSH operations) to the `piku` user without a password, verifying your identity via your public key and restricting what can be done remotely and passing on to `piku` itself the commands you'll be issuing.

## Testing

From your machine, do:

```bash
$ ssh piku@pi.lan
Usage: piku.py [OPTIONS] COMMAND [ARGS]...

  The smallest PaaS you've ever seen

Options:
  --help  Show this message and exit.

Commands:
  apps              List applications
  config            Show application configuration
  config:get        Retrieve a configuration setting
  config:live       Show live configuration settings
  config:set        Set a configuration setting
  deploy            Deploy an application
  destroy           Destroy an application
  disable           Disable an application
  enable            Enable an application
  git-hook          INTERNAL: Post-receive git hook
  git-receive-pack  INTERNAL: Handle git pushes for an app
  logs              Tail an application log
  ps                Show application worker count
  ps:scale          Show application configuration
  restart           Restart an application
  setup:ssh         Set up a new SSH key
Connection to pi.lan closed.
```

And that's it, you're set. Now to configure [uWSGI][uwsgi], which is what `piku` relies upon to manage your apps at runtime.

## uWSGI Installation (Debian Linux variants, any architecture)

[uWSGI][uwsgi] can be installed in a variety of fashions. However, these instructions assume you're installing it from source, and as such may vary from system to system.

### Raspbian Jessie

```bash
# at the time of this writing, this installs uwsgi 2.0.7
sudo apt-get install uwsgi
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku
# disable the standard uwsgi startup script
sudo systemctl disable uwsgi
```

_TODO: complete this with a new systemd setup that covers the required paths for uWSGI._

### Raspbian Wheezy

Since Raspbian Wheezy is a fairly old distribution by now, its `uwsgi-*` packages are completely outdated (and depend on Python 2.6), so we have to compile and install our own version, as well as using an old-style `init` script to have it start automatically upon boot.

```bash
sudo apt-get install build-essential python-dev libpcre3-dev
# at the time of this writing, this installs 2.0.12
sudo pip install uwsgi
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku

# set up our init script
sudo cp /tmp/uwsgi-piku.dist /etc/init.d/uwsgi-piku
sudo chmod +x /etc/init.d/uwsgi-piku
sudo update-rc.d uwsgi-piku defaults
sudo service uwsgi-piku start
```

## Go Installation (All Debian Linux variants, on Raspberry Pi)

> This is **EXPERIMENTAL** and may not work at all.

### Raspbian Wheezy/Jessie

Since Raspbian's Go compiler is version 1.0.2, we need something more up-to-date.

1. Get an [ARM 6 binary tarball][goarm]
2. Unpack it under the `piku` user like such:

```bash
su - piku
cd ~
tar -zxvf /tmp/go1.5.3.linux-arm.tar.gz
```

3. Give it a temporary `GOPATH` and install `godep`:

```bash
su - piku
cd ~
GOROOT=$HOME/go GOPATH=$HOME/golibs PATH=$PATH:$HOME/go/bin go get github.com/tools/godep
```

_TODO: complete this._

[goarm]: http://dave.cheney.net/unofficial-arm-tarballs
[uwsgi]: https://github.com/unbit/uwsgi
[cygwin]: http://www.cygwin.com