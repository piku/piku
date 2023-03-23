# Installation on Ubuntu 22.04 LTS (Jammy)

> This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

`piku` setup is simplified in Jammy, since it can take advantage of some packaging improvements in [uWSGI][uwsgi] and does not require a custom `systemd` service. Since Jammy also ships with Python 3.10, this is an ideal environment for new deployments on both Intel and ARM devices.

## Dependencies

Before installing `piku`, you need to install the following packages:

```bash
sudo apt-get update
sudo apt-get install -y build-essential certbot git \
    libjpeg-dev libxml2-dev libxslt1-dev zlib1g-dev nginx \
    python3-certbot-nginx \
    python3-dev python3-pip python3-click python3-virtualenv \
    uwsgi uwsgi-plugin-asyncio-python3 uwsgi-plugin-gevent-python3 \
    uwsgi-plugin-python3 uwsgi-plugin-tornado-python3
```
## Setting up the `piku` user

`piku` requires a separate user account to run. To create a new user with the right group membership (we're using the built-in `www-data` group because it's generally thought of as a less-privileged group), enter the following commands:

```bash
# pick a username
export PAAS_USERNAME=piku
# create it
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data $PAAS_USERNAME
```

This user _is not supposed to login to your system_. Instead, you'll interact with `piku` via SSH, and set things up by using `su`:

```bash
# copy your public key to /tmp (I'm assuming it's the first entry in authorized_keys)
head -1 ~/.ssh/authorized_keys > /tmp/pubkey
# install piku and have it set up SSH keys and default files
sudo su - $PAAS_USERNAME -c "wget https://raw.githubusercontent.com/piku/piku/master/piku.py && python3 ~/piku.py setup && python3 ~/piku.py setup:ssh /tmp/pubkey"
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

[uWSGI][uwsgi] in Jammy requires very little configuration, since it is already properly packaged. All you need to do is place a link to the `piku` configuration file in `/etc/uwsgi/apps-enabled`:

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

## Set up systemd.path to reload nginx upon config changes

```bash
# Set up systemd.path to reload nginx upon config changes
sudo cp ./piku-nginx.{path, service} /etc/systemd/system/
sudo systemctl enable piku-nginx.{path,service}
sudo systemctl start piku-nginx.path
# Check the status of piku-nginx.service
systemctl status piku-nginx.path # should return `Active: active (waiting)`
# Restart NGINX
sudo systemctl restart nginx
```

## Notes

> This file was last updated on November 2018

[uwsgi]: https://github.com/unbit/uwsgi
