# dns_service_registrar

Reconciles one `svc.*` DNS zone against the set of services a host actually runs.

## What this is

It is built for a two-layer name model in which machine-written names (Layer 1) have **two**
registrars, each confined to its own zone:

| Registrar | Writes | Zone (example) | Key |
|---|---|---|---|
| DHCP-driven DDNS (e.g. Kea) | host `A` + `PTR` | `<segment>.example.com` | the DHCP server's update key |
| **this role** | service `CNAME`s | `svc.<segment>.example.com` | `svc_tsig_key_name` |

Give the two registrars separate TSIG keys and restrict each with bind9's `allow-update`, so
neither can write the other's zone, and test that boundary in both directions. Humans write
neither: the human-facing names (Layer 2) are CNAMEs in a separate zone, kept in version control.

## Why CNAMEs, not A records

Records point at the host's **DDNS-registered name**, so when the host renumbers every service
follows automatically at Kea's speed with this role doing nothing. An A record would make this a
second address authority that must *notice* renumbering — a failure mode of a stale IP that still
resolves, which is worse than one that fails loudly.

## Ownership and garbage collection

The **CNAME target is the ownership marker**, already present in the data — no TXT registry needed.
A run only considers records pointing at its own `svc_dns_target`, so a zone shared by several
hosts is safe: no host can delete another's records. A wanted name already pointing elsewhere is a **hard failure**, not
a silent repoint.

## Usage

Invoked from the apply path of a stack deploy, so registration is a side effect of deploying rather
than a step someone can forget:

```yaml
- ansible.builtin.include_role:
    name: richard_lynch.network.dns_service_registrar
  vars:
    svc_dns_zone: "svc.apps.example.com"
    svc_dns_target: "app1.apps.example.com"
    svc_dns_names: "{{ ...derived from the stack's traefik routers... }}"
    svc_dns_apply: true
```

For a standalone or recovery run, call the role from a small play that supplies the same variables.

Generate-don't-apply: reports the diff and changes nothing unless `svc_dns_apply=true`.

## Testing

`molecule/default` exercises the role's real `compute.yml` against stubbed zone contents and asserts
**hand-typed literal** expectations — never re-deriving the role's own filter chain, which would
assert the copy against itself. Covered: the mixed case (add + delete + foreign-record-untouched +
no churn on an already-correct record), the empty-zone first run, the full rendered nsupdate script,
and the cross-host conflict hard-fail.

The I/O halves (AXFR, nsupdate, read-back) belong in a live test against a real server, using a
disposable zone such as `svc.test.example.com`.
