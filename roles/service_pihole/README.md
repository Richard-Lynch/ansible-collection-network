# service_pihole

Pi-hole ad-block / forwarding DNS. Two supported topologies:

- **Behind a resolver:** Pi-hole is the **upstream** in the chain, on a non-53
  port: `client → resolver (e.g. bind9) → pihole (:5053) → public upstreams`.
- **Front door:** Pi-hole is the client-facing resolver on the service address
  (`:53`), and the authoritative server (e.g. bind9, authoritative-only) moves
  behind it on another address. This is the only arrangement in which Pi-hole
  sees real client addresses.

## What it does

- Renders `docker-compose.yml` — `pihole/pihole` (pinned), web UI on
  `pihole_web_http_port`/ `pihole_web_https_port`, config via pihole **v6
  `FTLCONF_*` env**: upstreams, listen mode, web/API password, and (front-door
  topology) conditional forwarding.
- DNS port publish: `pihole_dns_bind_ip` unset (default) binds **all** addresses
  at `pihole_dns_port`. Set `pihole_dns_bind_ip` to an explicit host address
  (e.g. `192.0.2.2`) with `pihole_dns_port: 53` to bind **only** that address —
  so in the front-door topology Pi-hole does not also grab every other address
  on the host. Docker DNAT for an explicit HostIp still preserves the real
  client source IP, which is what makes per-client attribution work once Pi-hole
  is in front.
- Seeds `etc-pihole/adlists.list` from `pihole_adlists` and **rebuilds gravity**
  (`pihole -g`) when the adlists change.
- The web password comes from the caller (`pihole_web_password`, from your
  secrets manager); a placeholder is rejected by an assert.

No custom DNS/CNAME records are managed here. Local names belong to the
authoritative server, not Pi-hole.

## Conditional forwarding (front-door topology only)

When Pi-hole is client-facing, internal names (your primary zone, any
per-segment zones, and the local subnets' reverse zones) must still resolve —
Pi-hole delegates them to the authoritative server instead of sending them to
its public upstreams:

- `pihole_rev_servers` — one entry per CIDR, rendered as
  `FTLCONF_dns_revServers` (`dns.revServers` in pihole.toml). Format:
  `"<enabled>,<ip-cidr>,<server>[#port][,<domain>]"`, e.g.
  `"true,192.0.2.0/24,192.0.2.3"`. Used for each local subnet's reverse zone.
- `pihole_dnsmasq_lines` — raw dnsmasq lines, rendered as
  `FTLCONF_misc_dnsmasq_lines` (`misc.dnsmasq_lines`). Used for a domain that
  spans several subnets and so cannot be expressed as one CIDR-scoped
  `revServers` entry (`server=/example.com/192.0.2.3`).

Both are empty by default (`[]`) — the behind-a-resolver topology does not need
them. Build them from the same data that defines the zones your authoritative
server serves, so they cannot drift from it. No forwarding loop as long as the
domain space partitions cleanly (the authoritative server must not forward back
to Pi-hole, e.g. bind9 with recursion off).

`pihole_upstreams` (public DNS for everything else) is only ever changed by
editing it yourself.

## Own-hostname / pi.hole replies — `pihole_reply_host_ip`

Docker sets the container's **kernel hostname** to the full `pihole_hostname`
string (dots included: `hostname` inside the container prints
`pihole.example.com` verbatim, not just `pihole`). FTL's "local interface" reply
logic (`pihole.toml [dns.reply.host]`) auto-answers queries for **both**
`pi.hole` and the machine's own hostname using the address the query arrived on
— which, once Pi-hole sees direct client traffic, is the docker bridge, not the
service address. So in the front-door topology `pihole.example.com` resolves to
a **docker-internal address** while the authoritative server correctly answers
the service address, and the web UI looks unreachable while DNS works.

`pihole_reply_host_ip` fixes this by pinning FTL's own-hostname/`pi.hole`
replies to a fixed address instead of letting it auto-detect:

```yaml
pihole_reply_host_ip: "192.0.2.2" # front-door topology; empty/unset otherwise
```

Rendered as `FTLCONF_dns_reply_host_force4: "true"` +
`FTLCONF_dns_reply_host_IPv4: "<value>"`. This does **not** disable `pi.hole` —
it corrects what both `pi.hole` and the real hostname resolve to, so both point
at the address the authoritative server answers instead of a shadowing one. Left
unset (default) preserves FTL's auto-detect behaviour, which is correct behind a
resolver (Pi-hole then never sees a client-arriving query to misattribute).

## Domain rules (allow/deny/regex) — `manage_domains`

Domain rules added by hand in the web UI live only in the gravity database,
which does not survive a rebuild or a move to a new host.
`tasks/manage_domains.yml` makes `pihole_allow_domains` / `pihole_deny_domains`
/ `pihole_allow_regex` / `pihole_deny_regex` (repo vars) the source of truth,
reconciled against Pi-hole's live state via the **v6 REST API** (`/api/auth`,
`/api/domains`).

