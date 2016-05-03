import os
from bottle import app, get, request

app = app()

@get("/")
def default():
    table = ['<table border="0">']
    for k, v in os.environ.iteritems():
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</table><table>')
    for k, v in request.environ.iteritems():
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</table>')
    return '\n'.join(table)

if __name__ == '__main__':
    run(port=int(os.environ.get("PORT",8080)))