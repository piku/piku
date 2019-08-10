# Installation on Raspbian Stretch or Buster

> This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

`piku` setup is simplified in modern Debian versions, since it can take advantage of some packaging improvements in [uWSGI][uwsgi] and does not require a custom `systemd` service. However, Stretch still ships with Python 3.5, which means it's not an ideal environment for new deployments on both Intel and ARM devices (Buster, in turn, ships with Python 3.7).

## Setting up your Raspberry Pi

Download and install [Raspbian](https://www.raspberrypi.org/downloads/raspbian/) onto an SD card.

After you install it is recommended that you do the following to update your installation to the latest available software.

```bash
# update apt-get
sudo apt-get update

# upgrade all software
sudo apt-get upgrade
```

Configure your installation.  It is recommended that `Change Password` from the default and setup `Locale Options` (Locale and Timezone) and `EXPAND FILESYSTEM`.  You will also want to `Enable SSH`.
```bash
# configure your installation
sudo raspi-config
```

At this point it is a good idea to `sudo shutdown -h now` and make a backup image of the card.

## Dependencies

Before installing `piku`, you need to install the following packages:

```bash
sudo apt-get install -y build-essential certbot git incron \
    libjpeg-dev libxml2-dev libxslt1-dev zlib1g-dev nginx \
    python-certbot-nginx python-dev python-pip python-virtualenv \
    python3-dev python3-pip python3-click python3-virtualenv \
    uwsgi uwsgi-plugin-asyncio-python3 uwsgi-plugin-gevent-python \
    uwsgi-plugin-python uwsgi-plugin-python3 uwsgi-plugin-tornado-python \
    uwsgi-plugin-lua5.1 uwsgi-plugin-lua5.2 uwsgi-plugin-luajit
```
## Setting up the `piku` user

`piku` requires a separate user account to run. To create a new user with the right group membership (we're using the built-in `www-data` group because it's generally thought of as a less-privileged group).  This user (`piku`) _is not supposed to login to your system_. Instead, you'll interact with `piku` via SSH, and set things up by using `su`.

To create the `piku` user account, enter the following commands:

```bash
# pick a username
export PAAS_USERNAME=piku
# create it
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data $PAAS_USERNAME
```

You will have to copy your ssh public key to the raspberry pi from your main system.  If you already have `ssh`d into your newly installed pi you can do the following:

```bash
# copy your public key to /tmp (I'm assuming it's the first entry in authorized_keys)
head -1 ~/.ssh/authorized_keys > /tmp/pubkey
# install piku and have it set up SSH keys and default files
sudo su - $PAAS_USERNAME -c "wget https://raw.githubusercontent.com/rcarmo/piku/master/piku.py && python3 ~/piku.py setup && python3 ~/piku.py setup:ssh /tmp/pubkey"
rm /tmp/pubkey
```

The `setup` output should be something like this:

```
Creating '/home/piku/.piku/apps'.
Creating '/home/piku/.piku/repos'.
Creating '/home/piku/.piku/envs'.
Creating '/home/piku/.piku/uwsgi'.
Creating '/home/piku/.piku/uwsgi-available'.
Creating '/home/piku/.piku/uwsgi-enabled'.
Creating '/home/piku/.piku/logs'.
Setting '/home/piku/piku.py' as executable.
```

## uWSGI Configuration

[uWSGI][uwsgi] in Stretch and Buster requires very little configuration, since it is already properly packaged. All you need to do is create a symlink to the `piku` configuration file in `/etc/uwsgi/apps-enabled`:

```bash
sudo ln /home/$PAAS_USERNAME/.piku/uwsgi/uwsgi.ini /etc/uwsgi/apps-enabled/piku.ini
sudo systemctl restart uwsgi
```

## `nginx` Configuration

`piku` requires you to edit `/etc/nginx/sites-available/default` to the following, so it can inject new site configurations into `nginx`:

```
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root /var/www/html;
    index index.html index.htm;
    server_name _;
    location / {
        try_files $uri $uri/ =404;
    }
}
# replace `PAAS_USERNAME` with the username you created.
include /home/PAAS_USERNAME/.piku/nginx/*.conf;
```

## `incron` Configuration

To detect configuration changes and tell `nginx` to activate new `piku` sites, we use `incron`. Create `/etc/incron.d/paas` with the following contents:

```bash
# replace `PAAS_USERNAME` with the username you created.
/home/PAAS_USERNAME/.piku/nginx IN_MODIFY,IN_NO_LOOP /bin/systemctl reload nginx
```

## Notes

> This file was last updated on June 2019

[uwsgi]: https://github.com/unbit/uwsgi
