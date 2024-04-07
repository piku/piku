# Installation

## TL;DR:

To install it on your server, `ssh` in as `root` and run this:

```bash
curl https://piku.github.io/get | sh
```

## Installation Methods

`piku` requires `Python 3`, [uWSGI][uwsgi], `ssh`, and a Linux distribution that runs `systemd`, such as Raspbian Jessie/Debian 8+/Ubuntu/Fedora/CentOS.

There are 3 main ways to install `piku` on a server:

1. Use [piku-bootstrap](https://github.com/piku/piku-bootstrap) to do it if your server is already provisioned (that is what the TL;DR command does)

2. Use `cloud-init` to do it automatically at VPS build time (see the [`cloud-init`](https://github.com/piku/cloud-init) repository, which has examples for most common cloud providers)

3. Manually: Follow the guide below or one of the platform-specfic guides. 

There is also an [Ansible playbook](https://github.com/piku/ansible-setup).

!!! Contributing
    If you are running `piku` on specific Linux versions, feel free to contribute your own instructions.

## Generic Installation Steps

### Set up the `piku` user

`piku` requires a separate user account to run. To create a new user with the right group membership (we're using the built-in `www-data` group because it's generally thought of as a less-privileged group), enter the following command:

```bash
# pick a username
export PAAS_USERNAME=piku
# create it
sudo adduser --disabled-password --gecos 'PaaS access' --ingroup www-data $PAAS_USERNAME
# copy & setup piku.py
sudo su - $PAAS_USERNAME -c "wget https://raw.githubusercontent.com/piku/piku/master/piku.py && python3 ~/piku.py setup"
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

### Set up `ssh` access

If you don't have an `ssh` public key (or never used one before), you need to create one. The following instructions assume you're running some form of UNIX on your own machine (Windows users should check the documentation for their `ssh` client, unless you have [Cygwin][cygwin] installed).

**On your own machine**, issue the `ssh-keygen` command and follow the prompts:

```bash
ssh-keygen 

Generating public/private rsa key pair.
Enter file in which to save the key (/home/youruser/.ssh/id_rsa): 
Created directory '/home/youruser/.ssh'.
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in /home/youruser/.ssh/id_rsa.
Your public key has been saved in /home/youruser/.ssh/id_rsa.pub.
The key fingerprint is:
85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff youruser@yourlaptop.lan
The key's randomart image is:
+--[ RSA 2048]----+
<...>
+-----------------+
```

Copy the resulting `id_rsa.pub` (or equivalent, just make sure it's the _public_ file) to your `piku` server and do the following:

```bash
sudo su - piku
python3 piku.py setup:ssh /tmp/id_rsa.pub

Adding key '85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff'.
```

Now if you look at `.ssh/authorized_keys`, you should see something like this:

```bash
sudo su - piku
cat .ssh/authorized_keys
 
command="FINGERPRINT=85:29:07:cb:de:ad:be:ef:42:65:00:c8:d2:6b:9e:ff NAME=default /home/piku/piku.py $SSH_ORIGINAL_COMMAND",no-agent-forwarding,no-user-rc,no-X11-forwarding,no-port-forwarding ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDhTYZi/qeJBKgU3naI8FNjQgeMYnMsEtqrOmUc4lJoPNH2qBUTNkzwThGqsBm2HNLPURWMiEifBqF+kRixMud67Co7Zs9ys7pwFXkJB9bbZasd2JCGfVZ4UYXHnvgejSWkLAV/4bObhsbP2vWOmbbm91Cwn+PGJgoiW08yrd45lsDmgv9cUAJS3e8LkgVELvIDg49yM5ArB88oxwMEoUgWU2OniHmH0o1zw5I8WXHRhHOjb8cGsdTYfXEizRKKRTM2Mu6dKRt1GNL0UbWi8iS3uJHGD3AcQ4ApdMl5X0gTixKHponStOrSMy19/ltuIy8Sjr7KKPxz07ikMYr7Vpcp youruser@yourlaptop.lan
```

This line is what enables you to `ssh` (and perform `git` over `ssh` operations) to the `piku` user without a password, verifying your identity via your public key, restricting what can be done remotely and passing on to `piku` itself the commands you'll be issuing.

### Test

From your machine, do:

```bash
ssh piku@pi.lan

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
Connection to pi.lan closed.
```

[uwsgi]: https://github.com/unbit/uwsgi
[cygwin]: http://www.cygwin.com