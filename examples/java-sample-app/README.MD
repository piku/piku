[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
# Sample Java Application for `piku`

[![asciicast](https://asciinema.org/a/263991.svg)](https://asciinema.org/a/263991)

This is a simple Java app that demonstrates:

- HTTP port selection via the `PORT` variable (set in `ENV`)
* An independent worker process (that is auto-restarted upon exit) 

To publish this app to `piku`, clone the repository and run the following commands:

```bash
git clone git@github.com:matrixjnr/sample-java-app.git
```
Copy the contents to another folder excluding the `.git` folder.
Then initialize the new git repo.

```bash
git init
git add .
git commit -am "Your Message"
git remote add piku piku@your_server:sample-java-app
git push piku master
```
## Running the client

You should see `New client connected` in the logs.
The server returns Time to the user.

[![asciicast](https://asciinema.org/a/263980.svg)](https://asciinema.org/a/263980)

## To Note
Creating workers that have dependencies should be precompiled and packaged jar files with dependencies so as to be run as follows:
`worker: java -jar workersdir/test.jar`
Otherwise running workers from class files will throw errors.