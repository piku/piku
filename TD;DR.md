# Start here:

## DISCLAIMER!
### These instructions are correct as of April 1st 2016

Start by flashing a SD card with the latest Raspbian Jessie Lite image.
You can get it from [Raspberry Pi website](https://www.raspberrypi.org/downloads/raspbian/)

# Do this in your Raspberry Pi as 'pi' user

Boot it, launch *raspi-config* to perform (at least) the following configurations:
```
# as 'pi' user
sudo raspi-config
```

* 1) expand filesystem 
* 2) change default user password
* A3) setup memory split as you wish (I recommend 16Mb for GPU)

Optionally:
* 8) setup overclocking.

# Secure your installation

Delete generated SSH keys and recreate them.
(why this matters? [read it here](https://www.raspberrypi.org/forums/viewtopic.php?t=126892))
```
# as 'pi' user
sudo rm -v /etc/ssh/ssh_host_*
sudo dpkg-reconfigure openssh-server
sudo reboot
```

After the previous step you've created new SSH keys. 

Update installed packages
```
# as 'pi' user
sudo apt update
sudo apt upgrade
```

# Install additional packages

(needs validation if all packages are recent enough)
```
# as 'pi' user
sudo apt install -y python-virtualenv python-pip git uwsgi uwsgi-plugin-python
sudo pip install -U click
sudo reboot
```

# Meanwhile, go get the goodies while Raspberry Pi is rebootting



(We assume you know about ssh keys and have one "at hand", you'll need to copy it)

Clone [piku repo](https://github.com/rcarmo/piku) somewhere and copy files to your Raspberry Pi
```
# as yourself in your desktop/laptop computer
scp piku.py uwsgi-piku.service pi@your_machine:/tmp
scp your_public_ssh_key.pub    pi@your_machine:/tmp
```

# Back to the Pi

Prepare uWSGI (part one):
```
# as 'pi' user
sudo ln -s `which uwsgi` /usr/local/bin/uwsgi-piku
sudo systemctl disable uwsgi
sudo cp /tmp/uwsgi-piku.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable uwsgi-piku
```

Create 'piku' user and set it up
```
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
```
# as 'pi' user
sudo systemctl start uwsgi-piku
sudo systemctl status uwsgi-piku.service
```


# If you're still here, odds are your Pi is ready for work

Go back to your machine and try these commands:

```
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
  git-hook          INTERNAL: Post-receive git hook
  git-receive-pack  INTERNAL: Handle git pushes for an app
  logs              Tail an application log
  ps                Show application worker count
  ps:scale          Show application configuration
  restart           Restart an application
  setup             Initialize paths
  setup:ssh         Set up a new SSH key
Connection to your_machine closed.
```

If you find any bugs with this Gist, please let [Luis Correia](http://twitter.com/luisfcorreia) know ;)
