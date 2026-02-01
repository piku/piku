# Installation on Ubuntu 18.04 LTS (Bionic)

!!! Note
    This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

`piku` setup is simplified in Bionic, since it can take advantage of some packaging improvements in [uWSGI][uwsgi] and does not require a custom `systemd` service. Since Bionic also ships with Python 3.6, this is an ideal environment for new deployments on both Intel and ARM devices.

## Dependencies

Before installing `piku`, you need to install the following packages:

```bash
sudo apt-get update
sudo apt-get install -y build-essential certbot git \
    libjpeg-dev libxml2-dev libxslt1-dev zlib1g-dev nginx \
    python-certbot-nginx python-dev python-pip python-virtualenv \
    python3-dev python3-pip python3-click python3-virtualenv \
    uwsgi uwsgi-plugin-asyncio-python3 uwsgi-plugin-gevent-python \
    uwsgi-plugin-python uwsgi-plugin-python3 uwsgi-plugin-tornado-python
```

## Set up the `piku` user, Set up SSH access

See INSTALL.md

## uWSGI Configuration

[uWSGI][uwsgi] requires very little configuration, since it is already properly packaged. All you need to do is place a link to the `piku` configuration file in `/etc/uwsgi/apps-enabled`:

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
