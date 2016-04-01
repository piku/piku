# Python Sample Application

This is a simple Python app that demonstrates:

- HTTP port selection via the `PORT` variable (set in `ENV`)
- An independent worker process (that is auto-restarted upon exit) 

To publish this app to `piku`, make a copy of this folder and run the following commands:

```bash
cd python_copy
git init .
git remote add piku piku@your_server:python_example
git add .
git commit -a -m "initial commit"
git push piku master
```