# service_cloudflared

Deploy a **Cloudflare Tunnel client** (`cloudflared`) that exposes a service through Cloudflare
**without opening any inbound port** on the host. `cloudflared` only makes outbound connections to
Cloudflare's edge — the host never listens on a public port for the tunneled service.

## What it does

- Renders a docker-compose file and converges a single `cloudflared` container running
  `tunnel run` with `TUNNEL_TOKEN` from the environment.
- Image is **pinned** (`cloudflare/cloudflared:2025.7.0` by default); never use a floating tag, so
  an upgrade is a reviewed change.
- Refuses to run with the shipped placeholder token — `cloudflared_tunnel_token` must be supplied
  (from a secret store) or the role fails loudly before rendering anything.
- The compose file holds the token, so it is written `0600`.

## What it deliberately does NOT do

- **Does not write a local ingress config file.** Hostname → service routing (e.g.
  `status.example.com` → `http://127.0.0.1:3001`) and any **Cloudflare Access policy** protecting
  that hostname are configured on the tunnel in Cloudflare (dashboard or API — Zero Trust → Networks
  → Tunnels → Public Hostname, and Zero Trust → Access → Applications). This role only runs
  `cloudflared tunnel run` with a token — it has no way to see or enforce what Cloudflare does with
  that tunnel. **This means the role cannot verify an Access policy exists.** An unprotected public
  hostname behind a tunnel is reachable from anywhere with no IP filter at all — worse than no
  tunnel, because it looks protected but isn't. Confirm the Access policy after creating every new
  public hostname.
- **Does not terminate TLS locally.** Cloudflare terminates TLS at its edge for the public hostname;
  the hop from `cloudflared` to a service on the same host (e.g. `127.0.0.1:3001`) is plain HTTP over
  loopback. That hop never leaves the host, so local TLS on it adds machinery and no protection.

## Several instances

The role can run more than once — on different hosts, or twice on one host — each instance with its
own tunnel. **Every instance needs a DIFFERENT Cloudflare Tunnel and a DIFFERENT token.** Never
reuse a token across instances: set `cloudflared_container_name` / `cloudflared_config_dir` /
`cloudflared_tunnel_token` distinctly per deployment so two instances never collide or share a
tunnel identity.

## Cloudflare-side steps (this role cannot do these)

For a NEW `cloudflared` instance:

1. **Create the tunnel**: Zero Trust → Networks → Tunnels → Create a tunnel → *Cloudflared* → name it
   clearly (e.g. `status-tunnel`). Copy the tunnel **token** shown during setup.
2. **Store the token in your secret store** and pass it as `cloudflared_tunnel_token`.
3. **Add a Public Hostname** on the tunnel (e.g. `status.example.com`) with Service = `HTTP` and
   URL = the address the target service listens on. With `cloudflared_network_mode: host` that can be
   the host's loopback; prefer an explicit `127.0.0.1` over `localhost`, which resolves to `::1` first.
4. **Apply an Access policy to that hostname** (Zero Trust → Access → Applications → Self-hosted, same
   hostname) — do not leave it "Bypass" or with no policy.
5. An automated (non-browser) client that must reach a path behind the same Access policy can
   authenticate with a service token or Access mTLS instead of a browser login.

## Inputs

See [`meta/argument_specs.yml`](meta/argument_specs.yml) (generated from `meta/argument_specs.py`).
Key:

- `cloudflared_tunnel_token` (str, **no safe default** — the placeholder is rejected).
- `cloudflared_container_name` / `cloudflared_config_dir` — set distinctly per instance.
- `cloudflared_network_mode` (`bridge` | `host`, default `bridge`) — `host` when the tunnel's origin
  is a service on the host's own loopback.
- `cloudflared_protocol` (`quic` | `http2` | `auto`, default `quic`) — `http2` where QUIC dials time
  out (a path MTU too small for QUIC's datagrams).
- `cloudflared_deploy` (bool, default `true`) — `false` renders the config without starting or
  restarting the container (useful during a parallel-build cutover, where a second running replica
  would make Cloudflare balance live traffic onto it).

## Usage

```yaml
- hosts: status_host
  roles:
    - role: richard_lynch.network.service_cloudflared
      vars:
        cloudflared_container_name: status-tunnel
        cloudflared_config_dir: /opt/cloudflared-status
        cloudflared_network_mode: host
        cloudflared_tunnel_token: "{{ vault_status_tunnel_token }}"
```

## Testing

`molecule/default/` renders the compose file from sample vars (a fake, non-placeholder token) and
asserts the image tag is pinned, the token is rendered, `tunnel run` (not a local ingress config) is
used, and no host port is published. It cannot converge against a real tunnel.
