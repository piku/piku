# Installation

As of June 2018, these documents are being split off into distribution-specific files in the same folder. If you are running `piku` on specific Linux versions, feel free to contribute your own instructions.

> Please use distro-specific instructions whenever possible, since there have been recent improvements in `uwsgi` packaging that greatly simplify installation. 

Also, `piku` now **requires Python 3** and a Linux distribution that runs `systemd`, such as Raspbian Jessie/Debian 8+/Ubuntu

These generic installation notes should cover most Debian Linux variants (on any architecture). Very minor changes should be required to deploy on RHEL variants like CentOS, and there is specific emphasis on Raspbian because that's the typical deployment target.

You can, however, run `piku` on any POSIX-like environment where you have Python, [uWSGI][uwsgi] and SSH.

For installation, you only require `root`/`sudo` access and the following files:

* `piku.py`
* `uwsgi-piku.service`
* `piku-nginx.path`
* `piku-nginx.service`
* `nginx-default.dist`

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

### Raspbian Jessie, Debian 8, Ubuntu 16.04

```bash
sudo apt-get install git python3-virtualenv python3-pip
sudo pip3 install -U click
```

### Raspbian Wheezy

```bash
sudo apt-get install git python3
sudo easy_install3 -U pip3
sudo pip3 install -U click virtualenv
```

These may or may not be installed already (`click` usually isn't). For Raspbian Wheezy this is the preferred approach, since current `apt` packages are fairly outdated.

## Initialization

To set everything up, type `python piku.py setup`:

```bash
sudo su - piku
python3 piku.py setup

Creating '/home/piku/.piku/apps'.
Creating '/home/piku/.piku/repos'.
Creating '/home/piku/.piku/envs'.
Creating '/home/piku/.piku/uwsgi'.
Creating '/home/piku/.piku/uwsgi-available'.
Creating '/home/piku/.piku/uwsgi-enabled'.
Creating '/home/piku/.piku/logs'.
Setting '/home/piku/piku.py' as executable.
```

## Setting up SSH access

If you don't have an SSH public key (or never used one before), you need to create one. The following instructions assume you're running some form of UNIX on your own machine (Windows users should check the documentation for their SSH client, unless you have [Cygwin][cygwin] installed).

**On your own machine**, issue the `ssh-keygen` command and follow the prompts:

```bash
ssh-keygen 

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
sudo su - piku
python3 piku.py setup:ssh /tmp/id_rsa.pub

Adding key '85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff'.
```

Now if you look at `.ssh/authorized_keys`, you should see something like this:

```bash
sudo su - piku
cat .ssh/authorized_keys
 
command="FINGERPRINT=85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff NAME=default /home/piku/piku.py $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDhTYZi/qeJBKgU3naI8FNjQgeMYnMsEtqrOmUc4lJoPNH2qBUTNkzwThGqsBm2HNLPURWMiEifBqF+kRixMud67Co7Zs9ys7pwFXkJB9bbZasd2JCGfVZ4UYXHnvgejSWkLAV/4bObhsbP2vWOmbbm91Cwn+PGJgoiW08yrd45lsDmgv9cUAJS3e8LkgVELvIDg49yM5ArB88oxwMEoUgWU2OniHmH0o1zw5I8WXHRhHOjb8cGsdTYfXEizRKKRTM2Mu6dKRt1GNL0UbWi8iS3uJHGD3AcQ4ApdMl5X0gTixKHponStOrSMy19/ltuIy8Sjr7KKPxz07ikMYr7Vpcp youruser@yourlaptop.lan
```

This line is what enables you to SSH (and perform `git` over SSH operations) to the `piku` user without a password, verifying your identity via your public key, restricting what can be done remotely and passing on to `piku` itself the commands you'll be issuing.

## Testing

From your machine, do:

```bash
ssh piku@pi.lan

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
  logs              Tail an application log
  ps                Show application worker count
  ps:scale          Show application configuration
  restart           Restart an application
  setup             Initialize paths
  setup:ssh         Set up a new SSH key
Connection to pi.lan closed.
```

And that's it, you're set. Now to configure [uWSGI][uwsgi], which is what `piku` relies upon to manage your apps at runtime.

## uWSGI Installation (Debian Linux variants, any architecture)

[uWSGI][uwsgi] can be installed in a variety of fashions. These instructions cover both pre-packaged and source installs depending on your system.

### Raspbian Jessie, Debian 8

In Raspbian Jessie, Debian 8 and other `systemd` distributions where [uWSGI][uwsgi] is already available pre-compiled (but split into a number of plugins), do the following:

```bash
# At the time of this writing, this installs uwsgi 2.0.7 on Raspbian Jessie.
# You can also install uwsgi-plugins-all if you want to get runtime support for other languages
sudo apt-get install uwsgi uwsgi-plugin-python3
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku
# disable the standard uwsgi startup script
sudo systemctl disable uwsgi

# add our own startup script
sudo cp /tmp/uwsgi-piku.service /etc/systemd/system/
sudo systemctl enable uwsgi-piku
sudo systemctl start uwsgi-piku

# check it's running
sudo systemctl status uwsgi-piku.service
```
**Important Note:** Make sure you run `piku.py setup` as outlined above before starting the service.

Also, please note that `uwsgi-piku.service`, as provided, creates a `/run/uwsgi-piku` directory for it to place socket files and sundry. This is not actually used at the moment, since the `uwsgi` socket file is placed inside the `piku` user directory for consistency across OS distributions. This will be cleaned up in a later release.

### Raspbian Wheezy

Since Raspbian Wheezy is a fairly old distribution by now, its `uwsgi-*` packages are completely outdated (and depend on Python 2.6), so we have to compile and install our own version, as well as using an old-style `init` script to have it start automatically upon boot.

```bash
sudo apt-get install build-essential python-dev libpcre3-dev
# At the time of this writing, this installs 2.0.12
sudo pip install uwsgi
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku

# set up our init script
sudo cp /tmp/uwsgi-piku.dist /etc/init.d/uwsgi-piku
sudo chmod +x /etc/init.d/uwsgi-piku
sudo update-rc.d uwsgi-piku defaults
sudo service uwsgi-piku start
```
**Important Note:** Make sure you run `python3 piku.py setup` as outlined above before starting the service.

### Ubuntu 14.04 LTS

This is a mix of both the above, and should change soon when we get 16.04. If you have trouble, install [uWSGI][uwsgi] via `pip` instead.

```bash
# At the time of this writing, this installs uwsgi 1.9.17 on Ubuntu 14.04 LTS.
# You can also install uwsgi-plugins-all if you want to get runtime support for other languages
sudo apt-get install uwsgi uwsgi-plugin-python3
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku

# set up our init script
sudo cp /tmp/uwsgi-piku.dist /etc/init.d/uwsgi-piku
sudo chmod +x /etc/init.d/uwsgi-piku
sudo update-rc.d uwsgi-piku defaults
sudo service uwsgi-piku start
```

## nginx Installation (Raspbian 8, Ubuntu 16.04)

*PLEASE NOTE:* There is a bug in `nginx` 1.6.2 under Raspbian 8 that causes it to try to allocate around a gigabyte of RAM when using SSL with SPDY. I seriously recommend using Ubuntu instead, if you can, or disabling SSL altogether.

```bash
sudo apt-get install nginx
# Set up nginx to pick up our config files
sudo cp /tmp/nginx.default.dist /etc/nginx/sites-available/default
# Set up systemd.path to reload nginx upon config changes
sudo cp ./piku-nginx.{path, service} /etc/systemd/system/
sudo systemctl enable piku-nginx.{path,service}
sudo systemctl start piku-nginx.path
# Check the status of piku-nginx.service
systemctl status piku-nginx.path # should return `Active: active (waiting)`
# Restart NGINX
sudo systemctl restart nginx
```

## Java 8 Installation (All Debian Linux variants, on Raspberry Pi)

To be able to deploy Java apps, we're going to need to install Java (and, since we're going to be doing so on ARM, it's best to use Oracle's runtime). To do that, we're going to use the `webupd8team` PPA, which has a (cross-platform) Java installer.

