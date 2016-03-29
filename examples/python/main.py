import os
from bottle import app, route

@route("/")
def default():
    table = ['<table border="0">']
    for k, v in os.environ.iteritems():
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</table>')
    return '\n'.join(table)
