# Client-Side Plugins

Client-side plugins extend the `piku` command with local functionality. They enable commands that require coordination between your local machine and the piku server.

## How It Works

When you run `piku <command>`, the client checks for an executable at:

```
~/.piku/client-plugins/<command>
```

If found and executable, the plugin handles the command instead of sending it to the server.

For subcommands like `backup:data`, piku looks for a plugin matching the base command (`backup`).

## Plugin Interface

Plugins receive these arguments:

| Argument | Description | Example |
|----------|-------------|---------|
| `$1` | Server | `piku@myserver.com` |
| `$2` | App name | `myapp` |
| `$3` | Full command | `backup:data` |
| `$4+` | Additional arguments | (varies) |

Example plugin structure:

```sh
#!/bin/sh
server="$1"
app="$2"
cmd="$3"
shift 3
# remaining args now in $@

case "$cmd" in
    mycommand)
        # handle: piku mycommand
        ;;
    mycommand:sub)
        # handle: piku mycommand:sub
        ;;
esac
```

## Important: The Piku Shell

The piku user on the server has a restricted shell that only accepts piku commands (like `config:get`, `logs`, `run`, etc.), not arbitrary shell commands.

When writing plugins, keep this in mind:

| Method | Works? | Notes |
|--------|--------|-------|
| `ssh "$server" logs "$app"` | Yes | `logs` is a piku command |
| `ssh "$server" config:get "$app" VAR` | Yes | `config:get` is a piku command |
| `ssh "$server" "cat ~/.piku/apps/$app/file"` | No | `cat` is not a piku command |
| `scp "$server:.piku/apps/$app/file" .` | Yes | scp bypasses the piku shell |
| `ssh -N -L 8000:localhost:8000 "$server"` | Yes | `-N` means no command executed |

## Installation

```bash
# Create the plugins directory
mkdir -p ~/.piku/client-plugins

# Copy a plugin
cp examples/client-plugins/open ~/.piku/client-plugins/
chmod +x ~/.piku/client-plugins/open

# Or install directly from a URL
curl -sL https://example.com/my-plugin > ~/.piku/client-plugins/my-plugin
chmod +x ~/.piku/client-plugins/my-plugin
```

## Example Plugins

### open

Opens your app in the local browser.

```bash
piku open              # open app URL
piku open /admin       # open app URL with path
```

Uses `config:get` to fetch `NGINX_SERVER_NAME`, then opens the URL with the system browser.

### backup

Downloads app files to a local directory using `scp`.

```bash
piku backup                  # backup to ./appname-TIMESTAMP/
piku backup ./my-backups     # backup to custom directory
piku backup:data             # backup only data/ subdirectory
```

### tunnel

Creates SSH port tunnels to access services on the server.

```bash
piku tunnel 8000             # forward localhost:8000 to server:8000
piku tunnel 8000 3000        # forward localhost:3000 to server:8000
piku tunnel:db postgres      # forward postgres port (5432)
piku tunnel:db redis         # forward redis port (6379)
```

## Writing Your Own Plugins

1. Create an executable script in `~/.piku/client-plugins/`
2. Name it after the command you want to add
3. Parse `$1` (server), `$2` (app), `$3` (command), then `shift 3` for remaining args
4. Use `ssh "$server" <piku-command>` for piku commands
5. Use `scp` for file transfers
6. Use `ssh -N -L` for tunnels

### Template

```sh
#!/bin/sh
# ~/.piku/client-plugins/mycommand

server="$1"
app="$2"
cmd="$3"
shift 3

case "$cmd" in
    mycommand)
        echo "Running mycommand for $app on $server"
        # Your code here
        ;;
    mycommand:status)
        echo "Status subcommand"
        ;;
    *)
        echo "Unknown: $cmd"
        exit 1
        ;;
esac
```

## Combining with Server Plugins

Client plugins work well alongside server-side piku plugins. For example, a VS Code remote development setup might have:

- **Server plugin**: `code-tunnel` - manages VS Code tunnel daemon
- **Client plugin**: `code` - starts tunnel via server plugin, then launches local VS Code

```sh
#!/bin/sh
# Client plugin that coordinates with server plugin
server="$1"; app="$2"; cmd="$3"; shift 3

case "$cmd" in
    code)
        # Call server-side plugin to ensure tunnel is running
        tunnel_name=$(ssh "$server" code-tunnel:ensure "$app")
        # Launch local VS Code connected to the tunnel
        code --remote "tunnel+$tunnel_name" "/home/piku/.piku/apps/$app"
        ;;
    code:stop)
        ssh "$server" code-tunnel:stop "$app"
        ;;
esac
```
