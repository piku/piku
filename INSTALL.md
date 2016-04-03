# Installation

These installation notes should cover most Debian Linux variants (on any architecture). Very minor changes should be required to deploy on RHEL variants like CentOS, and there is specific emphasis on Raspbian because that's the typical deployment target.

You can, however, run `piku` on _any_ POSIX system where [uWSGI][uwsgi] and Python are available.

_TODO: describe the overall installation process._

## Setting up the `piku` user (Debian Linux, any architecture)

_TODO: describe the need for a separate user and why it's configured this way._

If you're impatient, you need to make sure you have a `~/.ssh/authorized_keys` file that looks like this:

```bash
command="FINGERPRINT=<your SSH fingerprint, not used right now> NAME=default /home/piku/piku.py $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding <your ssh key>
```

## uWSGI Installation (Debian Linux variants, any architecture)

[uWSGI][uwsgi] can be installed in a variety of fashions. However, these instructions assume you're installing it from source, and as such may vary from system to system.

### Raspbian

Since Raspbian's a fairly old distribution by now, its `uwsgi-*` packages are outdated (and depend on Python 2.6), so we have to compile and install our own version, as well as using an old-style `init` script to have it start automatically upon boot.

```bash
sudo apt-get install build-essential python-dev libpcre3-dev
# at the time of this writing, this installs 2.0.12
sudo pip install uwsgi
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku

# set up our init script
sudo cp uwsgi-piku.dist /etc/init.d/uwsgi-piku
sudo chmod +x /etc/init.d/uwsgi-piku
sudo update-rc.d uwsgi-piku defaults
sudo service uwsgi-piku start
```

## Go Installation (Debian Linux variants, on Raspberry Pi)

> This is **EXPERIMENTAL** and may not work at all.

### Raspbian

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
