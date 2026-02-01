# Ubuntu 16.04

!!! Note
    This is a standalone, distribution-specific version of `INSTALL.md`. You do not need to read or follow the original file, but can refer to it for generic steps like setting up SSH keys (which are assumed to be common knowledge here)

```bash
sudo apt-get update
sudo apt-get -y dist-upgrade
sudo apt-get -y autoremove
sudo apt-get install -y tmux vim htop fail2ban uwsgi uwsgi-plugin-python uwsgi-plugin-python3 uwsgi-plugin-asyncio-python3 uwsgi-plugin-gevent-python uwsgi-plugin-tornado-python nginx libxml2-dev libxslt1-dev python-dev zlib1g-dev build-essential git python3-virtualenv python3-pip python3-click
sudo pip3 install -U click pip
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data piku

# move to /tmp and grab our distribution files
cd /tmp
wget https://raw.githubusercontent.com/piku/piku/master/piku.py
wget https://raw.githubusercontent.com/piku/piku/master/piku-nginx.path
wget https://raw.githubusercontent.com/piku/piku/master/piku-nginx.service
wget https://raw.githubusercontent.com/piku/piku/master/nginx.default.dist
wget https://raw.githubusercontent.com/piku/piku/master/uwsgi-piku.service
# Set up nginx to pick up our config files
sudo cp /tmp/nginx.default.dist /etc/nginx/sites-available/default
# Set up systemd.path to reload nginx upon config changes
sudo cp ./piku-nginx.{path, service} /etc/systemd/system/
sudo systemctl enable piku-nginx.{path,service}
sudo systemctl start piku-nginx.path
# Restart NGINX
sudo systemctl restart nginx
sudo cp /tmp/uwsgi-piku.service /etc/systemd/system/
# refer to our executable using a link, in case there are more versions installed
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku
# disable the standard uwsgi startup script
sudo systemctl disable uwsgi
sudo systemctl enable uwsgi-piku
sudo su - piku
mkdir ~/.ssh
chmod 700 ~/.ssh
# now copy the piku script to this user account
cp /tmp/piku.py ~/piku.py
python3 piku.py setup
# Now import your SSH key using setup:ssh

sudo systemctl start uwsgi-piku
```
