# Nodejs + Wisp Sample Application

This example demonstrates using `wisp`, a 3rd party npm installed binary to run scripts.

It is otherwise identical to the node example.

To publish this app to `piku`, make a copy of this folder and run the following commands:

```bash
git init .
git remote add piku piku@your_server:wispchat
git add .
git commit -a -m "initial commit"
git push piku master
```

Then you can set up an SSL cert and connect a domain by setting config variables like this:

```bash
ssh piku@your_server config:set wispchat NGINX_SERVER_NAME=your_server NGINX_HTTPS_ONLY=1
```

Then visit the site `your_server` and you will see a simple websocket chat application.
