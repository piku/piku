Thanks to [jsenin](https://github.com/jsenin), `piku` currently has experimental support for external plugins via [#129](https://github.com/piku/piku/pull/129). 

Plugins are inserted into the commands listing and can perform arbitrary actions. At this moment there are no official plugins, but here is an example file that should be placed at `~/.piku/plugins/postgres/__init__.py` that could contain the commands to manage a Postgres database:

```python
import click

@click.group()
def postgres():
    """Postgres command plugin"""
    pass

@postgres.command("postgres:create")
@click.argument('name')
@click.argument('user')
@click.argument('password')
def postgres_create():
    """Postgres create a database"""
    pass

@postgres.command("postgres:drop")
@click.argument('name')
def postgres_drop():
    """Postgres drops a database"""
    pass

@postgres.command("postgres:import")
@click.argument('name')
def postgres_drop():
    """Postgres import a database"""
    pass

@postgres.command("postgres:dump")
@click.argument('name')
def postgres_drop():
    """Postgres dumps a database SQL"""
    pass

def cli_commands():
    return postgres
```
