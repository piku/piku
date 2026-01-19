# Installation on CentOS 9

!!! note
    This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

All steps done as root (or add sudo if you prefer).

## Dependencies

Before installing `piku`, you need to install the following packages:

```bash
dnf in -y ansible-core ansible-collection-ansible-posix ansible-collection-ansible-utils nginx nodejs npm openssl postgresql postgresql-server postgresql-contrib python3 python3-pip uwsgi uwsgi-logger-file uwsgi-logger-systemd
pip install click
```

## Set up the `piku` user

```bash
adduser --groups nginx piku
# copy & setup piku.py
su - piku -c "wget https://raw.githubusercontent.com/piku/piku/master/piku.py && python3 ~/piku.py setup"
```

## Set up SSH access

See INSTALL.md

## uWSGI Configuration

[FYI The uWSGI Emperor – multi-app deployment](https://uwsgi-docs.readthedocs.io/en/latest/Emperor.html)

```bash
mv /home/piku/.piku/uwsgi/uwsgi.ini /etc/uwsgi.d/piku.ini # linking alone increases the host attack service if one can get inside the piku user or one of its apps, so moving is safer
chown piku:piku /etc/uwsgi.d/piku.ini # In Tyrant mode (set by default in /etc/uwsgi.ini) the Emperor will run the vassal using the UID/GID of the vassal configuration file
systemctl restart uwsgi
journalctl -feu uwsgi # see logs
```

## `nginx` Configuration

[FYI Setting up and configuring NGINX](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/deploying_web_servers_and_reverse_proxies/setting-up-and-configuring-nginx_deploying-web-servers-and-reverse-proxies)

```bash
echo "include /home/piku/.piku/nginx/*.conf;" > /etc/nginx/conf.d/piku.conf
systemctl restart nginx
journalctl -feu nginx # see logs
```

## Set up systemd.path to reload nginx upon config changes

```bash
# Set up systemd.path to reload nginx upon config changes
su -
git clone https://github.com/piku/piku.git # need a copy of some files
cp -v piku/piku-nginx.{path,service} /etc/systemd/system/
systemctl enable piku-nginx.{path,service}
systemctl start piku-nginx.path
# Check the status of piku-nginx.service
systemctl status piku-nginx.path # should return `active: active (waiting)`
```

## Notes



[uwsgi]: https://github.com/unbit/uwsgi
