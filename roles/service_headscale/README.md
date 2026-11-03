# service_headscale

Deploys [Headscale](https://headscale.net) — a self-hosted Tailscale control
server — together with its embedded DERP relay, behind a traefik that terminates
TLS on one public port. One compose project, two containers, both on host
networking.

A typical target is a small public host that every client can reach; the
tailnet's names, routes and policy are the caller's options, set in inventory.

## Why it is shaped like this

| Choice                                     | Reason                                                                                                                                                                       |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| traefik in front, not Headscale's own ACME | Headscale's ACME supports only HTTP-01 (`:80`) and TLS-ALPN-01 (`:443`). Where those ports belong to something else, the cert must come from **DNS-01**, which traefik does. |
| traefik `readTimeout: 0s`                  | Control and DERP connections are long-lived upgraded streams; traefik v3's 60s default would cut every client once a minute.                                                 |
| host networking                            | STUN has to see each client's real source address/port, which Docker NAT rewrites. All TCP listeners are bound to loopback except traefik's.                                 |
| metrics on `127.0.0.1:9095`                | Headscale's default 9090 collides with anything Prometheus-shaped.                                                                                                           |
| `override_local_dns: false`                | Only the split domains go to the tailnet's resolvers, so a dead subnet router breaks the split names, not the client's whole internet.                                       |
| empty policy refused                       | An empty policy file is Headscale's **allow-all**.                                                                                                                           |

## Ports

| Port                             | Listener                             | Must be public    |
| -------------------------------- | ------------------------------------ | ----------------- |
| `headscale_server_port`/tcp      | traefik → Headscale (control + DERP) | yes               |
| `headscale_stun_port`/udp (3478) | Headscale STUN                       | yes               |
| 8080/tcp, 9095/tcp, 50443/tcp    | Headscale HTTP / metrics / gRPC      | **no** — loopback |

The DERP port is not separately configurable. Headscale derives it from
`server_url`, so it is always the same as `headscale_server_port`.

## State

`<deploy_dir>/lib/` holds the SQLite DB (users, nodes, keys), the Noise private
key and the DERP key. **Losing the Noise key forces every client to
re-register.** It is not backed up by this role.

## Restarts

Headscale reads `config.yaml` and `policy.json` only at startup. A change to
either recreates the container, which drops clients' **control** connections for
a few seconds. Established peer-to-peer tunnels keep passing traffic. traefik's
dynamic file is watched, so only its static config or credential triggers a
restart.

## Testing

`molecule test` renders every template from the role's own resolver and parses
the results as data. It calls the real role to prove both guards fire: the one
against an empty policy and the one against a `base_domain` Headscale rejects.
