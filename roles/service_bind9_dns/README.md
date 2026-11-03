# service_bind9_dns

Authoritative DNS for `*.example.com` and (topology-dependent) the LAN resolver — exposing a **task
interface so services register their own DNS records**. Validated with `named-checkconf` +
`named-checkzone`.

## Two supported topologies

- **bind9 recurses:** `bind9_recursion: true` — bind9 recurses by forwarding (`forward only`) to an
  upstream (`bind9_forward_ip:bind9_forward_port`, e.g. a co-located Pi-hole on `:5053`, or the
  `bind9_forwarders` list), and publishes `:53` on all host addresses.
- **Resolver in front (default):** `bind9_recursion: false` — bind9 is authoritative-only (no
  forwarders, no recursion). Clients query a resolver such as Pi-hole, which forwards the local
  zones to bind9. If both run on one host, set `bind9_dns_service_bind_ip` so bind9 publishes `:53`
  on ONLY its own (e.g. management) address, leaving the service address to the resolver.

## Canonical naming scheme

- Host: `<host>.<vlan>.vlans.example.com` (A record)
- Service: `<service>.<host>.<vlan>.vlans.example.com` (CNAME to host/traefik)
- Convenience: `<name>.example.com` (CNAME in the primary zone)

Zones: primary `example.com` (static) + per-VLAN `<vlan>.vlans.example.com` forward + reverse
(DDNS-updatable via TSIG `dhcp-key`).

## `main` — deploy the server

Renders `docker-compose.yml` (pinned `ubuntu/bind9`), `named.conf` (zone stanzas + an `include` of
`named.conf.options`), `named.conf.options` (options{}/logging{} — see below), the TSIG key file, and
creates the primary domain + per-VLAN forward/reverse zones from the `vlans` dict.

```yaml
- hosts: dns_servers
  roles:
    - role: richard_lynch.network.service_bind9_dns
      vars:
        bind9_primary_domain: "example.com"
        bind9_recursion: true
        bind9_forward_ip: "192.0.2.3"       # the upstream to forward to (recursion on only)
        ddns_tsig_key_secret: "{{ vault_ddns_tsig_key_secret }}"
```

### Why `named.conf.options` is a SEPARATE file from `named.conf`

`named.conf` is rendered `force: false` so the zone stanzas `add_domain`/`add_vlan` append survive
re-runs — but that means anything else in that file (options{}, logging{}) could **never** be updated
on an already-provisioned host; a second run would silently keep the first run's settings forever.
`bind9_recursion`/`bind9_dns_service_bind_ip` need to actually take effect when a topology change
runs against a host that's already been deployed once, so `options{}`/`logging{}` live in
`named.conf.options` instead — rendered fresh every run, and `include`d from the top of `named.conf`.

### Port publish

`bind9_dns_service_bind_ip` unset (default) binds **all** addresses at `bind9_dns_service_port`
(`0.0.0.0:53->53`). Set it to an explicit host address (e.g. `192.0.2.3`) to bind **only** that
address — so bind9 does not also grab a service address another DNS server on the host owns.

## DDNS and the zones directory's ownership

Dynamic updates need named to CREATE a `.jnl` journal next to each zone file. `named` drops
privileges to `-u bind` (uid **100** / gid **101** in the `ubuntu/bind9` image, the standard
Debian/Ubuntu allocation), so if the host-side zones directory (bind-mounted at `/etc/bind/zones`)
is `root:root mode 0755`, journal creation fails:

```
/etc/bind/zones/lan.vlans.example.com.zone.jnl: create: permission denied
updating zone 'lan.vlans.example.com/IN': error: journal open failed: unexpected error
```

and bind9 answers every UPDATE with SERVFAIL (Kea logs `DHCP_DDNS_FORWARD_ADD_REJECTED RCODE 2`),
even though TSIG and the zone's `allow-update` are correct. A later REMOVE of such a name then fails
too (`DHCP_DDNS_FORWARD_REMOVE_RRS_REJECTED`), because the record was never added — a downstream
symptom, not a separate bug. `bind9_zones_owner_uid`/`bind9_zones_owner_gid` (default `100`/`101`)
fix this at the source: the role chowns the zones directory (and any zone files already on disk)
instead of loosening the mode to something world-writable, and hard-gates on a `stat` read-back
that the ownership actually took.

Working DDNS is also what lets a resolver in front (e.g. Pi-hole) attribute queries to device
**names** rather than bare IPs.

## Task interface (services own their records)

Call via `tasks_from:` from a service play. All idempotent, `present`/`absent`.

| tasks_from | Adds | Key vars |
|---|---|---|
| `add_domain` | a primary domain zone (static) | `bind9_domain` |
| `add_vlan` | a VLAN forward + reverse zone | `bind9_vlan_item` (or `bind9_vlan`) `{name,domain_name,base,cidr}` |
| `add_host_to_domain` | an A record | `bind9_parent_domain`, `bind9_sub_domain`, `bind9_ip` |
| `add_cname_to_domain` | a CNAME | `bind9_parent_domain`, `bind9_sub_domain`, `bind9_domain` (target) |

```yaml
# A service registers its own DNS:
- ansible.builtin.include_role:
    name: richard_lynch.network.service_bind9_dns
    tasks_from: add_cname_to_domain
  vars:
    bind9_parent_domain: "lan.vlans.example.com"
    bind9_sub_domain: "grafana"
    bind9_domain: "monitoring.lan.vlans.example.com"
```

## Records in a DYNAMIC zone

`add_host_to_domain` / `add_cname_to_domain` read named.conf for the zone's `allow-update`
(`_record_zone_kind.yml`) and route by it:

| zone | `present` | `absent` |
|---|---|---|
| static (`allow-update none`) | `blockinfile`, as before | `blockinfile`, as before |
| dynamic + `bind9_record_infra_exception` (`infra: true`) | nsupdate-ADD only if bind9 does not serve that exact RRset (`_dynamic_record.yml`) | nsupdate-DELETE only if served |
| dynamic, anything else | NOT written; checked read-only: must resolve to its declared value, else FAIL (`_dynamic_skip.yml`) | not written; the name is Kea's |

A journaled zone's file belongs to bind9: it rewrites it from memory and drops the
`ANSIBLE MANAGED` markers, which is why `blockinfile` re-inserted the same records and restarted
bind9 on every run. The exception path never edits a file; it needs `dig`, `nsupdate` and
`ddns_tsig_key_secret` on the host. The exception exists for names that can never lease
(static-address hosts, the DNS/DHCP host itself), so DDNS can never register them. If a zone was
managed with `blockinfile` before it became dynamic, `rndc sync -clean` folds the leftover markers
and duplicates out of its file.

## Testing

`molecule test` has two halves. Offline, it renders the config to a temp dir in BOTH topology shapes
(recursion on/off, with/without an explicit port-bind IP) and asserts the output is coherent,
including that the recursion-off render carries no stray `forwarders`/`forward only`. Live, it runs
the record task interface against a real bind9 container (the pinned image) with a static and a
dynamic zone, twice, and requires the second run to be `changed=0`. On a real host, also check the
zones directory's ownership and that a `.jnl` file appears after the first successful update.
