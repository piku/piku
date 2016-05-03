import os
from bottle import default_app, route, request, view, static_file, run

@route("/")
@view("base")
def default():
    result = {}
    table = ['<table class="u-full-width"><tbody>']
    for k, v in sorted(os.environ.iteritems()):
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</tbody></table>')
    result['sys_data'] = '\n'.join(table)
    table = ['<table class="u-full-width"><tbody>']
    for k, v in sorted(dict(request.environ).iteritems()):
        table.append('<tr><th>%s</th><td>%s</td></tr>' % (k, v))
    table.append('</tbody></table>')
    result['req_data'] = '\n'.join(table)
    return result

@route("/<path:path>")
def static(path):
    return static_file(path, root="static")

app = default_app()

if __name__ == '__main__':
    run(port=int(os.environ.get("PORT",8080)))
