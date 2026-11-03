# service_public_endpoint

Publish **one** service as a human-authored name: an internal record in `endpoint_zone` and — only
when asked — a proxied Cloudflare record plus tunnel ingress, behind a verified Access app.

**It does NOT create Traefik routers.** It DETECTS an existing router for the name in
`endpoint_traefik_dynamic_dir` and refuses to overwrite it; `endpoint_upstream` is recorded and
reported but never written anywhere. A router for a genuinely new service is authored in the
traefik file-provider directory (or as compose labels) by the caller. That gap is real and this
README states it rather than letting the role's name imply otherwise.

One call per service, so a multi-step manual publication cannot be half-done.

## Usage

```yaml
- ansible.builtin.include_role:
    name: richard_lynch.network.service_public_endpoint
  vars:
    endpoint_name: grafana                         # -> grafana.example.com
    endpoint_upstream: "http://monitoring.example.com:3000"
    endpoint_zone: example.com
    endpoint_cname_target: traefik.example.com
    endpoint_bind9_addr: 192.0.2.53
    endpoint_traefik_dynamic_dir: /srv/ansible/files/traefik/dynamic
    endpoint_public: true                          # opt-in; default false
    endpoint_tunnel: main
    endpoint_tunnel_ids: {main: 00000000-0000-0000-0000-000000000000}
    endpoint_tunnel_service: https://traefik.example.com
    endpoint_cf_account: 0123456789abcdef0123456789abcdef
    endpoint_cf_zone: fedcba9876543210fedcba9876543210
    endpoint_cf_api_token: "{{ vault_cloudflare_api_token }}"  # or endpoint_cf_token_item + endpoint_op_vault (1Password)
    endpoint_machine_zone_labels: [dyn]            # refuse dyn.example.com and anything under it
    endpoint_apply: true                           # generate-don't-apply
```

Installation-wide values (zone, DNS server, Cloudflare ids, tunnel map, route directory) belong in
inventory; the call itself carries only the service.

## Human-authored names only

This writes names humans author. It **refuses** to write into a zone the caller declares
machine-owned — any zone carrying a label listed in `endpoint_machine_zone_labels` (DHCP-driven DNS
updates for hosts, `dns_service_registrar` for services). A hard gate enforces it rather than
trusting callers. The list is empty by default.

## The Cloudflare token

Pass it as `endpoint_cf_api_token` (no_log) from any secret store, or name a 1Password item with
`endpoint_cf_token_item` and `endpoint_op_vault` to have the role read it through
`richard_lynch.common.onepassword_cached` (which needs the `op` CLI). Every request that carries it
is `no_log`.

## What is automatic, and what is not

With a wildcard Access application in front of the zone:

| | Automatic? |
|---|---|
| Cloudflare **Access** policy | **yes** — the wildcard app covers new hostnames |
| Public DNS record | no |
| Tunnel ingress | no |
| Traefik router | no |
| Internal DNS record | no |

So four explicit steps plus one free one — and the free one is the *security* step, which means a
half-finished manual job fails safe but still gets forgotten. Hence this role.

## The three things it refuses to get wrong

**A name cannot hold both a CNAME and an A record.** bind9 responds by refusing to load the
**entire zone**, so one bad name takes every other name in it down with it.
`add_host_to_domain` and `add_cname_to_domain` use different blockinfile markers and do not
deduplicate each other. The role reads the **live** record first (not the repo, which can be stale)
and refuses a collision.

**The tunnel ingress endpoint REPLACES the whole list.** A PUT carrying only the new rule deletes
every existing hostname on that tunnel. The role GETs, appends, and asserts *before* the PUT that
nothing would be lost and the catch-all is still last — then reads back and asserts the controller
stored it. An existing rule keeps its POSITION, and the PUT is skipped when the merged list equals
the one read, so re-running a converged play reports `changed=0`.

**Access coverage is not authentication.** A more-specific app **beats** the wildcard, and a
deliberate bypass app for one hostname is common. Asserting "a wildcard exists" would pass while a
name sat behind a bypass. The role resolves the *winning* app for the hostname (from its policy
decisions, not its name, and across every hostname an app lists) and fails if it is a bypass — or
if the policies of any app matching the hostname could not be read, since unknown decisions may be
a bypass.

It also refuses an unproxied public record: `proxied: false` publishes the name straight past
Cloudflare, so Access would never be consulted.

## Adoption never rewrites a route

When the hostname is already in a tunnel's ingress list, the **existing rule is carried through
verbatim** — service value, `originRequest`, everything. Only a genuinely new hostname gets a rule
built from `endpoint_tunnel_service`.

This matters because two tunnels can use different service values: one tunnel's rules may point at
a proxy by DNS name (`https://traefik.example.com`) while another's point at a container-local proxy
(`https://traefik`). Rebuilding an existing rule from this call's service value would repoint those
services at a proxy with no routers for them — and a hostname-only gate would pass, because every
hostname was still present.

The gate therefore asserts both: no hostname lost, **and** every pre-existing rule byte-identical.

## What it will not do

Create or narrow Access applications. Editing a wildcard app changes authentication for every name
under it at once, so the role asserts coverage and leaves the policy alone.

Overwrite an existing Traefik router. A duplicate router name makes Traefik reject it, so the role
reports and skips rather than silently taking a live route down.

## Testing

`molecule/default/` calls the role's real merge logic against a realistic tunnel fixture — nine
hostnames plus a catch-all, on a service value that differs from the caller's — because that is the
blast radius of a naive PUT, not a toy list.

Both failure modes are verified by **mutation**, not assumed:

- make the merge replace instead of append → *"Refusing to PUT: 9 pre-existing hostname(s) would be
  dropped"*, naming all nine
- move the catch-all off the end → *"the catch-all is missing / not last"*
- rebuild an existing rule instead of adopting it → *"REWRITTEN rule(s): foxtrot.example.com:
  https://traefik -> https://traefik.example.com"*

It also runs the role's own Access gate (`tasks/_access_gate.yml`) against fixture apps and
policies: the wildcard wins and passes for an ordinary name, each more-specific bypass wins over it
and is refused, an app reached only through `self_hosted_domains` is found, and a matching app whose
policies could not be read is refused rather than reported as protected.
