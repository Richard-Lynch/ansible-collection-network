# service_frp_relay

Deploy an **frps** (fatedier/frp server) TCP relay on a public host.

## What it is

frps on a host with a public address forwards raw TCP (80/443 by default) to a private network. The
private side runs **frpc**, which dials OUT to the relay's control port, so a service behind NAT is
reachable at the relay's address without an inbound port on the private network. **TLS is not
terminated on the relay**: it passes through to the proxy behind frpc. This role manages the server
side only.

## What it does

Renders `frps.ini` (mode `0600`, it holds the token) and a docker-compose file, and converges the
relay only when either changed. It **disables the frps dashboard by default** — frps would otherwise
serve an admin panel on every interface with basic auth only. If re-enabled
(`frp_dashboard_enabled: true`), the template hard-binds it to `127.0.0.1` (reach it via an SSH
tunnel).

The container uses host networking, so the control port (`frp_bind_port`) and the relayed ports
(`frp_allow_ports`) listen on every interface of the relay host: that is the relay's purpose. The
control port is authenticated by `frp_token`; restrict the relayed ports further with the host's or
the provider's firewall.

## Inputs

See [`meta/argument_specs.yml`](meta/argument_specs.yml). Notable:

- **`frp_token`** (str, **required**, no default) — shared control-channel secret; must match
  `frpc.ini`. Never hardcode it. A placeholder-looking value (`CHANGEME`, `replace-me`, ...) or one
  shorter than 16 characters is refused before anything is rendered.
- **`frp_dashboard_pwd`** (str, no default) — required, and checked the same way, only when the
  dashboard is enabled.
- **`frp_dashboard_enabled`** (bool, default **false**) — keep off; loopback-only if enabled.
- `frp_version`, `frp_bind_port`, `frp_allow_ports`, `frp_deploy_dir` — relay config.

## Usage

```yaml
- hosts: relay
  roles:
    - role: richard_lynch.network.service_frp_relay
      frp_token: "{{ vault_frp_token }}"
```

## Safety / what it does NOT do

- **Applying a changed config restarts frps**, briefly dropping every relayed path. Gate a live run
  behind an explicit apply flag in the calling play rather than a default converge.
- It does not manage the frpc client or any DNS records.

## Testing

`molecule/default/` runs the role's own `tasks/_guards.yml` against placeholder, short and
dashboard-without-password inputs and requires each to be refused, then renders `frps.ini`
(dashboard off) and the compose file from sample vars and asserts the dashboard block is absent by
default. A full converge needs a real relay host.
