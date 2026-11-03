# unifi_network_dhcp

Brings per-VLAN DHCP settings on the UniFi controller (UDM) under Ansible control: dynamic pool
range, the resolvers handed to clients, and DHCP relay targets.

## Why this exists

Per-VLAN DHCP settings that live only on the router, as click-ops, drift in ways nobody notices.
A typical example: a DNS/DHCP **service** address that happens to be the *first address of its
VLAN's own DHCP pool*, so the host serving it holds it as a **dynamic lease** rather than
statically. Two consequences follow:

- The controller can lease the service address to any client. It does not only while
  `dhcpd_conflict_checking` is on — luck, not design.
- Removing the address from the host (`ip addr del`) is **not durable**: the host's DHCP client
  re-adds it at lease renewal, so a migration that "moves" the address quietly gets it back.

Raising `dhcpd_start` above the service address puts it structurally outside DHCP's control. This
role makes that, and every other per-VLAN DHCP setting, declared and reviewable.

## What it does

1. Asserts an API key was supplied (rejects the placeholder).
2. GETs the live `networkconf` and indexes it by VLAN id.
3. Fails if a requested VLAN does not exist — it never guesses.
4. Computes, per network, the merged object and a diff of only the keys that differ.
5. Reports the diff. **Changes nothing** unless `unifi_network_dhcp_apply=true`.
6. When applying: PUTs each changed object, re-GETs, and asserts the controller reports the values
   requested.

### Merge, don't construct

The UniFi REST API **replaces the whole object on PUT**. A network object carries over 50 keys; a
body built from scratch would silently drop every one you did not think to include. This role always
merges into the live object. The merge is verified in molecule against a fixture shaped like a
controller's `networkconf` response: same key count in and out, zero keys lost, only the requested
key changed.

## Usage

Always dry-run first and read the diff:

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: richard_lynch.network.unifi_network_dhcp
      unifi_network_dhcp_api_key: "{{ lookup('richard_lynch.common.onepassword_cached', ...) }}"
      unifi_network_dhcp_networks:
        - vlan: 100
          dhcpd_start: "192.0.2.11"
```

```bash
ansible-playbook <play>.yml                                    # diff only, no change
ansible-playbook <play>.yml -e unifi_network_dhcp_apply=true   # apply
```

## Getting the API key

Create an API key in the UniFi Network application (Settings → Control Plane → Integrations) and
pass it as `unifi_network_dhcp_api_key`, from a secrets manager rather than inventory.

> **Gotcha.** An empty `X-API-KEY` makes every request return `401 Unauthorized`, which looks
> exactly like a permissions or scope problem. If your secrets lookup can return an empty string
> without failing (a wrong field name, a path it misparses), check that before suspecting the key's
> permissions.

## Variables

See `meta/argument_specs.yml` for the full validated interface.

| Variable | Default | Purpose |
|---|---|---|
| `unifi_network_dhcp_host` | *required* | Controller address |
| `unifi_network_dhcp_site` | `default` | UniFi site internal reference |
| `unifi_network_dhcp_api_key` | placeholder | X-API-KEY (from a secrets manager; placeholder rejected) |
| `unifi_network_dhcp_validate_certs` | `false` | UDM presents a self-signed cert |
| `unifi_network_dhcp_networks` | `[]` | Desired per-network state |
| `unifi_network_dhcp_apply` | `false` | Generate-don't-apply; `true` actually PUTs |

Per-entry keys: `vlan` (required), `dhcpd_start`, `dhcpd_stop`, `dhcpd_dns` (list, → `dhcpd_dns_1..4`),
`dhcp_relay_servers` (list). Anything omitted is left as the controller has it.

## Notes

- Idempotent: a second run computes no change and PUTs nothing.
- `no_log` is set on every task carrying the API key or full network objects.
- The role only touches the keys you name. It is a reconciler, not a template — it will not converge
  the controller to some canonical whole-object state.

## Entrypoints

Do not call this role bare. Pick the entrypoint that matches the change you are making — each
validates only its own input, then includes the shared engine (`tasks/_apply.yml`).

| `tasks_from:` | Accepts | Notes |
|---|---|---|
| `settings` | `vlan` + `dhcpd_enabled`, `dhcpd_start`/`stop`, `dhcpd_leasetime`, `dhcpd_dns`, `dhcp_relay_servers` | Everything except the relay flag |
| `relay_on` | `vlan` **only** | Sets `dhcp_relay_enabled: true` itself |
| `relay_off` | `vlan` + any settings | May carry co-travelling fields |

```yaml
# put a VLAN into relay mode — TWO calls, in this order
- ansible.builtin.include_role:
    name: richard_lynch.network.unifi_network_dhcp
    tasks_from: settings
  vars:
    unifi_network_dhcp_networks: [{ vlan: 200, dhcp_relay_servers: ['192.0.2.2'] }]

- ansible.builtin.include_role:
    name: richard_lynch.network.unifi_network_dhcp
    tasks_from: relay_on
  vars:
    unifi_network_dhcp_networks: [{ vlan: 200 }]
```

### Why `relay_on` refuses everything but `vlan`

`dhcp_relay_enabled: true` is only accepted when it is the **only** thing changing. Sent alongside
anything else — including `dhcp_relay_servers`, which looks like it belongs — the controller
returns `rc: ok`, applies the other fields, and **silently drops the flag**, leaving a network with
no DHCP server at all. Only a read-back reveals it.

The previous design took every field in one call and policed combinations at runtime. That gate
counted keys and allowed `length <= 3`, which permits exactly
`{vlan, dhcp_relay_enabled, dhcp_relay_servers}` — the one failing shape — so networks configured
through it came up with no DHCP. A runtime check can be wrong; an input shape that cannot express
the bad request cannot.

Disabling relay is **asymmetric and that is deliberate**: `relay -> server` applies atomically, so
`relay_off` accepts other fields. Requiring isolation there would turn the documented rollback into
a two-step dance through a window with no DHCP server.

## Testing

`molecule/default/` calls the **real role through its real entrypoints**, with the controller
stubbed by an injected fixture (`unifi_network_dhcp_live_fixture`) and `apply: false`. It contains
no copy of the role's logic — the previous scenario re-implemented the merge here and asserted that
copy against itself, which is why a completely absent `dhcp_relay_enabled` passed a full molecule
run.

Both failure modes are verified by mutation, not assumed:

- deleting the `dhcp_relay_enabled` merge → *"relay_on did not set dhcp_relay_enabled in the merged
  object"*
- weakening `relay_on`'s guard back to `<= 3` → *"relay_on ACCEPTED {vlan, dhcp_relay_servers}"*

It also asserts the opposite error — that `relay_off` still accepts co-travelling fields — so the
asymmetry cannot be tidied away by someone making the two entrypoints look consistent.
