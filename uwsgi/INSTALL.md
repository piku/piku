# uWSGI Installation in Raspbian

Since Raspbian's a fairly old distribution by now, its `uwsgi` packages are outdated (and depend on Python 2.6), so we have to compile and install our own version, and use an `init` script:

```bash
sudo apt-get install build-essential python-dev libpcre3-dev
# at the time of this writing, this installs 2.0.12
sudo pip install uwsgi
# refer to our executable using a link, in case there are more versions installed
ln -s `which uwsgi` /usr/local/bin/uwsgi-piku

# set up our init script
sudo cp uwsgi-piku.sh /etc/init.d/uwsgi-piku
sudo chmod +x /etc/init.d/uwsgi-piku
sudo update-rc.d uwsgi-piku defaults
service uwsgi-piku start
```