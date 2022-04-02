# Setting up a Raspberry Pi Piku Server from Scratch

## DISCLAIMER!

### These instructions are correct as of April 1st 2016

Start by flashing a SD card with [the latest Raspbian Jessie Lite image](https://www.raspberrypi.org/downloads/raspbian/).

# Do this in your Raspberry Pi as 'pi' user

Boot it, launch *raspi-config* to perform (at least) the following configuration:

```bash
# as 'pi' user
sudo raspi-config
```

* 1) expand filesystem 
* 2) change default user password
* 3) set up memory split as you wish (for a headless server, 16MB for GPU)

Optionally:

* 4) set up over-clocking.

# Secure your install

Delete the existing SSH keys and recreate them (why? [read this](https://www.raspberrypi.org/forums/viewtopic.php?t=126892)).

```bash
# as 'pi' user
sudo rm -v /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server
sudo reboot
```

This will recreate the server keys. Next, update your system:

```bash
# as 'pi' user
sudo apt update
sudo apt upgrade
```

# Install required packages

As of April 2016, the shipping versions with Raspbian are recent enough to run `piku`:

```bash
# as 'pi' user
sudo apt install -y python-virtualenv python-pip git uwsgi uwsgi-plugin-python nginx
sudo pip install -U click
sudo reboot
```

# Meanwhile, go get the goodies while Raspberry Pi is rebooting

(We assume you know about ssh keys and have one "at hand", you'll need to copy it)

Clone the [piku repo](https://github.com/piku/piku) somewhere and copy files to your Raspberry Pi

```bash
# as yourself in your desktop/laptop computer
scp piku.py uwsgi-piku.service nginx.default.dist pi@your_machine:/tmp
scp your_public_ssh_key.pub pi@your_machine:/tmp
```

# Back to the Pi

Prepare uWSGI (part one):
```bash
# as 'pi' user
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku
sudo systemctl disable uwsgi
sudo cp /tmp/uwsgi-piku.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable uwsgi-piku
```

Prepare nginx:

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

Create 'piku' user and set it up

```bash
# as 'pi' user
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data piku
sudo su - piku
# this is now done as 'piku' user
mkdir ~/.ssh
chmod 700 ~/.ssh
cp /tmp/piku.py ~/piku.py
python piku.py setup
python piku.py setup:ssh /tmp/id_rsa.pub
# return to 'pi' user
exit
```

Prepare uWSGI (part two):

```bash
# as 'pi' user
sudo systemctl start uwsgi-piku
sudo systemctl status uwsgi-piku.service
```


# If you're still here, odds are your Pi is ready for work

Go back to your machine and try these commands:

```bash
# as yourself in your desktop/laptop computer
ssh piku@your_machine

Usage: piku.py [OPTIONS] COMMAND [ARGS]...

  The smallest PaaS you've ever seen

Options:
  --help  Show this message and exit.

Commands:
  apps              List applications
  config            Show application configuration
  config:get        Retrieve a configuration setting
  config:live       Show live configuration settings
  config:set        Set a configuration setting
  deploy            Deploy an application
  destroy           Destroy an application
  disable           Disable an application
  enable            Enable an application
  logs              Tail an application log
  ps                Show application worker count
  ps:scale          Show application configuration
  restart           Restart an application
  setup             Initialize paths
  setup:ssh         Set up a new SSH key
Connection to your_machine closed.
```

If you find any bugs with this quickstart guide, please let [Luis Correia](http://twitter.com/luisfcorreia) know ;)
