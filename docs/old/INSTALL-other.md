# Installation on other platforms

> This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)


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

## Set up the `piku` user, Set up SSH access

See INSTALL.md


## uWSGI Installation (Debian Linux variants, any architecture)

[uWSGI][uwsgi] can be installed in a variety of fashions. These instructions cover both pre-packaged and source installs depending on your system.

### Raspbian Jessie, Debian 8

> **Warning**
> 
> These OS releases are no longer supported and these instructions are kept for reference purposes only.

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

> **Warning**
> 
> This OS release is no longer supported and these instructions are kept for reference purposes only.

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

> **Warning**
> 
> This OS release is no longer supported and these instructions are kept for reference purposes only.

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

> **Warning**
> 
> These OS releases are no longer supported and these instructions are kept for reference purposes only.

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

> **Warning**
> 
> OpenJDK 8 is no longer shipping with most distributions and these instructions are kept for reference purposes only.

To be able to deploy Java apps, we're going to need to install Java (and, since we're going to be doing so on ARM, it's best to use Oracle's runtime). To do that, we're going to use the `webupd8team` PPA, which has a (cross-platform) Java installer.

First, get rid of OpenJDK and import the PPA key:

```bash
sudo apt-get remove openjdk*
sudo apt-key adv --recv-key --keyserver keyserver.ubuntu.com EEA14886
```

### Raspbian Jessie

> **Warning**
> 
> This OS release is no longer supported and these instructions are kept for reference purposes only.

For Jessie, we're going to use the `trusty` version of the installer:

```bash
sudo tee /etc/apt/sources.list.d/webupd8team.list
deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main 
deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main
^D
```

### Ubuntu 16.04 for ARM

> **Warning**
> 
> This OS release is no longer supported and these instructions are kept for reference purposes only.

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

> **Warning**
> 
> Wheezy and Jessie are no longer supported and these instructions are kept for reference purposes only.

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
