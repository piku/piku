# Django Sample Application

This is a simple Django app that demonstrates running the Django `collectstatic` and `migrate` tasks in the `release` worker phase.

To publish this app to `piku`, make a copy of this folder and run the following commands inside the copy:

```bash
git init .
git remote add piku piku@your_server:django_example
git add .
git commit -a -m "initial commit"
git push piku master
```

Then you can set up an SSL cert and connect a domain by setting config variables like this:

```bash
ssh piku@your_server config:set django_example NGINX_SERVER_NAME=your_server NGINX_HTTPS_ONLY=1
```

You can create a super user and set a password like this:

```bash
piku run django_example -- ./manage.py createsuperuser --email your@email.com --username admin --no-input
piku run django_example -- ./manage.py changepassword admin
```

You will not see a prompt after the second command but you can type a new password anyway and hit enter.