**Add your allowlist here** — in inventory (the role's own defaults are all
empty):

```yaml
pihole_allow_domains:
  - example.com # <- exact-match single-domain overrides here
pihole_deny_domains: []
pihole_allow_regex:
  - '(\.|^)example\.net$' # <- regex-kind rules here (kind=regex, not exact)
pihole_deny_regex: []
```

Nothing is invented or seeded by this role — all four lists start empty. Exact
and regex rules are reconciled together (four repo lists, one diff/add/remove
pass) but never conflated with each other — `kind` is part of a rule's identity,
so a regex pattern is never coerced into (or matched against) an exact-domain
rule and vice versa. Call `tasks_from: manage_domains` from a play to reconcile
this onto a running Pi-hole (generate-don't-apply by default).

### How reconciliation works

1. Authenticate (`POST /api/auth`), get a session id.
2. `GET /api/domains`, index the live **exact**-kind rules (this does not manage
   regex rules).
3. Compute the diff: **ADD** anything in
   `pihole_allow_domains`/`pihole_deny_domains` not already live under the same
   type; **REMOVE** only entries whose `comment` matches
   `pihole_domains_managed_comment` (i.e. entries this role itself created) that
   are no longer in the repo list. A rule added by hand in the web UI (any other
   comment) is **never** touched — this role reconciles its own entries, not the
   whole domains table.
4. Report the diff. Change nothing unless `pihole_domains_apply=true`.
5. When applying: `POST`/`DELETE` to reconcile, then re-`GET` and hard-gate that
   every wanted domain is now live (never trust a write's HTTP status alone).
6. Log out the session.

Call it via `tasks_from:` from a play, same pattern as `service_bind9_dns`'s
record interface:

```yaml
- ansible.builtin.include_role:
    name: richard_lynch.network.service_pihole
    tasks_from: manage_domains
  vars:
    pihole_web_password: "{{ pihole_admin_password }}" # from your secrets manager
```

```bash
ansible-playbook <play>.yml                                  # diff only, no change
ansible-playbook <play>.yml -e pihole_domains_apply=true      # reconcile
```

**`no_log` and debuggability.** The authentication call is `no_log` (its body
carries the password and its response the session id), but it does not fail on
its own: the assert after it reports the HTTP status and Pi-hole's own message
from the registered result, so an API error stays visible without the credential
reaching the log.

### Groups / clients

`pihole_groups` / `pihole_clients` are reserved (declared, defaulted to `[]`)
but not wired up — Pi-hole's group/client API follows the same `/api/*` +
session-auth shape as domains, so adding them later is a small extension of
`manage_domains.yml`, not a redesign. Not built now because nothing in this task
needed per-client policy yet; do it when there's a concrete use.

## Usage

```yaml
- hosts: dns
  roles:
    - role: richard_lynch.network.service_pihole
      vars:
        pihole_web_password: "{{ pihole_admin_password }}" # from your secrets manager
```

Key vars (see `defaults/main.yml`): `pihole_image`, `pihole_upstreams` (default
`8.8.8.8`,`8.8.4.4`), `pihole_adlists`, `pihole_dns_port`, `pihole_dns_bind_ip`
(unset = all addresses), `pihole_listening_mode` (all),
`pihole_rev_servers`/`pihole_dnsmasq_lines` (front-door topology only),
`pihole_reply_host_ip` (front-door topology only — pins the own-hostname/pi.hole
replies, see above),
`pihole_allow_domains`/`pihole_deny_domains`/`pihole_allow_regex`/`pihole_deny_regex`
(domain rules, see above). `pihole_deploy: false` renders config only (tests).

## Testing

`molecule test` runs offline (renders compose + adlists in both topology shapes,
asserts image pin / ports / upstreams / listen mode / adlists / explicit HostIp
/ revServers / dnsmasq_lines / reply_host_ip, and exercises the `manage_domains`
add/remove diff logic — exact AND regex kinds — against fabricated live data —
no network needed). The REST API reconciliation and the `pihole_reply_host_ip`
behaviour are worth proving once against a real Pi-hole (a preview run, then a
`dig` read-back) before relying on them.
