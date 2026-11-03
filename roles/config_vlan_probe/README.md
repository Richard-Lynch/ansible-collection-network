# config_vlan_probe

Configures a **multi-homed VLAN probe** — a guest with a leg on several VLANs,
whose job is to be a place to send **link-local** traffic from on each segment —
and, more importantly, **proves each leg actually landed on the VLAN it was
asked for**.

## Why this role exists

A Wake-on-LAN magic packet is a **layer-2 broadcast**. It does not cross a VLAN
boundary, so it must originate on the target's own segment. Routed unicast
between VLANs usually works, but broadcast, multicast and ARP are confined to
their broadcast domain by design — so a controller or automation host that sits
on one VLAN cannot wake, ARP-check or discover anything on the others. A guest
with one leg on each segment gives every segment a local sender.

## The position assertion is the point

A magic packet is **unacknowledged UDP**. A probe sitting on the wrong broadcast
domain sends successfully, reports success, and wakes nothing — so **liveness is
not coverage**. This role therefore reads the guest's **own interface state**
and asserts every expected address is really held, rather than trusting the
`tag=` the guest was created with.

That distinction is not theoretical. On many hypervisors a guest NIC configured
with VLAN tag 1 lands on the trunk's **native** (untagged) VLAN, whatever its id
is, and a NIC tagged with the native VLAN's own id may land nowhere useful — it
cannot reach its gateway, while every other leg works first time. Asserting on
the request rather than the result would report such a guest as fully covered.

The assertion is **proven capable of failing**: add a VLAN to
`config_vlan_probe_expected` that the guest has no leg on and it fails naming
it.

## Variables

| variable                     | required | default                                                  | meaning                                                                                                                                                                                                                                              |
| ---------------------------- | :------: | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `config_vlan_probe_expected` | **yes**  | —                                                        | The segments this guest must be on: a list of `{name, id, address, cidr, gateway}`. **Derive it in the caller from the same VLAN data that builds the legs**, never hand-copy it — a hand-typed list is a second source of truth and goes stale the first time a VLAN is added. |
| `config_vlan_probe_packages` |    no    | `iputils-arping`, `iputils-ping`, `iproute2`, `dnsutils` | Link-local tooling.                                                                                                                                                                                                                                  |
| `config_vlan_probe_apply`    |    no    | `false`                                                  | Generate-don't-apply gate. `false` asserts position and changes nothing; `true` also installs the tooling.                                                                                                                                           |

`config_vlan_probe_expected` has **no default on purpose**:
which segments a probe is expected to hold is installation configuration, and a
default would make the role assert a position nobody asked for.

## Services on the probe

Each is its own entrypoint and play, and each uses the guest for what it
uniquely has: a leg on every segment.

| entrypoint | what it does |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wake_endpoint` | `GET /wake/<target>` sends a Wake-on-LAN packet on the target's own segment. Allowlist: `config_vlan_probe_wake_targets`. **The endpoint has no authentication**: anyone who can reach its port can list the declared targets and wake them. Bind or firewall it so only trusted segments can reach it. |
| `broadcast_relay` | Re-emits declared UDP **broadcasts** from one leg onto another, one way, **with the sender's address preserved**, so the unicast answer goes straight back to the sender. It exists for LAN game discovery (a client on a wireless VLAN finding a server on a wired one). Allowlist: `config_vlan_probe_relays`. The only privilege is `CAP_NET_RAW` (ambient, on a DynamicUser). |

The relay maps each declared broadcast address to the interface that holds it,
**from the guest's own facts**, and refuses a relay that names a leg the guest
does not hold. It forwards only packets that arrived **as broadcasts** from
inside the source leg's subnet. That subnet check is also what stops loops: what
the relay emits carries a foreign source on the other leg. It re-emits at most
`config_vlan_probe_relay_rate` packets per second.

## What is deliberately NOT installed

- **Nothing for Wake-on-LAN.** `community.general.wakeonlan` builds and sends
  the magic packet from the module's own Python over a UDP socket, so no
  `etherwake`/`wakeonlan` binary is needed.
- **No `avahi-daemon`/`gssdp`.** Running avahi would make the probe an mDNS
  _participant_ rather than an observer, and an unused daemon on every VLAN is
  attack surface for a capability nobody asked for. Install them deliberately if
  and when the discovery case is actually pursued.
- **No `tcpdump`.** Genuinely useful during an incident, and it needs
  capabilities an unprivileged container may not grant. A deliberate decision, not a
  default.

## Argspec is generated

`meta/argument_specs.yml` and `defaults/main.yml` are **generated** from
`meta/argument_specs.py`. Edit the Python, then:

```
venv/bin/python tools/argspec/cli.py x generate config_vlan_probe
```

## Caller

The caller's provisioning play, which should derive both the legs and the
expectation list from the same VLAN map so the two cannot drift.
