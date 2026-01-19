# Upgrading to Multi-Environment Support

This guide explains how to upgrade an existing piku installation to support multiple environments (e.g., `piku`, `piku-staging`, `piku-prod`) on the same server.

## What Changed

The systemd service files have been converted to templates to support multiple piku users on the same server:

| Old File | New File |
|----------|----------|
| `uwsgi-piku.service` | `uwsgi-piku@.service` |
| `piku-nginx.path` | `piku-nginx@.path` |

The nginx configuration now uses a wildcard pattern to include configs from all piku users:

```nginx
# Old
include /home/piku/.piku/nginx/*.conf;

# New
include /home/piku*/.piku/nginx/*.conf;
```

## Migration Steps

### 1. Download New Systemd Files

```bash
cd /tmp
wget https://raw.githubusercontent.com/piku/piku/master/uwsgi-piku@.service
wget https://raw.githubusercontent.com/piku/piku/master/piku-nginx@.path
```

### 2. Stop and Disable Old Services

```bash
sudo systemctl stop uwsgi-piku piku-nginx.path
sudo systemctl disable uwsgi-piku piku-nginx.path
```

### 3. Remove Old Service Files

```bash
sudo rm /etc/systemd/system/uwsgi-piku.service
sudo rm /etc/systemd/system/piku-nginx.path
```

### 4. Install New Template Files

```bash
sudo cp /tmp/uwsgi-piku@.service /etc/systemd/system/
sudo cp /tmp/piku-nginx@.path /etc/systemd/system/
sudo systemctl daemon-reload
```

### 5. Enable and Start Services with Instance Name

```bash
sudo systemctl enable uwsgi-piku@piku
sudo systemctl start uwsgi-piku@piku
sudo systemctl enable piku-nginx@piku.path
sudo systemctl start piku-nginx@piku.path
```

### 6. Update Nginx Configuration

Edit your nginx configuration (usually `/etc/nginx/sites-available/default` or `/etc/nginx/conf.d/piku.conf`) and change:

```nginx
include /home/piku/.piku/nginx/*.conf;
```

to:

```nginx
include /home/piku*/.piku/nginx/*.conf;
```

Then reload nginx:

```bash
sudo systemctl reload nginx
```

### 7. Verify

Check that services are running:

```bash
systemctl status uwsgi-piku@piku
systemctl status piku-nginx@piku.path
```

## Adding Additional Environments

To add a staging environment (or any other environment):

### 1. Create the User

```bash
sudo adduser --disabled-password --gecos 'PaaS staging' --ingroup www-data piku-staging
```

### 2. Install piku for the New User

```bash
sudo su - piku-staging
wget https://raw.githubusercontent.com/piku/piku/master/piku.py
python3 ~/piku.py setup
exit
```

### 3. Enable Services for the New User

```bash
sudo systemctl enable uwsgi-piku@piku-staging
sudo systemctl start uwsgi-piku@piku-staging
sudo systemctl enable piku-nginx@piku-staging.path
sudo systemctl start piku-nginx@piku-staging.path
```

### 4. Set Up SSH Keys

Copy your SSH public key to the new user:

```bash
sudo su - piku-staging
python3 ~/piku.py setup:ssh /path/to/your/key.pub
exit
```

### 5. Deploy to the New Environment

From your development machine:

```bash
git remote add staging piku-staging@yourserver:myapp
git push staging main
```

## Using piku-bootstrap for Multi-Environment Setup

If using piku-bootstrap, you can install additional environments by setting the `PIKU_USER` environment variable:

```bash
# Install default piku environment
./piku-bootstrap install

# Install staging environment
PIKU_USER=piku-staging ./piku-bootstrap install
```
