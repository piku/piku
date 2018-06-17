# Ubuntu 16.04

Full installation sequence on a blank Ubuntu 16.04 machine:

```bash
sudo apt-get update
sudo apt-get -y dist-upgrade
sudo apt-get -y autoremove
sudo apt-get install -y tmux vim htop fail2ban uwsgi uwsgi-plugin-python uwsgi-plugin-python3 uwsgi-plugin-asyncio-python3 uwsgi-plugin-gevent-python uwsgi-plugin-tornado-python nginx incron libxml2-dev libxslt1-dev python-dev zlib1g-dev build-essential git python-virtualenv python-pip
sudo pip install -U click pip
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data piku

# move to /tmp and grab our distribution files
cd /tmp
wget https://raw.githubusercontent.com/rcarmo/piku/master/piku.py
wget https://raw.githubusercontent.com/rcarmo/piku/master/incron.dist
wget https://raw.githubusercontent.com/rcarmo/piku/master/nginx.default.dist
wget https://raw.githubusercontent.com/rcarmo/piku/master/uwsgi-piku.service
# Set up nginx to pick up our config files
sudo cp /tmp/nginx.default.dist /etc/nginx/sites-available/default
# Set up incron to reload nginx upon config changes
sudo cp /tmp/incron.dist /etc/incron.d/piku
sudo systemctl restart incron
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
python piku.py setup
# Now import your SSH key using setup:ssh

sudo systemctl start uwsgi-piku
```
