import os
from bottle import default_app, route, request, view, static_file, run

@route("/")
@view("base")
def default():
    result = {}
    table = ['<table class="u-full-width"><tbody>']
    for k, v in sorted(os.environ.items()):
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</tbody></table>')
    result['sys_data'] = '\n'.join(table)
    table = ['<table class="u-full-width"><tbody>']
    for k, v in sorted(dict(request.environ).items()):
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</tbody></table>')
    result['req_data'] = '\n'.join(table)
    return result

@route("/<path:path>")
def static(path):
    return static_file(path, root="static")

app = default_app()

if __name__ == '__main__':
    log.debug("Beginning run.")
    HTTP_PORT = int(environ.get('PORT', 8000))
    BIND_ADDRESS = environ.get('BIND_ADDRESS', '127.0.0.1')
    DEBUG = 'true' == environ.get('DEBUG', 'false').lower()
    run(host=BIND_ADDRESS, port=HTTP_PORT, debug=DEBUG)
