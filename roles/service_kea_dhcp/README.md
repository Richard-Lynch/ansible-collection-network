# service_kea_dhcp

ISC Kea DHCPv4 + DHCP-DDNS — hands out leases per VLAN and registers hostnames into BIND 9 via DDNS,
signing each update with a TSIG key (`ddns_tsig_key_name`).

## What it does

- `kea-dhcp4` (`isc/docker/kea-dhcp4`, pinned 2.5.8) — DHCP on `:67`, control API `:8000`, per-VLAN
  subnets/pools + `domain-name-servers` option from `kea_vlans`. Lease DB is a memfile persisted in the
  `kea_dhcp_dhcp_leases` volume (`/var/lib/kea/dhcp.leases`) — **the lease DB must be preserved across
  any host migration**, or every client is treated as new.
- `kea-dhcp-ddns` (pinned 2.5.8) — receives NCRs from dhcp4 (`:53001`) and sends TSIG-signed DNS UPDATEs
  to bind9 for the forward + reverse zones of each VLAN.
- `entrypoint.sh` resolves the ddns container IP into the dhcp4 config at start.

## Key vars

Full declarations, types and rationale live in `meta/argument_specs.py`; the generated
`defaults/main.yml` carries the same prose as comments. The load-bearing ones:

| var | default | why it matters |
|---|---|---|
| `kea_vlans` | *required* | Subnets to serve. Typically built from an inventory VLAN map as `vlans.values() \| selectattr('dns','undefined')` — a VLAN with a `dns:` key is served by another DHCP server and excluded. |
| `kea_dns_servers` | *required* | bind9 targets for **DDNS** updates. Not the same thing as the client resolver. |
| `ddns_tsig_key_secret` | *required*, `no_log` | From vault. |
| `kea_service_ip` | *required* | The host address the DHCP port map binds to (never the wildcard). |
| `kea_dns_zone_suffix` | *required* | The suffix bind9 serves per-VLAN zones under, e.g. `vlans.example.com`. |
| `kea_reservations` | `[]` | Host reservations, rendered per subnet. Normally merged from a reservations directory by `kea_reservations`. |
| `kea_inpool_reservations_allowed` | `[]` | Declared exceptions to the reserved-band rule. |
| `kea_pool_offset` | `10` | Where the dynamic pool starts. `.2`–`.10` is the reserved band; the pool begins at `.11`. |
| `kea_option_dns_servers` | `kea_dns_servers` | **Client-facing** resolver (option 6). Must be the *service* address, not a management address. |
| `kea_server_identifier` | *required* | Option 54. Must be the host's real address — Kea's docker-internal one breaks every unicast renewal. |
| `kea_match_client_id` | `false` | Match reservations on MAC alone. |
| `kea_authoritative` | `true` | NAK rather than ignore, so a renumber is fast and visible. |

## The address plan this role enforces

With the default `kea_pool_offset: 10`, shown for a /24 whose base is `.1`:

```
.1         gateway (router)
.2 - .10   reserved band — infrastructure statics + DHCP reservations
.11 - .251 dynamic pool
```

Four guard rails run **before** any config is rendered, so a bad input fails the play rather than
producing a Kea that hands out wrong names or leases reserved addresses:

1. every VLAN's `domain_name` matches `kea_dns_zone_suffix` (else DDNS registers into a zone bind9
   does not serve, and the names simply never resolve);
2. the client resolver list is non-empty (`[]` does not trigger `| default(...)`);
3. the resolver sits inside the reserved band (stable and un-leasable);
4. every reservation sits inside its subnet's reserved band, unless listed in
   `kea_inpool_reservations_allowed`.

Then the rendered config is validated with `kea-dhcp4 -t` **before** any restart, and Kea is read
back afterwards — a container that comes up with a crash-looping daemon still reports "restarted".

## Testing

`molecule test` runs offline and renders **all three** templates — compose, the DDNS config, and
`kea-dhcp4.conf.template.j2` — then parses the dhcp4 output as JSON and asserts on the real
structure: reservations land in the correct subnet, the optional `hostname` key is omitted rather
than emitted empty, pools start above the reserved band, and `match-client-id` / `authoritative` /
option 54 / DDNS suffixes are all as declared.

Each assertion has been verified to **fail** against an injected regression (subnet filter removed,
hostname emitted unconditionally, pool overlapping the band) — a test that has never failed proves
nothing.

Live validation: ask the **running process** for its config with a `config-get` through the
control agent (as `kea_reservations`' `assert_reserved` entrypoint does), not the file on disk,
which is the previous run's output.