First, get rid of OpenJDK and import the PPA key:

```bash
sudo apt-get remove openjdk*
sudo apt-key adv --recv-key --keyserver keyserver.ubuntu.com EEA14886
```

### Raspbian Jessie

For Jessie, we're going to use the `trusty` version of the installer:

```bash
sudo tee /etc/apt/sources.list.d/webupd8team.list
deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main 
deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main
^D
```

### Ubuntu 16.04 for ARM

For Xenial, we're going to use its own version:

```bash
sudo tee /etc/apt/sources.list.d/webupd8team.list
deb http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main 
deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu xenial main
^D
```

Now perform the actual install:

```bash
sudo apt-get update
sudo apt-get install oracle-java8-installer oracle-java8-set-default
```

## Go Installation (All Debian Linux variants, on Raspberry Pi)

> This is **EXPERIMENTAL** and may not work at all.

### Raspbian Wheezy/Jessie

Since Raspbian's Go compiler is version 1.0.2, we need something more up-to-date.

1. Get an [ARM 6 binary tarball][goarm]
2. Unpack it under the `piku` user like such:

```bash
sudo su - piku
tar -zxvf /tmp/go1.5.3.linux-arm.tar.gz
# remove unnecessary files
rm -rf go/api go/blog go/doc go/misc go/test
```

3. Give it a temporary `GOPATH` and install `godep`:

```bash
sudo su - piku
GOROOT=$HOME/go GOPATH=$HOME/gopath PATH=$PATH:$HOME/go/bin go get github.com/tools/godep
# temporary workaround until this is fixed in godep or Go 1.7(?)
GOROOT=$HOME/go GOPATH=$HOME/gopath PATH=$PATH:$HOME/go/bin go get golang.org/x/sys/unix
```

_TODO: complete this._

[goarm]: http://dave.cheney.net/unofficial-arm-tarballs
[uwsgi]: https://github.com/unbit/uwsgi
[cygwin]: http://www.cygwin.com
