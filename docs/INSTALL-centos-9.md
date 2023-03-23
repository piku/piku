# Installation on CentOS 9

> This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

## Dependencies

Before installing `piku`, you need to install the following packages:

```bash
dnf in -y ansible nginx nodejs npm postgresql postgresql-server python3 uwsgi
```

## Set up the `piku` user

```bash
export PAAS_USERNAME=piku
adduser --groups nginx $PAAS_USERNAME
# copy & setup piku.py
sudo su - $PAAS_USERNAME -c "wget https://raw.githubusercontent.com/piku/piku/master/piku.py && python3 ~/piku.py setup"
```

## Set up SSH access

See INSTALL.md

## uWSGI Configuration

[FYI The uWSGI Emperor – multi-app deployment](https://uwsgi-docs.readthedocs.io/en/latest/Emperor.html)

```bash
sudo ln -s /home/$PAAS_USERNAME/.piku/uwsgi/uwsgi.ini /etc/uwsgi.d/piku.ini
sudo systemctl restart uwsgi
```

## `nginx` Configuration

[FYI Setting up and configuring NGINX](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/deploying_web_servers_and_reverse_proxies/setting-up-and-configuring-nginx_deploying-web-servers-and-reverse-proxies)

```bash
echo "include /home/$PAAS_USERNAME/.piku/nginx/*.conf;" > /usr/share/nginx/modules/piku.conf
sudo systemctl restart nginx
```

## Set up systemd.path to reload nginx upon config changes

```bash
# Set up systemd.path to reload nginx upon config changes
sudo su -
git clone https://github.com/piku/piku.git # need a copy of some files
cp -v piku/piku-nginx.{path,service} /etc/systemd/system/
systemctl enable piku-nginx.{path,service}
systemctl start piku-nginx.path
# Check the status of piku-nginx.service
systemctl status piku-nginx.path # should return `active: active (waiting)`
```

## Notes



[uwsgi]: https://github.com/unbit/uwsgi
